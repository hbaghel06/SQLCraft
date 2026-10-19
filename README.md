# SQLCraft Studio

> **Natural Language to SQL Query Generator & Execution Explainer**  
> *Academic Mini Project & Developer Workbench*  
> **Institution:** Pranveer Singh Institute of Technology (PSIT), Kanpur  
> **Course:** B.Tech in Computer Science & Engineering (3rd Semester)  

---

## 📌 Overview
**SQLCraft** is a lightweight, web-based database productivity platform designed to bridge the gap between conversational human language and relational database management systems (RDBMS). 

Users provide a relational database schema and a plain-English request (e.g., *"Find the top 3 students by average score across all subjects"*). SQLCraft synthesizes production-ready SQL queries for **MySQL, PostgreSQL, and SQLite**, outputs a **clause-by-clause educational explanation**, and **executes the query locally** against an in-memory SQLite sandbox to display live tabular data rows.

---

## 🌟 Key Features

1. **Natural Language to SQL Synthesis (NL2SQL):**
   * Translates plain English business requirements into syntactically valid relational SQL queries.
   * Grounded strictly in user-supplied schemas to prevent hallucinated table or column names.

2. **Clause-by-Clause Logical Explanation:**
   * Educational breakdowns explaining *why* specific relational operators (`JOIN`, `GROUP BY`, `HAVING`, `ORDER BY`) were chosen.
   * Ideal for DBMS coursework and viva evaluations.

3. **Multi-Dialect Compatibility:**
   * Generates tailored syntax for **MySQL**, **PostgreSQL**, and **SQLite**.

4. **⚡ Live In-Memory SQLite Sandbox:**
   * Does not just generate text—actually executes the schema and query in an isolated in-memory SQLite database (`:memory:`).
   * Displays the real table rows, column headers, and record counts returned by the query.

5. **💾 One-Click Export Tools:**
   * **`Copy`**: Copies raw SQL to clipboard.
   * **`.SQL`**: Exports the query as a `.sql` file.
   * **`JSON`**: Exports the complete response object (SQL, explanations, execution metadata) as a `.json` file.

6. **🔄 Zero-Failure Local Fallback:**
   * Operates 100% offline using a built-in rule engine if the Gemini API key is not configured or if internet connectivity drops. Live project evaluations will never fail or throw 500 error screens.

---

## 🏗️ System Architecture

```
[ User Web Browser ] (HTML5 / Twitter Bootstrap 5 / Vanilla JS)
       │
       ▼ HTTP POST /api/generate-sql
[ Flask Backend Server (Python 3.10+) ]
       │
       ├──► [ Context Assembly & Schema Sanitizer ]
       │          │
       │          ├──► [ Google Gemini API ] (gemini-2.0-flash / gemini-1.5-flash)
       │          │           OR
       │          └──► [ SQLCraft Local Rule Engine ] (Offline Zero-Failure Fallback)
       │
       ├──► [ In-Memory SQLite Sandbox Engine ] (Live Execution & Row Generation)
       │
       ▼ Formatted JSON Response
[ Live UI Rendering ] (Syntax Code Block + Clause Breakdown + Live Data Table)
```

---

## 🚀 Quick Start Guide (Windows)

### Option A: 1-Click Launch (Recommended)
Simply double-click:
```
run_sqlcraft.bat
```
This automatically verifies Python, launches the local server, and opens `http://127.0.0.1:5000` in your default browser.

---

### Option B: Manual Command-Line Launch
1. Open PowerShell or Command Prompt in this folder:
   ```bash
   cd C:\Users\Dell\.gemini\antigravity\scratch\sqlcraft
   ```

2. Install dependencies (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Configure Gemini API Key:
   * Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env
     ```
   * Open `.env` and paste your free key from [Google AI Studio](https://aistudio.google.com/).  
   *(If skipped, SQLCraft will seamlessly run in local offline mode).*

4. Start the server:
   ```bash
   python app.py
   ```

5. Open your browser at:
   ```
   http://127.0.0.1:5000
   ```

---

## 🧪 Benchmark Test Cases for Live Demonstration

| # | Selected Preset | Natural Language Prompt | Expected SQL Clauses Tested |
|---|---|---|---|
| **1** | **College Management** | *"Find top 3 students by average score across all subjects."* | `JOIN`, `GROUP BY`, `AVG()`, `HAVING`, `ORDER BY DESC`, `LIMIT` |
| **2** | **College Management** | *"Count how many students are enrolled in each department."* | `LEFT JOIN`, `COUNT()`, `GROUP BY`, `ORDER BY` |
| **3** | **College Management** | *"List students who have not enrolled in any course yet."* | `LEFT JOIN ... WHERE marks.mark_id IS NULL` |
| **4** | **E-Commerce Store** | *"Show total amount spent and order count per customer."* | `JOIN`, `COUNT()`, `SUM()`, `GROUP BY`, `ORDER BY` |

---

## 📁 Repository Structure
```
sqlcraft/
├── app.py                   # Flask server, JSON parser, SQLite sandbox, Gemini client
├── requirements.txt         # Project dependencies
├── .env.example             # Environment configuration template
├── run_sqlcraft.bat         # 1-Click Windows launcher script
├── sample_database.sql      # Standalone SQL schema & seed data dump
├── test_product.py          # Automated verification test suite
├── README.md                # Project documentation
├── viva_preparation_guide.md# Viva Voce preparation & examiner Q&A cheat-sheet
└── templates/
    └── index.html           # Bootstrap 5 responsive UI (Tabs, Sandbox Table, History)
```

---

## 📄 License & Academic Attribution
Developed as an individual academic mini-project by **CSE 3rd Semester Students** at **Pranveer Singh Institute of Technology (PSIT), Kanpur**.  
Licensed under the **MIT License**.
