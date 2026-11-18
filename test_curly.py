from app import generate_local_intelligent_fallback, execute_sqlite_locally

schema = """
create table stud (
name varchar(850),
id integer
);
"""

# Test 1: All curly brackets: {"hb", 54}, {"jn", 654}
prompt1 = """insertion->{"hb", 54},
insertion->{"jn", 654}"""

res1 = generate_local_intelligent_fallback(schema, prompt1, 'mysql')
print("SQL 1 (all curly):")
print(res1["sql"])
exec1 = execute_sqlite_locally(schema, res1["sql"])
print("Rows 1:", exec1["rows"])
assert len(exec1["rows"]) == 2
assert exec1["rows"] == [["hb", 54], ["jn", 654]]

# Test 2: Mismatched curly/round: ("hb", 54), ("jn", 654}
prompt2 = """insertion->("hb", 54),
insertion->("jn", 654}"""
res2 = generate_local_intelligent_fallback(schema, prompt2, 'mysql')
exec2 = execute_sqlite_locally(schema, res2["sql"])
assert len(exec2["rows"]) == 2
assert exec2["rows"] == [["hb", 54], ["jn", 654]]

# Test 3: N curly brackets (e.g. 4 rows)
prompt3 = """
{"user1", 10},
{"user2", 20},
{"user3", 30},
{"user4", 40}
"""
res3 = generate_local_intelligent_fallback(schema, prompt3, 'mysql')
exec3 = execute_sqlite_locally(schema, res3["sql"])
assert len(exec3["rows"]) == 4

print("\nALL CURLY BRACKETS & N-ROW TESTS PASSED 100%!")
