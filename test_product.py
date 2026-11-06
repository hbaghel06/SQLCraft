import json
from app import extract_and_parse_json, generate_local_intelligent_fallback, execute_sqlite_locally

# 1. Test markdown-wrapped JSON extraction
raw_llm_output = """```json
{
  "sql": "SELECT * FROM students;",
  "explanation": ["Selects all columns from the students table."]
}
```"""

parsed = extract_and_parse_json(raw_llm_output)
assert parsed["sql"] == "SELECT * FROM students;"
print("Test 1: JSON Markdown extraction passed!")

# 2. Test local intelligent fallback
fallback = generate_local_intelligent_fallback(
    "CREATE TABLE students (student_id INT, name VARCHAR(100));",
    "Find top 3 students by average score",
    "mysql"
)
assert "SELECT" in fallback["sql"]
print("Test 2: Local engine fallback passed!")

# 3. Test SQLite local sandbox execution
schema = """
CREATE TABLE students (student_id INT PRIMARY KEY, name VARCHAR(100), dept_id INT, enrollment_year INT);
CREATE TABLE marks (mark_id INT PRIMARY KEY, student_id INT, course_id INT, score DECIMAL(5,2));
"""
query = "SELECT s.name, AVG(m.score) as avg_score FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.name;"
exec_res = execute_sqlite_locally(schema, query)
assert exec_res["success"] is True
assert len(exec_res["columns"]) == 2
assert len(exec_res["rows"]) > 0
print(f"Test 3: SQLite sandbox passed! Returned {len(exec_res['rows'])} live rows: {exec_res['rows']}")

# 4. Test Custom Schema and Custom Insertion
custom_schema = """
CREATE TABLE stud (
    name VARCHAR(20),
    roll int,
    dept VARCHAR(10)
);
"""
custom_query = 'show me the prompt for insertion of values ("hb", 23, "cse")'
custom_fallback = generate_local_intelligent_fallback(custom_schema, custom_query, "mysql")
print("\nGenerated SQL for Custom Input:")
print(custom_fallback["sql"])
assert "INSERT INTO stud" in custom_fallback["sql"]
assert "'hb'" in custom_fallback["sql"]
assert "23" in custom_fallback["sql"]
assert "'cse'" in custom_fallback["sql"]
print("Test 4a: Custom SQL generation passed!")

custom_exec = execute_sqlite_locally(custom_schema, custom_fallback["sql"])
assert custom_exec["success"] is True
assert custom_exec["columns"] == ["name", "roll", "dept"]
assert len(custom_exec["rows"]) == 1
assert custom_exec["rows"][0] == ["hb", 23, "cse"]
print(f"Test 4b: Custom SQLite execution passed! Row: {custom_exec['rows'][0]}")

# 5. Test Custom Schema SELECT on empty table (auto-seeding)
select_query = "show all students from stud"
select_fallback = generate_local_intelligent_fallback(custom_schema, select_query, "postgres")
select_exec = execute_sqlite_locally(custom_schema, select_fallback["sql"])
assert select_exec["success"] is True
assert select_exec["columns"] == ["name", "roll", "dept"]
assert len(select_exec["rows"]) > 0
print(f"Test 5: Custom SELECT auto-seeding passed! Rows: {select_exec['rows']}")

print("\nAll Product-Ready Tests (Standard + Custom) Passed Successfully!")
