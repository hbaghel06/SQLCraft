import json
from app import app

client = app.test_client()

schema = """
CREATE TABLE stud (
    name VARCHAR(20),
    roll int,
    dept VARCHAR(10)
);
"""
prompt = 'show me the prompt for insertion of values ("hb", 23, "cse")'

response = client.post('/api/generate-sql', json={
    'schema': schema,
    'query': prompt,
    'dialect': 'mysql'
})

print(f"Status Code: {response.status_code}")
data = response.get_json()
print("Generated SQL:\n" + data.get("sql", ""))
print("\nExplanation:")
for exp in data.get("explanation", []):
    print(f" - {exp}")
print("\nExecution Results:")
print(" Columns:", data.get("execution", {}).get("columns"))
print(" Rows:", data.get("execution", {}).get("rows"))
print(" Message:", data.get("execution", {}).get("message"))

assert response.status_code == 200
assert "INSERT INTO stud (name, roll, dept)" in data["sql"]
assert data["execution"]["success"] is True
assert data["execution"]["rows"] == [["hb", 23, "cse"]]
print("\nALL FLASK API ENDPOINT CHECKS PASSED PERFECTLY!")
