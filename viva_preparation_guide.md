# SQLCraft — Viva Voce Preparation & Examiner Q&A Guide
> **Academic Mini Project Evaluation Reference**  
> **Course:** B.Tech CSE (3rd Semester) | Pranveer Singh Institute of Technology (PSIT), Kanpur  

---

## 🎯 1. The 30-Second Elevator Pitch
*(Say this when the professor/external examiner asks: "Tell me about your project.")*

> *"Good morning/afternoon, Sir/Ma'am. My project is **SQLCraft**, an intelligent developer productivity and learning platform that translates conversational English questions into production-ready SQL queries for MySQL, PostgreSQL, and SQLite.*  
> *Unlike generic chatbots, SQLCraft is strictly grounded in the database schema you provide, eliminating hallucinations. It generates an educational, clause-by-clause explanation of why specific joins or aggregations were chosen, and it includes an in-memory SQLite sandbox that actually executes the query locally to display live result rows.*  
> *I built it using Python Flask, the Google Gemini API, SQLite, and a responsive Bootstrap 5 interface."*

---

## 💡 2. Top 10 Most Common Viva Questions & Model Answers

### Q1: Why not just use ChatGPT or a regular web chatbot?
**Answer:**  
*"ChatGPT is an ungrounded chat interface. In ChatGPT, users have to repeatedly paste their schema in every prompt, the output is conversational text that often contains markdown ticks or syntax errors, and it cannot execute the query.  
SQLCraft provides a dedicated schema manager, multi-dialect toggling (MySQL vs. Postgres), structured clause-by-clause educational breakdowns, one-click `.sql` and `JSON` file exports, and a live in-memory execution sandbox that verifies the query on real tables."*

---

### Q2: How did you ensure the AI outputs strict JSON without conversational text or code blocks?
**Answer:**  
*"I used two layers of defense:  
1. At the API level, I configured `types.GenerateContentConfig(response_mime_type='application/json')` using the official `google-genai` SDK, which forces the model at the decoding level to emit valid JSON.  
2. At the application layer in `app.py`, I implemented `extract_and_parse_json()` with regular expression pattern matching that automatically strips markdown fences (like ````json) and extracts the valid `{...}` payload to eliminate JSON decode errors."*

---

### Q3: How do you prevent hallucinations (inventing tables or columns that don't exist)?
**Answer:**  
*"Through Context Injection and System Instructions. In our system prompt, we explicitly instruct the model: 'Only use tables and columns specified in the schema. Do not hallucinate columns.' Because the schema DDL is supplied as structural context alongside the query, the model's attention is constrained strictly to the defined relational entities."*

---

### Q4: Why did you use an in-memory SQLite sandbox instead of connecting to a real MySQL server?
**Answer:**  
*"Portability, speed, and security. By utilizing Python's built-in `sqlite3.connect(':memory:')`, SQLCraft can spin up an isolated, zero-latency database sandbox in RAM on any machine without requiring the user or evaluator to install, configure, or maintain a local MySQL or Oracle database service. It runs instantly anywhere."*

---

### Q5: What is the technical difference between the `WHERE` clause and the `HAVING` clause in SQL?
*(Professors frequently ask this DBMS core question!)*  
**Answer:**  
*"The `WHERE` clause filters individual records **before** any grouping or aggregation takes place. The `HAVING` clause filters aggregated groups **after** the `GROUP BY` clause has been applied. For example, `WHERE score > 50` filters individual rows, whereas `HAVING AVG(score) > 75` filters aggregated student groups."*

---

### Q6: What is the difference between `INNER JOIN` and `LEFT JOIN`?
**Answer:**  
*"An `INNER JOIN` returns only records that have matching values in both tables. A `LEFT JOIN` returns all records from the left table, and the matched records from the right table; if there is no match, the right side returns `NULL` values. For example, to find students who haven't enrolled in courses, we use a `LEFT JOIN` and check `WHERE course_id IS NULL`."*

---

### Q7: What happens if there is no internet connection during the evaluation?
**Answer:**  
*"SQLCraft is designed with a zero-failure architecture. If the API key is absent or internet connectivity drops, `app.py` catches the exception and immediately falls back to its built-in Local Rule Engine. The demo continues smoothly, generating standard benchmark queries and executing live tables in SQLite without crashing."*

---

### Q8: What are the main components of your technology stack?
**Answer:**  
* **Frontend:** HTML5, CSS3, Twitter Bootstrap 5.3, JavaScript (Fetch API, DOM manipulation, LocalStorage).
* **Backend:** Python 3.10+ with Flask (REST API) and Flask-CORS.
* **Database & Sandbox:** SQLite3 (in-memory relational execution).
* **AI Engine:** Google Gemini API (`gemini-2.0-flash` / `gemini-1.5-flash`).
* **Environment Tools:** `python-dotenv` for configuration and PowerShell/Batch scripting for 1-click execution.

---

### Q9: Can SQLCraft handle different SQL dialects?
**Answer:**  
*"Yes. Relational database engines have distinct dialect variations—for example, string concatenation (`CONCAT()` in MySQL vs. `||` in PostgreSQL/SQLite) and pagination syntax (`LIMIT/OFFSET` in MySQL/PostgreSQL vs. `FETCH FIRST` in Oracle/SQL Server). SQLCraft includes a dialect selector that prompts the model to enforce engine-specific syntax."*

---

### Q10: What is the future scope of this project?
**Answer:**  
* Connecting to live remote enterprise databases (PostgreSQL/MySQL) via connection strings.
* Adding a Query Cost & Index Analyzer (`EXPLAIN ANALYZE`) to suggest database performance optimizations.
* Integrating voice-to-text input using the Web Speech API for hands-free query creation.

---

## 🎬 3. Flawless 3-Step Live Demo Protocol
During your presentation, follow this sequence:

1. **Step 1 (Launch):** Double-click `run_sqlcraft.bat`. Show the dark-themed UI loading automatically in the browser.
2. **Step 2 (Preset Demonstration):**
   * Keep the default **"College / University"** schema preset.
   * In Quick Prompts, select: *"Top 3 students by avg score"*.
   * Click **"Synthesize SQL & Test Locally"**.
   * Show the generated SQL with `JOIN`, `GROUP BY`, and `HAVING`.
   * Scroll down and show the **Clause-by-Clause Execution Breakdown**.
3. **Step 3 (Live Sandbox Proof):**
   * Click on the **"Live Sandbox Output"** tab.
   * Point out the live table with student names (`Aarav Sharma`, `Priya Patel`) and average scores.
   * Click the **"Copy"** or **".SQL"** button to demonstrate export capability.
