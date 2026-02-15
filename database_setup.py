import sqlite3
import datetime

def setup_database():
    """Create the database and tables with sample data."""
    
    # Connect to SQLite database (creates if doesn't exist)
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    
    # Create categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        budget_limit REAL DEFAULT 0.0
    )
    ''')
    
    # Create expenses table with foreign key constraint
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL CHECK(amount > 0),
        category_id INTEGER NOT NULL,
        description TEXT,
        date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')
    
    # Insert default categories with budgets if they don't exist
    default_categories = [
        (1, 'Food & Dining', 300.00),
        (2, 'Transportation', 150.00),
        (3, 'Entertainment', 100.00),
        (4, 'Shopping', 200.00),
        (5, 'Utilities', 250.00),
        (6, 'Healthcare', 100.00),
        (7, 'Education', 150.00),
        (8, 'Other', 50.00)
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO categories (id, name, budget_limit) 
    VALUES (?, ?, ?)
    ''', default_categories)
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("✅ Database 'expenses.db' created successfully!")
    print("✅ Tables 'categories' and 'expenses' initialized.")
    print("✅ Sample categories added.")
    print("\nYou can now run 'expense_tracker.py'")

if __name__ == "__main__":
    setup_database()
