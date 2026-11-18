import re

def test_extract(user_query, columns):
    col_count = len(columns)
    all_rows = []

    # 1. Multi-line analysis: check if each line has an input record
    lines = [l.strip() for l in user_query.strip().splitlines() if l.strip()]
    
    # Pattern matching any bracket pair, including mismatched ones like ( ... } or [ ... )
    # e.g. ("hb", 54) or ("jn", 654} or ["hb", 54] or {"hb", 54}
    bracket_pat = r"[\(\{\[]\s*([^(){}\[\]]+?)\s*[\)\}\]]"

    # Try matching all bracketed groups in the entire text
    bracket_groups = re.findall(bracket_pat, user_query)
    if bracket_groups and len(bracket_groups) >= 1:
        for bg in bracket_groups:
            parts = re.split(r""",\s*(?=(?:[^'"]*['"][^'"]*['"])*[^'"]*$)""", bg)
            row_vals = [p.strip().strip("'\"") for p in parts if p.strip()]
            if row_vals:
                all_rows.append(row_vals)
        if all_rows:
            return all_rows

    # 2. Line-by-line fallback: extract tokens from each line if multiple lines exist
    if len(lines) > 1:
        line_rows = []
        for line in lines:
            # strip prefixes like "insertion->", "insert:", "add:"
            cleaned_line = re.sub(r"^(?:insert(?:ion)?(?:\s*->|:|\s+)?|add(?:\s*->|:|\s+)?)\s*", "", line, flags=re.IGNORECASE).strip()
            # extract string literals or numbers from this line
            tokens = re.findall(r"""['\"]([^'"]+)['\"]|(-?\d+\.?\d*)""", cleaned_line)
            vals = [t[0] if t[0] else t[1] for t in tokens if t[0] or t[1]]
            if vals:
                line_rows.append(vals)
        if line_rows:
            return line_rows

    # 3. Stream of tokens: if flat stream of values, group by col_count
    tokens = re.findall(r"""['\"]([^'"]+)['\"]|(-?\d+\.?\d*)""", user_query)
    all_tokens = [t[0] if t[0] else t[1] for t in tokens if t[0] or t[1]]
    if all_tokens and col_count > 0:
        # Group into chunks of size col_count
        chunked = [all_tokens[i:i + col_count] for i in range(0, len(all_tokens), col_count)]
        return chunked

    return []

# Test with the user's exact prompt from image:
query1 = """insertion->("hb", 54),
insertion->("jn", 654}"""
cols = ['name', 'id']

print("Test 1 (user's exact image):", test_extract(query1, cols))

# Test with 5 records, mixed brackets:
query2 = """insert 5 records:
("a", 1),
{"b", 2},
["c", 3],
("d", 4},
("e", 5)"""
print("Test 2 (5 records mixed brackets):", test_extract(query2, cols))

# Test with line-by-line without brackets:
query3 = """
insertion-> "hb", 54
insertion-> "jn", 654
"""
print("Test 3 (no brackets):", test_extract(query3, cols))

# Test single row:
query4 = 'insert ("Alice", 25)'
print("Test 4 (single row):", test_extract(query4, cols))
