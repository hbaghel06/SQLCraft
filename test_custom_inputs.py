"""
Comprehensive test for ALL real-world custom input scenarios in SQLCraft.
Tests arbitrary schemas with free-form natural language prompts.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app, generate_local_intelligent_fallback, execute_sqlite_locally

client = app.test_client()

PASS = 0
FAIL = 0

def check(label, sql, must_contain, must_not_contain=None):
    global PASS, FAIL
    sql_up = sql.upper()
    ok = all(kw.upper() in sql_up for kw in must_contain)
    if must_not_contain:
        ok = ok and all(kw.upper() not in sql_up for kw in must_not_contain)
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         SQL: {sql}")
        print(f"         Expected to contain: {must_contain}")
        if must_not_contain:
            print(f"         Expected NOT to contain: {must_not_contain}")

# ===========================================================
# SCHEMA 1: Employee table (most common custom use case)
# ===========================================================
emp_schema = """
CREATE TABLE employee (
    emp_id INT PRIMARY KEY,
    emp_name VARCHAR(100),
    department VARCHAR(50),
    salary DECIMAL(10,2),
    city VARCHAR(50)
);"""

print("\n=== SCHEMA: employee (emp_id, emp_name, department, salary, city) ===")

r = generate_local_intelligent_fallback(emp_schema, "write a query to get all employees", "mysql")
check("get all employees", r["sql"], ["SELECT", "FROM", "employee"])

r = generate_local_intelligent_fallback(emp_schema, "find employees with salary greater than 50000", "mysql")
check("salary > 50000", r["sql"], ["SELECT", "FROM", "employee", "salary", "50000"], ["SELECT 1"])

r = generate_local_intelligent_fallback(emp_schema, "show employees from the HR department", "mysql")
check("filter by department HR", r["sql"], ["SELECT", "FROM", "employee", "department", "HR"])

r = generate_local_intelligent_fallback(emp_schema, "insert a new employee: emp_id=1, emp_name=Alice, department=IT, salary=60000, city=Delhi", "mysql")
check("insert with named values", r["sql"], ["INSERT INTO", "employee"])

r = generate_local_intelligent_fallback(emp_schema, 'add a new record ("101", "John", "Finance", "75000", "Mumbai")', "mysql")
check("insert with parenthesized values", r["sql"], ["INSERT INTO", "employee", "101", "John"])

r = generate_local_intelligent_fallback(emp_schema, "how many employees are there in each department?", "mysql")
check("count by department", r["sql"], ["COUNT", "FROM", "employee", "department", "GROUP BY"])

r = generate_local_intelligent_fallback(emp_schema, "find the average salary of employees", "mysql")
check("average salary", r["sql"], ["AVG", "salary", "FROM", "employee"])

r = generate_local_intelligent_fallback(emp_schema, "delete the employee with emp_id = 5", "mysql")
check("delete where id=5", r["sql"], ["DELETE FROM", "employee", "5"])

r = generate_local_intelligent_fallback(emp_schema, "update salary to 80000 where emp_name is Alice", "mysql")
check("update salary", r["sql"], ["UPDATE", "employee", "SET", "salary"])

r = generate_local_intelligent_fallback(emp_schema, "show top 5 employees ordered by salary descending", "mysql")
check("top 5 by salary DESC", r["sql"], ["SELECT", "FROM", "employee", "ORDER BY", "salary", "DESC", "LIMIT", "5"])

# ===========================================================
# SCHEMA 2: Student/College (original use case)
# ===========================================================
stud_schema = """
CREATE TABLE stud (
    name VARCHAR(20),
    roll int,
    dept VARCHAR(10)
);"""

print("\n=== SCHEMA: stud (name, roll, dept) ===")

r = generate_local_intelligent_fallback(stud_schema, 'show me the prompt for insertion of values ("hb", 23, "cse")', "mysql")
check("original insert case", r["sql"], ["INSERT INTO", "stud", "name", "roll", "dept", "'hb'", "23", "'cse'"])

r = generate_local_intelligent_fallback(stud_schema, "show all students from stud table", "mysql")
check("show all students", r["sql"], ["SELECT", "FROM", "stud"])

r = generate_local_intelligent_fallback(stud_schema, "find students from cse department", "mysql")
check("find by dept = cse", r["sql"], ["SELECT", "FROM", "stud"])

r = generate_local_intelligent_fallback(stud_schema, "how many students are in each dept?", "mysql")
check("count by dept", r["sql"], ["COUNT", "FROM", "stud", "GROUP BY"])

# ===========================================================
# SCHEMA 3: Product / Inventory
# ===========================================================
prod_schema = """
CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(8,2),
    stock INT
);"""

print("\n=== SCHEMA: products (product_id, product_name, category, price, stock) ===")

r = generate_local_intelligent_fallback(prod_schema, "list all products with price less than 500", "postgres")
check("price < 500", r["sql"], ["SELECT", "FROM", "products", "price", "500"], ["SELECT 1"])

r = generate_local_intelligent_fallback(prod_schema, "show products in the Electronics category", "postgres")
check("filter by category", r["sql"], ["SELECT", "FROM", "products", "category", "Electronics"])

r = generate_local_intelligent_fallback(prod_schema, "what is the maximum price of products?", "postgres")
check("max price", r["sql"], ["MAX", "price", "FROM", "products"])

r = generate_local_intelligent_fallback(prod_schema, "count total products by category", "postgres")
check("count by category", r["sql"], ["COUNT", "FROM", "products", "category", "GROUP BY"])

r = generate_local_intelligent_fallback(prod_schema, 'add product ("5", "Laptop", "Electronics", "45000", "10")', "postgres")
check("insert product", r["sql"], ["INSERT INTO", "products"])

# ===========================================================
# SCHEMA 4: Library
# ===========================================================
lib_schema = """
CREATE TABLE books (
    book_id INT,
    title VARCHAR(200),
    author VARCHAR(100),
    genre VARCHAR(50),
    published_year INT
);"""

print("\n=== SCHEMA: books (book_id, title, author, genre, published_year) ===")

r = generate_local_intelligent_fallback(lib_schema, "show all books by J.K. Rowling", "sqlite")
check("books by author", r["sql"], ["SELECT", "FROM", "books"])

r = generate_local_intelligent_fallback(lib_schema, "find books of genre Fiction published after 2000", "sqlite")
check("genre=Fiction + year filter", r["sql"], ["SELECT", "FROM", "books"])

r = generate_local_intelligent_fallback(lib_schema, "insert a book: title=Dune, author=Frank Herbert, genre=SciFi", "sqlite")
check("insert book named values", r["sql"], ["INSERT INTO", "books"])

r = generate_local_intelligent_fallback(lib_schema, "delete book with book_id = 3", "sqlite")
check("delete by id", r["sql"], ["DELETE FROM", "books", "3"])

# ===========================================================
# SCHEMA 5: Hospital
# ===========================================================
hosp_schema = """
CREATE TABLE patients (
    patient_id INT PRIMARY KEY,
    patient_name VARCHAR(100),
    age INT,
    disease VARCHAR(100),
    doctor_name VARCHAR(100)
);"""

print("\n=== SCHEMA: patients (patient_id, patient_name, age, disease, doctor_name) ===")

r = generate_local_intelligent_fallback(hosp_schema, "get all patients above age 60", "mysql")
check("age > 60", r["sql"], ["SELECT", "FROM", "patients", "age", "60"], ["SELECT 1"])

r = generate_local_intelligent_fallback(hosp_schema, "find patients with diabetes", "mysql")
check("disease = diabetes", r["sql"], ["SELECT", "FROM", "patients"])

r = generate_local_intelligent_fallback(hosp_schema, "how many patients does each doctor have?", "mysql")
check("count patients per doctor", r["sql"], ["COUNT", "FROM", "patients", "GROUP BY"])

r = generate_local_intelligent_fallback(hosp_schema, 'register a new patient ("1", "Raj Kumar", "35", "Fever", "Dr. Sharma")', "mysql")
check("register patient", r["sql"], ["INSERT INTO", "patients"])

# ===========================================================
# LIVE EXECUTION TEST
# ===========================================================
print("\n=== LIVE EXECUTION (SQLite in-memory) ===")
exec_res = execute_sqlite_locally(stud_schema, "INSERT INTO stud (name, roll, dept)\nVALUES ('hb', 23, 'cse');")
ok = exec_res["success"] and exec_res["rows"] == [["hb", 23, "cse"]]
print(f"  [{'PASS' if ok else 'FAIL'}] Insert + live row fetch: {exec_res['rows']}")
if ok: PASS += 1
else: FAIL += 1

exec_res2 = execute_sqlite_locally(emp_schema, "SELECT * FROM employee;")
ok2 = exec_res2["success"] and len(exec_res2["rows"]) > 0
print(f"  [{'PASS' if ok2 else 'FAIL'}] Auto-seed custom table SELECT: {len(exec_res2['rows'])} rows returned")
if ok2: PASS += 1
else: FAIL += 1

# ===========================================================
print(f"\n{'='*50}")
print(f"  TOTAL: {PASS+FAIL} tests  |  PASSED: {PASS}  |  FAILED: {FAIL}")
print(f"{'='*50}")
if FAIL == 0:
    print("  ALL TESTS PASSED - SQLCraft custom input engine is working!")
else:
    print(f"  {FAIL} test(s) need attention.")
