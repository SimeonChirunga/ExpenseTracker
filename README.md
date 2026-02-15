# Overview

This project is a console-based Expense Tracker built with Python and SQLite. It demonstrates how a relational database can be integrated into a practical software application to manage personal finances efficiently. The system allows users to perform full CRUD operations (Create, Read, Update, Delete) on expense records, categorize them, set budget limits, and generate spending summaries – all while maintaining data integrity through foreign key constraints and SQL transactions.

Purpose: 

As a software engineer, I developed this application to deepen my understanding of relational database design and SQL in a real-world context. By building a complete data-driven tool, I explored concepts such as:

- Database schema design (normalization, relationships)

- Parameterized queries to prevent SQL injection

- Error handling and transaction rollbacks

- Aggregation queries for reporting (GROUP BY, JOIN, CASE expressions)

- Integration of Python with SQLite using the built-in sqlite3 module

How to Use
Run the script – it will automatically create the database file (expenses.db) and populate default categories if none exist.

A menu with numbered options will appear. Enter the corresponding number to:
- Add a new expense (amount, category, optional description, date)
- View all expenses in a formatted table
- Update or delete existing expenses
- Search by category (ID or name), date range, or description keyword
- View spending summary per category (with budget tracking and percentage used)
- Generate a monthly report
- Export the full report to a text file.



[Software Demo Video](https://youtu.be/g0ocP0R72r4)

# Relational Database

The project uses SQLite, a lightweight, file-based relational database engine. SQLite was chosen because it requires no separate server setup, is self-contained, and integrates seamlessly with Python. All data is stored in a single file (expenses.db), which makes the application portable and easy to distribute.

Two tables were designed to model the expense tracking domain:

## Database Schema

### `categories` Table
| Column       | Type           | Description                                      |
|--------------|----------------|--------------------------------------------------|
| id           | INTEGER (PK)   | Auto-incrementing primary key                    |
| name         | TEXT (UNIQUE)  | Category name (e.g., Food, Transportation)       |
| budget_limit | DECIMAL(10,2)  | Monthly spending limit (0.00 means no limit)     |
| created_at   | TIMESTAMP      | Auto-populated creation timestamp                |

### `expenses` Table
| Column       | Type           | Description                                      |
|--------------|----------------|--------------------------------------------------|
| id           | INTEGER (PK)   | Auto-incrementing primary key                    |
| amount       | DECIMAL(10,2)  | Expense amount (must be > 0)                     |
| category_id  | INTEGER (FK)   | References `categories(id)`                      |
| description  | TEXT           | Optional description of the expense              |
| date         | DATE           | Date of the expense (YYYY-MM-DD)                 |
| created_at   | TIMESTAMP      | Auto-populated creation timestamp                |

Relationships:

A one-to-many relationship exists between categories and expenses: one category can have many expenses, but each expense belongs to exactly one category.

The foreign key category_id enforces referential integrity with ON DELETE CASCADE – deleting a category automatically removes all its associated expenses.

Indexes & Constraints:

The name column in categories is UNIQUE to prevent duplicate categories.
Primary keys are automatically indexed by SQLite.
Foreign key constraints are enabled at runtime via PRAGMA foreign_keys = ON.

# Development Environment

Tools:
Visual Studio Code (code editor)
SQLite command-line shell (for quick inspection)
Git for version control
Language: Python 3.10+

Libraries:
sqlite3 – built-in module for database operations
datetime – for handling dates (today’s date, formatting)
os – to check if the database file exists
typing – for type hints (improves code readability and maintainability)

# Useful Websites

{Make a list of websites that you found helpful in this project}

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python sqlite3 Module Documentation](https://docs.python.org/3/library/sqlite3.html)
- [Real Python – SQLite in Python](https://realpython.com/python-sqlite-sqlalchemy/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/sqlite)


# Future Work

{Make a list of things that you need to fix, improve, and add in the future.}

- Graphical User Interface (GUI) – Replace the console menu with a desktop (Tkinter/PyQt) or web (Flask) interface for easier data entry and visualization.
- Multiple user support – Add user authentication so the application can serve multiple individuals, each with their own categories and expenses.
- Cloud sync – Store the database in the cloud (e.g., using SQLite on cloud storage or migrating to a client‑server DB like PostgreSQL) for access across devices.
- Recurring expenses – Allow users to define recurring transactions that are automatically added each month.



