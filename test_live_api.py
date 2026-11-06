"""
Live HTTP test against the running Flask server on http://127.0.0.1:5000
"""
import urllib.request
import json

url = "http://127.0.0.1:5000/api/generate-sql"
payload = {
    "schema": "CREATE TABLE stud (\n    name VARCHAR(20),\n    roll int,\n    dept VARCHAR(10)\n);",
    "query": 'show me the prompt for insertion of values ("hb", 23, "cse")',
    "dialect": "mysql"
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode("utf-8"))

print("=" * 60)
print("LIVE SERVER RESPONSE")
print("=" * 60)
print("\nGenerated SQL:")
print(result.get("sql", ""))
print("\nEngine:", result.get("source", ""))
print("\nExplanation:")
for e in result.get("explanation", []):
    print(f"  - {e}")
print("\nExecution Result:")
exec_r = result.get("execution", {})
print(f"  Success: {exec_r.get('success')}")
print(f"  Columns: {exec_r.get('columns')}")
print(f"  Rows:    {exec_r.get('rows')}")
print(f"  Message: {exec_r.get('message')}")
print("=" * 60)

# Assertions
assert "INSERT INTO stud (name, roll, dept)" in result["sql"], f"FAIL: Wrong SQL: {result['sql']}"
assert "('hb', 23, 'cse')" in result["sql"], f"FAIL: Values not found: {result['sql']}"
assert exec_r["success"] is True, f"FAIL: Execution failed: {exec_r['message']}"
assert exec_r["columns"] == ["name", "roll", "dept"], f"FAIL: Wrong columns: {exec_r['columns']}"
assert exec_r["rows"] == [["hb", 23, "cse"]], f"FAIL: Wrong rows: {exec_r['rows']}"

print("\nALL LIVE HTTP TESTS PASSED!")
