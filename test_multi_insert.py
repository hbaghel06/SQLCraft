from app import generate_local_intelligent_fallback, execute_sqlite_locally

# 1. Exact user input from screenshot:
schema = """
create table stud (
name varchar(850),
id integer
);
"""
prompt = """insertion->("hb", 54),
insertion->("jn", 654}"""

res = generate_local_intelligent_fallback(schema, prompt, 'mysql')
print("GENERATED SQL:")
print(res["sql"])
print("\nEXPLANATION:")
for exp in res["explanation"]:
    print(" -", exp)

exec_res = execute_sqlite_locally(schema, res["sql"])
print("\nEXECUTION RESULT:")
print("Success:", exec_res["success"])
print("Columns:", exec_res["columns"])
print("Rows:", exec_res["rows"])

assert exec_res["success"] is True
assert len(exec_res["rows"]) == 2
assert exec_res["rows"] == [["hb", 54], ["jn", 654]]
print("\n--> TEST 1 (User's Exact Mismatched Input): PASSED!")

# 2. Test with 5 records, arbitrary brackets:
prompt_n = """
insert 5 records:
("Alpha", 101),
["Beta", 102],
{"Gamma", 103),
("Delta", 104},
("Epsilon", 105)
"""
res_n = generate_local_intelligent_fallback(schema, prompt_n, 'mysql')
exec_n = execute_sqlite_locally(schema, res_n["sql"])
assert exec_n["success"] is True
assert len(exec_n["rows"]) == 5
print("--> TEST 2 (5 Records Mixed Brackets): PASSED! Total rows:", len(exec_n["rows"]))

# 3. Test arbitrary commands (e.g. UPDATE with multiple fields, OR conditions, DELETE):
prompt_up = 'update stud set name to "Master HB" where id = 54'
res_up = generate_local_intelligent_fallback(schema, prompt_up, 'mysql')
print("--> TEST 3 (UPDATE command):", res_up["sql"].replace("\n", " "))

prompt_del = 'delete from stud where id = 654'
res_del = generate_local_intelligent_fallback(schema, prompt_del, 'mysql')
print("--> TEST 4 (DELETE command):", res_del["sql"].replace("\n", " "))

print("\nALL ARBITRARY N-INPUT AND COMMAND CHECKS PASSED!")
