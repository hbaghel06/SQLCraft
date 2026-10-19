-- =====================================================================
-- SQLCraft: Benchmark Database Schemas & Sample Seed Data
-- Designed for Relational DBMS Evaluation & Live Demonstration
-- Institution: Pranveer Singh Institute of Technology (PSIT), Kanpur
-- =====================================================================

-- ---------------------------------------------------------------------
-- DATABASE SCHEMA 1: College / University Management System
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS marks;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    dept_id INT PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL
);

CREATE TABLE students (
    student_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dept_id INT,
    enrollment_year INT,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

CREATE TABLE courses (
    course_id INT PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL
);

CREATE TABLE marks (
    mark_id INT PRIMARY KEY,
    student_id INT,
    course_id INT,
    score DECIMAL(5,2),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Seed Data for College Schema
INSERT INTO departments (dept_id, dept_name) VALUES
(1, 'Computer Science & Engineering'),
(2, 'Information Technology'),
(3, 'Electronics & Communication');

INSERT INTO students (student_id, name, dept_id, enrollment_year) VALUES
(101, 'Aarav Sharma', 1, 2024),
(102, 'Priya Patel', 1, 2024),
(103, 'Rohan Verma', 2, 2023),
(104, 'Sneha Gupta', 3, 2024),
(105, 'Vikram Singh', 1, 2023);

INSERT INTO courses (course_id, course_name, credits) VALUES
(201, 'Database Management Systems', 4),
(202, 'Operating Systems', 4),
(203, 'Computer Networks', 3);

INSERT INTO marks (mark_id, student_id, course_id, score) VALUES
(1, 101, 201, 88.50),
(2, 101, 202, 92.00),
(3, 102, 201, 79.00),
(4, 102, 202, 85.00),
(5, 103, 201, 68.00),
(6, 105, 201, 94.50),
(7, 105, 202, 89.00);


-- ---------------------------------------------------------------------
-- DATABASE SCHEMA 2: E-Commerce & Retail Store System
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    city VARCHAR(50)
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    total_amount DECIMAL(10,2),
    status VARCHAR(20),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    item_id INT PRIMARY KEY,
    order_id INT,
    product_name VARCHAR(100),
    quantity INT,
    unit_price DECIMAL(10,2),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Seed Data for E-Commerce Schema
INSERT INTO customers (customer_id, name, email, city) VALUES
(1, 'Rahul Mehra', 'rahul@example.com', 'Delhi'),
(2, 'Ananya Roy', 'ananya@example.com', 'Mumbai'),
(3, 'Karan Johar', 'karan@example.com', 'Bangalore');

INSERT INTO orders (order_id, customer_id, order_date, total_amount, status) VALUES
(1001, 1, '2024-03-15', 4500.00, 'Delivered'),
(1002, 1, '2024-04-10', 1250.00, 'Delivered'),
(1003, 2, '2024-05-01', 8900.00, 'Shipped'),
(1004, 3, '2024-05-12', 320.00, 'Processing');
