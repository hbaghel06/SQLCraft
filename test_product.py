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
print("\nAll Product-Ready Tests Passed Successfully!")
