from app import generate_local_intelligent_fallback, execute_sqlite_locally

schema = """
create table dod (
name varchar(50),
id int
);
"""
prompt = 'insertion of values --> ("hb", 1), ("db", 5)'

res = generate_local_intelligent_fallback(schema, prompt, 'mysql')
print("SQL:\n" + res["sql"])

exec_res = execute_sqlite_locally(schema, res["sql"])
print("\nEXEC RESULT:")
print("Success:", exec_res["success"])
print("Columns:", exec_res["columns"])
print("Rows:", exec_res["rows"])

assert exec_res["success"] is True
assert len(exec_res["rows"]) == 2
assert exec_res["rows"] == [["hb", 1], ["db", 5]]
print("\nTEST PASSED PERFECTLY!")
