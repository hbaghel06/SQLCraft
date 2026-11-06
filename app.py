import os
import re
import json
import sqlite3
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

SYSTEM_INSTRUCTION = """
You are an expert SQL Architect and Database Professor.
Your job is to translate natural language user questions into accurate, production-ready SQL queries based strictly on the user-provided schema.

Rules:
1. Only use tables and columns specified in the schema. Do not hallucinate columns.
2. Adhere strictly to the requested SQL dialect (e.g., MySQL, PostgreSQL, SQLite).
3. Output MUST be valid, parsable JSON matching this exact structure:
{
  "sql": "SELECT ...;",
  "explanation": [
    "Explanation of clause 1...",
    "Explanation of clause 2..."
  ]
}
4. Do NOT wrap the output in markdown code blocks like ```json. Return ONLY the raw JSON string.
"""

def extract_and_parse_json(text):
    """Robust JSON parser that extracts JSON even if surrounded by markdown fences or conversational text."""
    if not text:
        raise ValueError("Empty response received from model.")
    
    clean_text = text.strip()
    
    # Remove markdown code block fences if present
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*```$", "", clean_text)
        clean_text = clean_text.strip()
    
    # Try direct parse
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        pass
    
    # Fallback: search for first { and matching last }
    json_match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from model response: {clean_text[:200]}")

def generate_with_gemini(schema_text, user_query, dialect):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
Database Schema:
{schema_text}

Target Dialect: {dialect}

User Request: {user_query}

Respond strictly with a JSON object containing "sql" and "explanation".
"""

    # Try gemini-2.0-flash first, fallback to gemini-1.5-flash
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            parsed = extract_and_parse_json(response.text)
            parsed["source"] = f"Gemini ({model_name})"
            return parsed
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Gemini API generation failed: {last_err}")

def parse_tables_and_columns(schema_text):
    """
    Extracts all table names and their column names from any DDL text.
    Handles custom schemas with parenthesized types (e.g. VARCHAR(20), DECIMAL(10,2)).
    """
    tables = {}
    if not schema_text:
        return tables

    chunks = re.split(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?", schema_text, flags=re.IGNORECASE)
    for chunk in chunks[1:]:
        tbl_match = re.match(r"^[`\"'\[]?(\w+)[`\"'\]]?\s*\(", chunk.strip(), re.DOTALL)
        if not tbl_match:
            continue
        tbl_name = tbl_match.group(1).strip()
        start_idx = chunk.find("(")
        if start_idx == -1:
            continue

        depth = 0
        end_idx = -1
        for i in range(start_idx, len(chunk)):
            if chunk[i] == '(':
                depth += 1
            elif chunk[i] == ')':
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break

        body = chunk[start_idx + 1:end_idx] if end_idx != -1 else chunk[start_idx + 1:]
        col_defs = []
        curr = []
        d = 0
        for ch in body:
            if ch == '(':
                d += 1
            elif ch == ')':
                d -= 1
            if ch == ',' and d == 0:
                col_defs.append("".join(curr).strip())
                curr = []
            else:
                curr.append(ch)
        if curr:
            col_defs.append("".join(curr).strip())

        cols = []
        for c_def in col_defs:
            c_clean = c_def.strip()
            if not c_clean or re.match(r"^(PRIMARY\s+KEY|FOREIGN\s+KEY|KEY|CONSTRAINT|UNIQUE|CHECK|INDEX)\b", c_clean, re.IGNORECASE):
                continue
            parts = c_clean.split()
            if parts:
                col = parts[0].strip("`\"'[](),;")
                if col and not re.match(r"^(PRIMARY|FOREIGN|KEY|CONSTRAINT|UNIQUE|CHECK)\b", col, re.IGNORECASE):
                    cols.append(col)
        if tbl_name and cols:
            tables[tbl_name] = cols
    return tables

def detect_intent(query_lower):
    """
    Detects the SQL intent (INSERT, SELECT, UPDATE, DELETE, AGGREGATE, CREATE)
    from free-form natural language using broad semantic pattern matching.
    Returns one of: 'insert', 'select', 'aggregate', 'update', 'delete', 'create'
    """
    q = query_lower

    # --- INSERT patterns ---
    insert_patterns = [
        r"\binsert\b", r"\binsertion\b", r"\badd\s+(a\s+)?(new\s+)?(record|row|entry|data|student|employee|user|item|product|customer|patient|order)\b",
        r"\bput\s+(a\s+)?(new\s+)?(record|row|entry|data)\b",
        r"\bregister\b", r"\benroll\b", r"\bcreate\s+(a\s+)?(new\s+)?(record|entry|row)\b",
        r"\bsave\s+(a\s+)?(new\s+)?(record|entry|row)\b",
        r"\bwrite\s+(a\s+)?query\s+(to\s+)?(insert|add)\b",
        r"\bquery\s+(to\s+|for\s+)(insert|add|store|save)\b",
        r"\bstatement\s+(to\s+|for\s+)(insert|add)\b",
        r"values\s*\(", r"\binto\s+\w+\s*\(",
    ]
    for pat in insert_patterns:
        if re.search(pat, q):
            return "insert"

    # --- DELETE patterns ---
    delete_patterns = [
        r"\bdelete\b", r"\bremove\b", r"\bdrop\s+(a\s+)?(row|record|entry)\b",
        r"\berase\b", r"\bpurge\b",
        r"\bwrite\s+(a\s+)?query\s+(to\s+)?(delete|remove)\b",
        r"\bquery\s+(to\s+|for\s+)(delete|remove|erase)\b",
    ]
    for pat in delete_patterns:
        if re.search(pat, q):
            return "delete"

    # --- UPDATE patterns ---
    update_patterns = [
        r"\bupdate\b", r"\bmodify\b", r"\bchange\b", r"\bedit\b",
        r"\bset\s+\w+\s*(=|to)\b", r"\balter\s+(the\s+)?(record|row|entry|value)\b",
        r"\bwrite\s+(a\s+)?query\s+(to\s+)?(update|modify|change)\b",
        r"\bquery\s+(to\s+|for\s+)(update|modify|change|edit)\b",
    ]
    for pat in update_patterns:
        if re.search(pat, q):
            return "update"

    # --- AGGREGATE patterns ---
    aggregate_patterns = [
        r"\bcount\b", r"\bhow\s+many\b", r"\bnumber\s+of\b", r"\btotal\b",
        r"\baverage\b", r"\bavg\b", r"\bsum\b", r"\bmaximum\b", r"\bmax\b",
        r"\bminimum\b", r"\bmin\b", r"\bgroup\s+by\b", r"\baggregate\b",
        r"\bstatistics\b", r"\bsummary\b",
    ]
    for pat in aggregate_patterns:
        if re.search(pat, q):
            return "aggregate"

    # --- SELECT patterns (broadest - check last) ---
    select_patterns = [
        r"\bselect\b", r"\bshow\b", r"\bfetch\b", r"\bget\b", r"\bdisplay\b",
        r"\blist\b", r"\bfind\b", r"\bsearch\b", r"\bview\b", r"\bprint\b",
        r"\bretrieve\b", r"\breturn\b", r"\bextract\b", r"\bpull\b", r"\bread\b",
        r"\bwrite\s+(a\s+)?query\b", r"\bquery\s+(to|for|that|which)\b",
        r"\bsql\s+(to|for|that)\b", r"\bstatement\s+(to|for|that)\b",
        r"\bwho\b", r"\bwhich\b", r"\bwhere\b", r"\bwhat\b",
        r"\bhave\b", r"\beach\b", r"\ball\b", r"\bevery\b",
        r"\bwith\b.*\bgreater\b", r"\bwith\b.*\bless\b",
        r"\bwith\b.*\bmore\s+than\b", r"\bwith\b.*\bless\s+than\b",
        r"\bwith\b.*\bequal\b", r"\bwith\b.*\bbetween\b",
        r"\bgreater\s+than\b", r"\bless\s+than\b", r"\bmore\s+than\b",
        r"\bat\s+least\b", r"\bat\s+most\b", r"\bbetween\b",
        r"\bliving\s+in\b", r"\bworking\s+in\b", r"\bfrom\s+\w+\b",
        r"\bborn\s+in\b", r"\baged\b", r"\bage\s+(above|below|over|under)\b",
    ]
    for pat in select_patterns:
        if re.search(pat, q):
            return "select"

    return "select"  # default fallback


def extract_where_conditions(query_lower, columns, target_table=""):
    """
    Extracts WHERE conditions from free-form natural language.
    Handles: col = val, col > val, col < val, col >= val, col <= val,
    'col greater than val', 'from the X dept', 'above age N', 'aged over N', etc.
    """
    conditions = []
    q = query_lower
    # Only exclude SQL keywords, NOT words that could be values (like 'from' in "from the HR dept")
    sql_stopwords = {"and", "or", "where", "select", "null", "query", "sql", "from", target_table.lower() if target_table else ""}

    for col in columns:
        col_lower = col.lower()
        col_pat = re.escape(col_lower)

        # Pattern: col > val, col >= val, col < val, col <= val, col = val, col != val
        op_match = re.search(
            rf"\b{col_pat}\b\s*(>=|<=|!=|<>|>|<|=)\s*['\"]?(-?\w[\w\.\-]*)['\"]?",
            q
        )
        if op_match:
            op = op_match.group(1)
            val = op_match.group(2).strip("'\"")
            if val.lower() not in sql_stopwords:
                val_fmt = val if re.match(r"^-?\d+(\.\d+)?$", val) else f"'{val}'"
                if op == "!=":
                    op = "<>"
                conditions.append(f"{col} {op} {val_fmt}")
                continue

        # Pattern: col is/equals/: val
        eq_match = re.search(
            rf"\b{col_pat}\b\s*(?:is|equals|equal\s+to|=|:)\s*['\"]?([\w\.\-]+)['\"]?",
            q
        )
        if eq_match:
            val = eq_match.group(1).strip("'\"")
            if val.lower() not in sql_stopwords:
                val_fmt = val if re.match(r"^-?\d+(\.\d+)?$", val) else f"'{val}'"
                conditions.append(f"{col} = {val_fmt}")
                continue

        # Pattern: col greater than / more than / above / over val (and "above age 60", "over age 18")
        gt_match = re.search(
            rf"\b{col_pat}\b.*?(?:greater\s+than|more\s+than|above|over|exceeds?|at\s+least)\s+['\"]?(-?\d+[\.\d]*)['\"]?",
            q
        )
        if not gt_match and col_lower in q:
            # Check inverted: "above age 60", "over 50000 salary"
            gt_match_inv = re.search(
                rf"(?:greater\s+than|more\s+than|above|over|exceeds?|at\s+least)\s+(?:{col_pat}\s+)?['\"]?(-?\d+[\.\d]*)['\"]?",
                q
            )
            if gt_match_inv:
                gt_match = gt_match_inv

        if gt_match:
            conditions.append(f"{col} > {gt_match.group(1)}")
            continue

        # Pattern: col less than / below / under val (and "under age 18", "below age 60")
        lt_match = re.search(
            rf"\b{col_pat}\b.*?(?:less\s+than|below|under|at\s+most)\s+['\"]?(-?\d+[\.\d]*)['\"]?",
            q
        )
        if not lt_match and col_lower in q:
            lt_match_inv = re.search(
                rf"(?:less\s+than|below|under|at\s+most)\s+(?:{col_pat}\s+)?['\"]?(-?\d+[\.\d]*)['\"]?",
                q
            )
            if lt_match_inv:
                lt_match = lt_match_inv

        if lt_match:
            conditions.append(f"{col} < {lt_match.group(1)}")
            continue

        # Pattern: col between X and Y
        between_match = re.search(
            rf"\b{col_pat}\b.*?between\s+(-?\d+[\.\d]*)\s+and\s+(-?\d+[\.\d]*)", q
        )
        if between_match:
            conditions.append(f"{col} BETWEEN {between_match.group(1)} AND {between_match.group(2)}")
            continue

        # Pattern: col like / contains / named val
        like_match = re.search(
            rf"\b{col_pat}\b.*?(?:like|contains?|starts?\s+with|named?|called)\s+['\"]?([\w\s\.\-]+?)['\"]?(?:\s|$)",
            q
        )
        if like_match:
            conditions.append(f"{col} LIKE '%{like_match.group(1).strip()}%'")
            continue

        # Pattern: "in/from the <value>" for string columns (e.g. "from the HR department", "in Mumbai")
        # Applies to columns that are clearly categorical (dept, city, gender, category, status, type, branch)
        if any(k in col_lower for k in ["dept", "department", "category", "city", "gender",
                                          "status", "type", "branch", "section", "class",
                                          "grade", "district", "state", "country", "region"]):
            in_match = re.search(
                rf"(?:in|from)\s+(?:the\s+)?['\"]?([\w]+)['\"]?\s+(?:{re.escape(col_lower)}|{re.escape(col_lower[:-1]) if col_lower.endswith('s') else ''})",
                q
            )
            if not in_match:
                # Also try: "from the <value>" where value comes right before or after context
                in_match2 = re.search(
                    rf"(?:{re.escape(col_lower)}|department|dept|category|city)\s+(?:is\s+|=\s*|:\s*)?['\"]?([\w]+)['\"]?",
                    q
                )
                if in_match2:
                    val = in_match2.group(1).strip()
                    if val.lower() not in sql_stopwords and len(val) > 1:
                        conditions.append(f"{col} = '{val}'")
                        continue
            else:
                val = in_match.group(1).strip()
                if val.lower() not in sql_stopwords:
                    conditions.append(f"{col} = '{val}'")
                continue

    # --- Generic patterns when no column name appears in query ---
    # e.g. "employees with salary > 50000" (column name appears but pattern above missed)
    for col in columns:
        col_lower = col.lower()
        # Already found condition for this column
        if any(col in cond for cond in conditions):
            continue

        # Generic "above/below <number>" near a numeric-sounding column
        num_keywords = ["salary", "price", "age", "score", "marks", "amount", "cgpa",
                        "gpa", "roll", "id", "year", "rating", "stock", "quantity",
                        "total", "count", "num", "number"]
        if any(k in col_lower for k in num_keywords):
            # "above 60" / "over 60" / "greater than 60" near this column context
            general_gt = re.search(
                r"(?:above|over|greater\s+than|more\s+than|exceeds?|at\s+least)\s+(-?\d+[\.\d]*)",
                q
            )
            if general_gt:
                conditions.append(f"{col} > {general_gt.group(1)}")
                break
            general_lt = re.search(
                r"(?:below|under|less\s+than|at\s+most)\s+(-?\d+[\.\d]*)",
                q
            )
            if general_lt:
                conditions.append(f"{col} < {general_lt.group(1)}")
                break

    # --- Standalone string filter: "in <Value>" or "from <Value>" near text columns ---
    # e.g. "employees from Mumbai" where city is a column
    if not conditions:
        text_cols = [c for c in columns if not any(k in c.lower() for k in
                     ["id", "roll", "num", "year", "age", "code", "pin",
                      "price", "salary", "amount", "score"])]
        for col in text_cols:
            col_lower = col.lower()
            match = re.search(
                r"(?:from|in|of|at|named?|called)\s+(?:the\s+)?['\"]?([\w]+)['\"]?",
                q
            )
            if match:
                val = match.group(1).strip()
                tbl_low = target_table.lower() if target_table else ""
                bad = {"the", "a", "an", "this", "that", "table", "schema",
                       "query", "sql", "all", "each", "every", "which", col_lower,
                       tbl_low, tbl_low[:-1] if tbl_low.endswith("s") else tbl_low + "s"}
                if val.lower() not in bad and len(val) > 1:
                    conditions.append(f"{col} = '{val}'")
                    break

    return conditions


def extract_values_from_prompt(user_query, columns):
    """
    Extracts INSERT values from prompts like:
    - 'insert ("Alice", 25, "HR")'
    - 'add a record with name Alice, age 25, dept HR'
    - 'insert name="Alice", age=25'
    """
    # 1. Try parenthesized values: ("hb", 23, "cse") or ('hb', 23, 'cse')
    paren_match = re.search(r"\(\s*([^()]+)\s*\)", user_query)
    if paren_match:
        raw = paren_match.group(1)
        # Split on comma not inside quotes
        parts = re.split(r""",\s*(?=(?:[^'"]*['"][^'"]*['"])*[^'"]*$)""", raw)
        vals = []
        for p in parts:
            p = p.strip().strip("'\"")
            vals.append(p)
        if vals:
            return vals

    # 2. Try "col = val" pairs: name="Alice", age=25
    kv_matches = re.findall(r"(\w+)\s*=\s*['\"]?([\w\s]+?)['\"]?(?:,|$)", user_query, re.IGNORECASE)
    if kv_matches:
        col_val_map = {k.lower(): v.strip() for k, v in kv_matches}
        ordered = [col_val_map.get(c.lower(), None) for c in columns]
        if any(v is not None for v in ordered):
            return [v if v is not None else "NULL" for v in ordered]

    # 3. Try "with col val" pattern: "with name Alice age 25 dept HR"
    vals = []
    for col in columns:
        m = re.search(
            rf"\b{re.escape(col.lower())}\b\s+['\"]?([\w\s]+?)['\"]?(?:\s+\w+\s+|\s*$|,)",
            user_query.lower()
        )
        if m:
            vals.append(m.group(1).strip())

    if len(vals) == len(columns):
        return vals

    # 4. Try quoted strings + standalone numbers in order
    tokens = re.findall(r"""['\"]([^'"]+)['\"]|(-?\d+\.?\d*)""", user_query)
    ordered_vals = []
    for t in tokens:
        ordered_vals.append(t[0] if t[0] else t[1])

    if ordered_vals:
        return ordered_vals

    return []


def generate_local_intelligent_fallback(schema_text, user_query, dialect):
    """
    Advanced NL-to-SQL engine that handles ANY custom schema and ANY free-form prompt.
    Uses semantic intent detection + column-aware parsing. 100% offline.
    """
    query_lower = user_query.lower().strip()
    dialect_upper = dialect.upper()

    tables = parse_tables_and_columns(schema_text)

    # --- Step 1: Identify target table ---
    target_table = None
    columns = []

    if tables:
        # Match by explicit table name in query
        for tbl in tables:
            pattern = rf"\b{re.escape(tbl.lower())}\b"
            if re.search(pattern, query_lower):
                target_table = tbl
                columns = tables[tbl]
                break

        # Match by column name mentioned in query
        if not target_table:
            best_tbl = None
            best_score = 0
            for tbl, cols in tables.items():
                score = sum(1 for c in cols if re.search(rf"\b{re.escape(c.lower())}\b", query_lower))
                if score > best_score:
                    best_score = score
                    best_tbl = tbl
            if best_tbl:
                target_table = best_tbl
                columns = tables[best_tbl]

        # Default to first table
        if not target_table:
            target_table = list(tables.keys())[0]
            columns = tables[target_table]
    else:
        target_table = "data"
        columns = ["id", "value"]

    # --- Step 2: Detect intent from free-form language ---
    intent = detect_intent(query_lower)

    # --- Step 3: Generate SQL based on intent ---

    if intent == "insert":
        raw_vals = extract_values_from_prompt(user_query, columns)
        formatted_vals = []
        for v in raw_vals:
            v_clean = str(v).strip().strip("'\"")
            if re.match(r"^-?\d+(\.\d+)?$", v_clean):
                formatted_vals.append(v_clean)
            else:
                formatted_vals.append(f"'{v_clean}'")

        if not formatted_vals:
            # Generate placeholder values based on column types from schema
            for c in columns:
                cl = c.lower()
                if any(k in cl for k in ["id", "roll", "num", "year", "age", "code", "pin"]):
                    formatted_vals.append("1")
                elif any(k in cl for k in ["price", "salary", "amount", "score", "marks", "cgpa", "gpa"]):
                    formatted_vals.append("0.00")
                elif any(k in cl for k in ["date", "dob", "joined"]):
                    formatted_vals.append("'2024-01-01'")
                elif any(k in cl for k in ["email"]):
                    formatted_vals.append(f"'user@example.com'")
                elif any(k in cl for k in ["phone", "mobile", "contact"]):
                    formatted_vals.append("'9999999999'")
                else:
                    formatted_vals.append(f"'Sample_{c}'")

        target_cols = columns[:len(formatted_vals)] if 0 < len(formatted_vals) <= len(columns) else columns
        if len(formatted_vals) > len(columns):
            formatted_vals = formatted_vals[:len(columns)]
            target_cols = columns

        col_clause = f" ({', '.join(target_cols)})"
        val_clause = f"({', '.join(formatted_vals)})"

        sql = f"INSERT INTO {target_table}{col_clause}\nVALUES {val_clause};"
        explanation = [
            f"Target dialect: {dialect_upper}.",
            f"Detected intent: INSERT — adding a new record into '{target_table}'.",
            f"Columns targeted: {', '.join(target_cols)}.",
            f"Values mapped: {val_clause} (strings quoted, numbers unquoted)."
        ]

    elif intent == "update":
        # Find SET column and value
        set_parts = []
        set_match = re.findall(
            r"(?:set\s+)?(\w+)\s*(?:=|to)\s*['\"]?([\w\s\.\-]+)['\"]?(?:,|where|$)",
            query_lower
        )
        for col_name, val in set_match:
            matched = next((c for c in columns if c.lower() == col_name), None)
            if matched:
                val_fmt = val.strip() if re.match(r"^-?\d+(\.\d+)?$", val.strip()) else f"'{val.strip()}'"
                set_parts.append(f"{matched} = {val_fmt}")

        if not set_parts:
            # Pick first non-id column as placeholder
            for c in columns:
                if not any(k in c.lower() for k in ["id", "primary", "key"]):
                    set_parts.append(f"{c} = 'new_value'")
                    break

        where_conds = extract_where_conditions(query_lower, columns, target_table)
        set_clause = ", ".join(set_parts)
        where_clause = f"\nWHERE {' AND '.join(where_conds)}" if where_conds else ""

        sql = f"UPDATE {target_table}\nSET {set_clause}{where_clause};"
        explanation = [
            f"Target dialect: {dialect_upper}.",
            f"Detected intent: UPDATE — modifying records in '{target_table}'.",
            f"SET clause: {set_clause}.",
            f"Condition: {where_clause.strip() if where_clause else 'No WHERE clause (all rows affected)'}."
        ]

    elif intent == "delete":
        where_conds = extract_where_conditions(query_lower, columns, target_table)
        where_clause = f"\nWHERE {' AND '.join(where_conds)}" if where_conds else ""

        sql = f"DELETE FROM {target_table}{where_clause};"
        explanation = [
            f"Target dialect: {dialect_upper}.",
            f"Detected intent: DELETE — removing records from '{target_table}'.",
            f"Condition: {where_clause.strip() if where_clause else 'WARNING: No WHERE clause — this will delete ALL rows.'}."
        ]

    elif intent == "aggregate":
        # Identify aggregation function
        agg_func = "COUNT(*)"
        agg_alias = "total_count"
        num_col = None

        # Find numeric column for SUM/AVG/MAX/MIN
        for c in columns:
            cl = c.lower()
            if any(k in cl for k in ["salary", "price", "score", "marks", "amount", "cgpa", "gpa", "age", "total"]):
                num_col = c
                break

        # Determine aggregation function — COUNT wins if "count/how many/number of" is present
        # Only use SUM when "sum" (not "total count") is explicit with a numeric column
        if re.search(r"\bcount\b|\bhow\s+many\b|\bnumber\s+of\b", query_lower):
            agg_func = "COUNT(*)"
            agg_alias = "total_records"
        elif re.search(r"\bavg\b|\baverage\b", query_lower) and num_col:
            agg_func = f"AVG({num_col})"
            agg_alias = f"avg_{num_col.lower()}"
        elif re.search(r"\bsum\b", query_lower) and num_col:
            agg_func = f"SUM({num_col})"
            agg_alias = f"sum_{num_col.lower()}"
        elif re.search(r"\btotal\b", query_lower) and num_col and not re.search(r"\btotal\s+\w*\s*(products?|records?|rows?|students?|employees?|customers?|patients?|items?)\b", query_lower):
            # "total salary" = SUM, but "total products" = COUNT
            agg_func = f"SUM({num_col})"
            agg_alias = f"total_{num_col.lower()}"
        elif re.search(r"\bmax\b|\bmaximum\b|\bhighest\b|\blargest\b", query_lower) and num_col:
            agg_func = f"MAX({num_col})"
            agg_alias = f"max_{num_col.lower()}"
        elif re.search(r"\bmin\b|\bminimum\b|\blowest\b|\bsmallest\b", query_lower) and num_col:
            agg_func = f"MIN({num_col})"
            agg_alias = f"min_{num_col.lower()}"

        # Detect GROUP BY column
        # Priority 1: categorical columns explicitly mentioned in query
        group_col = None
        categorical_keywords = ["dept", "department", "category", "type", "gender",
                                 "city", "status", "grade", "class", "branch", "section",
                                 "district", "state", "country", "region"]
        for c in columns:
            cl = c.lower()
            if re.search(rf"\b{re.escape(cl)}\b", query_lower):
                if any(k in cl for k in categorical_keywords):
                    group_col = c
                    break

        # Priority 2: "each <col>" / "per <col>" / "by <col>" pattern
        if not group_col:
            each_match = re.search(r"\b(?:each|per|by|for\s+each|for\s+every)\s+([\w_]+)\b", query_lower)
            if each_match:
                word = each_match.group(1)
                # Try exact match first
                matched = next((c for c in columns if c.lower() == word), None)
                if not matched:
                    # Try partial match (e.g., "doctor" matches "doctor_name")
                    matched = next((c for c in columns if word in c.lower() or c.lower() in word), None)
                if matched:
                    group_col = matched

        # Priority 3: any column explicitly mentioned that's not numeric/id
        if not group_col:
            for c in columns:
                cl = c.lower()
                if re.search(rf"\b{re.escape(cl)}\b", query_lower) and c != num_col:
                    if not any(k in cl for k in ["id", "roll", "num", "year", "date"]):
                        group_col = c
                        break

        # Limit detection
        limit_clause = ""
        lim_m = re.search(r"\b(?:top|first|limit)\s*(\d+)\b", query_lower)
        if lim_m:
            limit_clause = f"\nLIMIT {lim_m.group(1)}"

        where_conds = extract_where_conditions(query_lower, columns, target_table)
        where_clause = f"\nWHERE {' AND '.join(where_conds)}" if where_conds else ""

        if group_col:
            sql = f"SELECT {group_col}, {agg_func} AS {agg_alias}\nFROM {target_table}{where_clause}\nGROUP BY {group_col}\nORDER BY {agg_alias} DESC{limit_clause};"
        else:
            sql = f"SELECT {agg_func} AS {agg_alias}\nFROM {target_table}{where_clause};"

        explanation = [
            f"Target dialect: {dialect_upper}.",
            f"Detected intent: AGGREGATE — computing {agg_func} on '{target_table}'.",
            f"Group by: {group_col if group_col else 'None (single aggregate result)'}.",
            f"Filter: {where_clause.strip() if where_clause else 'No filter applied'}."
        ]

    else:  # SELECT (default)
        # Detect columns to project
        selected_cols = []
        for col in columns:
            if re.search(rf"\b{re.escape(col.lower())}\b", query_lower):
                selected_cols.append(col)

        # Only project specific cols if explicitly named and "all/*/records" not mentioned
        if selected_cols and not any(w in query_lower for w in ["all", "every", "each", "*", "records", "rows", "everything"]):
            col_projection = ", ".join(selected_cols)
        else:
            col_projection = "*"

        where_conds = extract_where_conditions(query_lower, columns, target_table)
        where_clause = f"\nWHERE {' AND '.join(where_conds)}" if where_conds else ""

        # ORDER BY detection
        order_clause = ""
        order_col = None
        for c in columns:
            if re.search(rf"\b{re.escape(c.lower())}\b", query_lower):
                if any(k in query_lower for k in ["order by", "sort by", "sorted", "ordered", "ranked", "highest", "lowest", "ascending", "descending"]):
                    order_col = c
                    break
        if order_col:
            direction = "DESC" if any(d in query_lower for d in ["desc", "descending", "highest", "largest", "newest", "latest"]) else "ASC"
            order_clause = f"\nORDER BY {order_col} {direction}"

        # LIMIT detection
        limit_clause = ""
        lim_m = re.search(r"\b(?:top|first|limit|only)\s*(\d+)\b", query_lower)
        if lim_m:
            limit_clause = f"\nLIMIT {lim_m.group(1)}"

        # JOIN detection (multi-table)
        join_clause = ""
        all_tables = list(tables.keys())
        if len(all_tables) > 1:
            joined = [target_table]
            for other_tbl in all_tables:
                if other_tbl == target_table:
                    continue
                tbl_lower = other_tbl.lower()
                if re.search(rf"\b{re.escape(tbl_lower)}\b", query_lower):
                    # Find common column for JOIN
                    t1_cols = set(c.lower() for c in columns)
                    t2_cols = set(c.lower() for c in tables[other_tbl])
                    common = t1_cols & t2_cols
                    if common:
                        join_col = next(iter(common))
                        # Capitalize to match actual column name
                        actual_col_t1 = next(c for c in columns if c.lower() == join_col)
                        actual_col_t2 = next(c for c in tables[other_tbl] if c.lower() == join_col)
                        join_clause += f"\nJOIN {other_tbl} ON {target_table}.{actual_col_t1} = {other_tbl}.{actual_col_t2}"
                    else:
                        # Try matching id-like foreign key pattern
                        fk_col = next((c for c in tables[other_tbl] if tbl_lower[:-1] in c.lower() or "id" in c.lower()), None)
                        pk_col = next((c for c in columns if "id" in c.lower()), None)
                        if fk_col and pk_col:
                            join_clause += f"\nJOIN {other_tbl} ON {target_table}.{pk_col} = {other_tbl}.{fk_col}"
                        else:
                            join_clause += f"\nJOIN {other_tbl} USING (id)"
                    joined.append(other_tbl)
                    col_projection = "*"  # use * for joins

        sql = f"SELECT {col_projection}\nFROM {target_table}{join_clause}{where_clause}{order_clause}{limit_clause};"
        explanation = [
            f"Target dialect: {dialect_upper}.",
            f"Detected intent: SELECT — querying records from '{target_table}'.",
            f"Columns: {col_projection}.",
            f"Filter: {where_clause.strip() if where_clause else 'No filter — full table scan.'}.",
        ]
        if order_clause:
            explanation.append(f"Ordering: {order_clause.strip()}.")
        if limit_clause:
            explanation.append(f"Row limit: {limit_clause.strip()}.")

    return {
        "sql": sql,
        "explanation": explanation,
        "source": "SQLCraft Local Dynamic Engine (Offline Mode)",
        "is_mock": True
    }

def execute_sqlite_locally(schema_sql, query_sql):
    """
    Executes the schema and query inside an isolated in-memory SQLite sandbox.
    Seeds sample data so live tables and rows can be displayed!
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    try:
        # Execute schema statements
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        for stmt in statements:
            # Skip comments or non-DDL directives
            if re.match(r"^(/\*|--|SET\s+|USE\s+)", stmt.strip(), re.IGNORECASE):
                continue
            # Clean common MySQL/PostgreSQL dialect markers for SQLite in-memory execution
            sqlite_compatible = re.sub(r"ENGINE\s*=\s*[\w\d]+", "", stmt, flags=re.IGNORECASE)
            sqlite_compatible = re.sub(r"DEFAULT\s+CHARSET\s*=\s*[\w\d]+", "", sqlite_compatible, flags=re.IGNORECASE)
            sqlite_compatible = re.sub(r"COLLATE\s*=\s*[\w\d]+", "", sqlite_compatible, flags=re.IGNORECASE)
            sqlite_compatible = re.sub(r"\bAUTO_INCREMENT\b", "AUTOINCREMENT", sqlite_compatible, flags=re.IGNORECASE)
            sqlite_compatible = re.sub(r"DECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)", "REAL", sqlite_compatible, flags=re.IGNORECASE)
            try:
                cursor.execute(sqlite_compatible)
            except Exception as stmt_err:
                print(f"[Schema Execution Warning] {stmt_err} on: {sqlite_compatible[:50]}")

        # Seed sample data for tables
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 1. Preset college schema seeding
            if "departments" in tables:
                cursor.executemany(
                    "INSERT OR IGNORE INTO departments VALUES (?, ?);",
                    [(1, "Computer Science"), (2, "Information Technology"), (3, "Electronics")]
                )
            if "students" in tables:
                cursor.executemany(
                    "INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?);",
                    [(101, "Aarav Sharma", 1, 2024), (102, "Priya Patel", 1, 2024), (103, "Rohan Verma", 2, 2023), (104, "Sneha Gupta", 3, 2024)]
                )
            if "courses" in tables:
                cursor.executemany(
                    "INSERT OR IGNORE INTO courses VALUES (?, ?, ?);",
                    [(201, "DBMS", 4), (202, "Operating Systems", 4), (203, "Computer Networks", 3)]
                )
            if "marks" in tables:
                cursor.executemany(
                    "INSERT OR IGNORE INTO marks VALUES (?, ?, ?, ?);",
                    [(1, 101, 201, 88.5), (2, 101, 202, 92.0), (3, 102, 201, 79.0), (4, 102, 202, 85.0), (5, 103, 201, 68.0)]
                )

            # 2. Dynamic custom table seeding (only for SELECT queries on empty custom tables)
            is_insert_dml = bool(re.search(r"^\s*(?:INSERT|UPDATE|DELETE)\b", query_sql, re.IGNORECASE))
            if not is_insert_dml:
                for tbl in tables:
                    if tbl in ["departments", "students", "courses", "marks"]:
                        continue
                    cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
                    count = cursor.fetchone()[0]
                    if count == 0:
                        cursor.execute(f"PRAGMA table_info({tbl});")
                        col_info = cursor.fetchall()
                        if col_info:
                            row1 = []
                            row2 = []
                            for idx, c in enumerate(col_info):
                                cname = c[1].lower()
                                ctype = (c[2] or "").lower()
                                if any(k in ctype for k in ["int", "serial"]) or any(k in cname for k in ["id", "roll", "num", "year"]):
                                    row1.append(101 + idx)
                                    row2.append(102 + idx)
                                elif any(k in ctype for k in ["real", "float", "double"]) or any(k in cname for k in ["price", "score", "salary", "amount"]):
                                    row1.append(88.5)
                                    row2.append(92.0)
                                else:
                                    if "dept" in cname:
                                        row1.append("CSE")
                                        row2.append("IT")
                                    elif "name" in cname:
                                        row1.append("Aarav Sharma")
                                        row2.append("Priya Patel")
                                    elif "email" in cname:
                                        row1.append("aarav@example.com")
                                        row2.append("priya@example.com")
                                    elif "city" in cname:
                                        row1.append("Mumbai")
                                        row2.append("Delhi")
                                    else:
                                        row1.append(f"{c[1]}_Val1")
                                        row2.append(f"{c[1]}_Val2")

                            placeholders = ", ".join(["?"] * len(col_info))
                            cursor.executemany(f"INSERT OR IGNORE INTO {tbl} VALUES ({placeholders});", [tuple(row1), tuple(row2)])
            conn.commit()
        except Exception as seed_err:
            print(f"[Seed Warning] {seed_err}")

        # Clean query for execution
        clean_query = query_sql.strip().rstrip(";")
        cursor.execute(clean_query)
        conn.commit()
        
        # If cursor.description is None (e.g. INSERT, UPDATE, DELETE)
        if cursor.description is None:
            match = re.search(r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+[`\"'\[]?(\w+)[`\"'\]]?", clean_query, re.IGNORECASE)
            target_table = match.group(1) if match else None
            
            if not target_table:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                all_t = [r[0] for r in cursor.fetchall()]
                target_table = all_t[0] if all_t else None

            if target_table:
                cursor.execute(f"SELECT * FROM {target_table};")
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                rows_display = [list(r) for r in rows[:50]]
                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows_display,
                    "row_count": len(rows),
                    "message": f"Successfully executed! Record modified/inserted in '{target_table}'. Displaying current table rows."
                }

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        rows_display = [list(r) for r in rows[:50]]

        return {
            "success": True,
            "columns": columns,
            "rows": rows_display,
            "row_count": len(rows),
            "message": f"Successfully executed! Returned {len(rows)} row(s)."
        }
    except Exception as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "message": f"SQLite execution notice: {str(e)}"
        }
    finally:
        conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate-sql", methods=["POST"])
def generate_sql():
    try:
        data = request.get_json() or {}
        schema_text = data.get("schema", "").strip()
        user_query = data.get("query", "").strip()
        dialect = data.get("dialect", "mysql").strip().lower()

        if not schema_text or not user_query:
            return jsonify({"error": "Both database schema and query description are required."}), 400

        result = None
        # Attempt Gemini if key is provided
        if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
            try:
                result = generate_with_gemini(schema_text, user_query, dialect)
            except Exception as api_err:
                # Log error and seamlessly fall back to local engine so demo NEVER breaks!
                print(f"[Warning] Gemini API failed ({api_err}), falling back to local engine.")
                result = generate_local_intelligent_fallback(schema_text, user_query, dialect)
                result["api_notice"] = f"Using local engine (API notice: {str(api_err)[:100]})"
        else:
            result = generate_local_intelligent_fallback(schema_text, user_query, dialect)

        # Attempt in-memory local execution test
        execution_result = execute_sqlite_locally(schema_text, result.get("sql", ""))
        result["execution"] = execution_result

        return jsonify(result)

    except Exception as e:
        print(f"[Error in generate_sql] {e}, falling back to local engine.")
        # Guaranteed fallback so frontend NEVER receives a 500 or broken JSON
        fallback = generate_local_intelligent_fallback(
            request.json.get("schema", "") if request.is_json else "",
            request.json.get("query", "") if request.is_json else "",
            request.json.get("dialect", "mysql") if request.is_json else "mysql"
        )
        fallback["warning"] = f"Recovered via local fallback engine: {str(e)[:100]}"
        fallback["execution"] = execute_sqlite_locally(
            request.json.get("schema", "") if request.is_json else "",
            fallback.get("sql", "")
        )
        return jsonify(fallback)

@app.route("/api/execute-raw", methods=["POST"])
def execute_raw():
    try:
        data = request.get_json() or {}
        schema_sql = data.get("schema", "").strip()
        query_sql = data.get("sql", "").strip()

        if not schema_sql or not query_sql:
            return jsonify({"error": "Schema and SQL query required for execution."}), 400

        res = execute_sqlite_locally(schema_sql, query_sql)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print(f"[*] SQLCraft Product Engine running locally at http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
