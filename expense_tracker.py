# Importing needed modules
import sqlite3      # For SQLite database operations
import datetime     # For handling dates
import os           # For file/directory operations (checking if database exists)
from typing import Optional, List, Tuple   # Type hints for better code clarity

# ============================================
# ExpenseTracker Class
# ============================================
class ExpenseTracker:
    """
    A class that manages all expense tracking operations.
    It connects to an SQLite database and provides methods for CRUD,
    filtering, reporting, and exporting.
    """
    
    def __init__(self, db_path: str = 'expenses.db'):
        """
        Constructor: Initializes the tracker with a database path.
        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path          # Store database file path
        self.conn = None                # Database connection object (initially None)
        self.cursor = None              # Database cursor (initially None)
        self.connect_db()               # Immediately establish a connection

    def connect_db(self):
        """
        Establish a connection to the SQLite database.
        Sets row_factory to sqlite3.Row for dictionary-like access,
        creates a cursor, and enables foreign key constraints.
        """
        try:
            # Connect to the database file (creates file if it doesn't exist)
            self.conn = sqlite3.connect(self.db_path)
            # Set row factory FIRST: rows can be accessed by column name (like a dict)
            self.conn.row_factory = sqlite3.Row
            # Create a cursor object to execute SQL commands
            self.cursor = self.conn.cursor()
            # Enable foreign key constraints for this connection
            self.cursor.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            # If connection fails, print error and re-raise to stop execution
            print(f" Database connection error: {e}")
            raise

    def close_db(self):
        """
        Close the database connection if it's open.
        Called when done using the tracker.
        """
        if self.conn:
            self.conn.close()

    # ========== CORE CRUD OPERATIONS ==========
    
    def add_expense(self, amount: float, category_id: int, 
                   description: str = "", date: str = None) -> bool:
        """
        Insert a new expense record into the database.
        :param amount: Expense amount (must be > 0)
        :param category_id: ID of the category this expense belongs to
        :param description: Optional description text
        :param date: Date in 'YYYY-MM-DD' format. If None, use today.
        :return: True if successful, False otherwise.
        """
        # Validate that amount is positive
        if amount <= 0:
            print(" Amount must be greater than 0")
            return False
        
        # If no date provided, use today's date in ISO format
        if not date:
            date = datetime.date.today().isoformat()
        
        try:
            # First, verify that the category exists in the categories table
            self.cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
            if not self.cursor.fetchone():
                print(f" Category ID {category_id} does not exist")
                return False
            
            # Use a parameterized query to insert the new expense safely (prevents SQL injection)
            self.cursor.execute('''
                INSERT INTO expenses (amount, category_id, description, date)
                VALUES (?, ?, ?, ?)
            ''', (amount, category_id, description, date))
            
            # Commit the transaction to make changes permanent
            self.conn.commit()
            print(f"Expense of ${amount:.2f} added successfully!")
            
            # After adding, check if this category's budget is exceeded or nearly exceeded
            self.check_budget_limit(category_id)
            
            return True
            
        except sqlite3.Error as e:
            # If any database error occurs, print it and rollback any changes
            print(f" Error adding expense: {e}")
            self.conn.rollback()
            return False
    
    def view_all_expenses(self, limit: int = 50) -> List[sqlite3.Row]:
        """
        Retrieve all expenses with category names, ordered by date (most recent first).
        :param limit: Maximum number of records to return.
        :return: List of sqlite3.Row objects (each row acts like a dictionary).
        """
        try:
            # Perform a JOIN to get the category name from the categories table
            self.cursor.execute('''
                SELECT e.id, e.amount, c.name as category, 
                       e.description, e.date, e.created_at
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                ORDER BY e.date DESC, e.created_at DESC
                LIMIT ?
            ''', (limit,))
            
            # Fetch all rows and return them as a list
            expenses = self.cursor.fetchall()
            return expenses
            
        except sqlite3.Error as e:
            print(f"Error retrieving expenses: {e}")
            return []
    
    def update_expense(self, expense_id: int, amount: float = None,
                      category_id: int = None, description: str = None,
                      date: str = None) -> bool:
        """
        Modify an existing expense record.
        Only fields that are provided (not None) will be updated.
        :param expense_id: ID of the expense to update.
        :param amount: New amount (if provided).
        :param category_id: New category ID (if provided).
        :param description: New description (if provided).
        :param date: New date (if provided).
        :return: True if successful, False otherwise.
        """
        try:
            # Build a dynamic list of SET clauses and corresponding parameter values
            updates = []
            params = []
            
            if amount is not None:
                # Validate amount
                if amount <= 0:
                    print("Amount must be greater than 0")
                    return False
                updates.append("amount = ?")
                params.append(amount)
            
            if category_id is not None:
                # Validate that the new category exists
                self.cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
                if not self.cursor.fetchone():
                    print(f" Category ID {category_id} does not exist")
                    return False
                updates.append("category_id = ?")
                params.append(category_id)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if date is not None:
                updates.append("date = ?")
                params.append(date)
            
            # If no fields were provided, nothing to update
            if not updates:
                print(" No fields to update")
                return False
            
            # Add the expense_id as the last parameter for the WHERE clause
            params.append(expense_id)
            
            # Build the full UPDATE query with the dynamic SET clauses
            query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            
            # rowcount indicates how many rows were affected. If 0, the expense ID didn't exist.
            if self.cursor.rowcount == 0:
                print(f" No expense found with ID {expense_id}")
                return False
            
            # Commit the changes
            self.conn.commit()
            print(f"✅ Expense ID {expense_id} updated successfully!")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error updating expense: {e}")
            self.conn.rollback()
            return False
    
    def delete_expense(self, expense_id: int) -> bool:
        """
        Remove an expense record from the database.
        :param expense_id: ID of the expense to delete.
        :return: True if successful, False otherwise.
        """
        try:
            # Execute DELETE statement with parameterized ID
            self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            
            # Check if any row was actually deleted
            if self.cursor.rowcount == 0:
                print(f" No expense found with ID {expense_id}")
                return False
            
            # Commit the deletion
            self.conn.commit()
            print(f" Expense ID {expense_id} deleted successfully!")
            return True
            
        except sqlite3.Error as e:
            print(f" Error deleting expense: {e}")
            self.conn.rollback()
            return False
    
    # ========== QUERY OPERATIONS ==========
    
    def search_by_category(self, category_id: int = None, 
                          category_name: str = None) -> List[sqlite3.Row]:
        """
        Search for expenses by category ID or category name.
        :param category_id: Direct category ID.
        :param category_name: Category name (partial match, case-insensitive).
        :return: List of matching expenses.
        """
        try:
            # If category_name is provided, resolve it to an ID first
            if category_name:
                # Use LIKE for partial, case-insensitive matching
                self.cursor.execute(
                    "SELECT id FROM categories WHERE name LIKE ?", 
                    (f"%{category_name}%",)
                )
                result = self.cursor.fetchone()
                if not result:
                    print(f" No category found with name '{category_name}'")
                    return []
                # Get the ID from the result row (using dictionary-like access)
                category_id = result['id']
            
            # Now search expenses by that category ID
            self.cursor.execute('''
                SELECT e.id, e.amount, c.name as category, 
                       e.description, e.date
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.category_id = ?
                ORDER BY e.date DESC
            ''', (category_id,))
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f" Error searching by category: {e}")
            return []
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> List[sqlite3.Row]:
        """
        Retrieve expenses that occurred between start_date and end_date (inclusive).
        :param start_date: Start date in 'YYYY-MM-DD' format.
        :param end_date: End date in 'YYYY-MM-DD' format.
        :return: List of matching expenses.
        """
        try:
            # Use BETWEEN operator for inclusive range
            self.cursor.execute('''
                SELECT e.id, e.amount, c.name as category, 
                       e.description, e.date
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.date BETWEEN ? AND ?
                ORDER BY e.date DESC
            ''', (start_date, end_date))
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f" Error filtering by date: {e}")
            return []
    
    def search_by_description(self, keyword: str) -> List[sqlite3.Row]:
        """
        Search expenses whose description contains the given keyword.
        :param keyword: Search term (case-insensitive partial match).
        :return: List of matching expenses.
        """
        try:
            # Use LIKE with wildcards around the keyword
            self.cursor.execute('''
                SELECT e.id, e.amount, c.name as category, 
                       e.description, e.date
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.description LIKE ?
                ORDER BY e.date DESC
            ''', (f"%{keyword}%",))
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f" Error searching by description: {e}")
            return []
    
    # ========== DATA ANALYSIS & REPORTING ==========
    
    def get_spending_summary(self) -> List[sqlite3.Row]:
        """
        Generate a spending summary per category, including transaction count,
        total spent, budget limit, remaining budget, and percentage used.
        :return: List of summary rows.
        """
        try:
            # Use GROUP BY to aggregate per category
            # LEFT JOIN ensures categories with no expenses are still shown (with zeros)
            # CASE expression calculates percentage only if budget_limit > 0
            self.cursor.execute('''
                SELECT 
                    c.name as category,
                    COUNT(e.id) as transaction_count,
                    SUM(e.amount) as total_spent,
                    c.budget_limit,
                    (c.budget_limit - SUM(e.amount)) as remaining_budget,
                    CASE 
                        WHEN c.budget_limit > 0 THEN 
                            ROUND((SUM(e.amount) / c.budget_limit) * 100, 2)
                        ELSE 0 
                    END as percent_used
                FROM categories c
                LEFT JOIN expenses e ON c.id = e.category_id
                GROUP BY c.id, c.name, c.budget_limit
                ORDER BY total_spent DESC
            ''')
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f" Error generating spending summary: {e}")
            return []
    
    def get_monthly_spending(self, year: int = None, month: int = None) -> List[sqlite3.Row]:
        """
        Generate a monthly spending report for a specific year and month.
        :param year: Year (e.g., 2026). If None, use current year.
        :param month: Month (1-12). If None, use current month.
        :return: List of category totals for that month.
        """
        try:
            # Default to current year/month if not provided
            if year is None:
                year = datetime.date.today().year
            if month is None:
                month = datetime.date.today().month
            
            # Use strftime to extract year and month from the date column
            self.cursor.execute('''
                SELECT 
                    c.name as category,
                    SUM(e.amount) as monthly_total,
                    COUNT(e.id) as transaction_count
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE strftime('%Y', e.date) = ? 
                  AND strftime('%m', e.date) = ?
                GROUP BY c.id, c.name
                ORDER BY monthly_total DESC
            ''', (str(year), f"{month:02d}"))  # month formatted with leading zero
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f" Error generating monthly report: {e}")
            return []
    
    def get_total_spending(self) -> float:
        """
        Calculate the total amount spent across all expenses.
        :return: Total sum as float, or 0.0 if no expenses.
        """
        try:
            self.cursor.execute('SELECT SUM(amount) as total FROM expenses')
            result = self.cursor.fetchone()
            # result is a sqlite3.Row; we can access by column name
            if result and result['total'] is not None:
                return float(result['total'])
            return 0.0
        except sqlite3.Error as e:
            print(f" Error calculating total spending: {e}")
            return 0.0
    
    # ========== HELPER FUNCTIONS ==========
    
    def check_budget_limit(self, category_id: int):
        """
        Check if total spending for a given category exceeds or nears its budget limit.
        Prints warnings if over budget or over 90% of budget.
        :param category_id: The category to check.
        """
        try:
            # Query to get category name, budget limit, and total spent
            self.cursor.execute('''
                SELECT 
                    c.name,
                    c.budget_limit,
                    COALESCE(SUM(e.amount), 0) as spent
                FROM categories c
                LEFT JOIN expenses e ON c.id = e.category_id
                WHERE c.id = ?
                GROUP BY c.id
            ''', (category_id,))
            
            result = self.cursor.fetchone()
            # Only check if budget_limit is greater than 0 (i.e., a budget is set)
            if result and result['budget_limit'] > 0:
                spent = result['spent'] or 0
                if spent > result['budget_limit']:
                    print(f"  Warning: You've exceeded the budget for {result['name']}!")
                    print(f"   Budget: ${result['budget_limit']:.2f}, Spent: ${spent:.2f}")
                elif spent > result['budget_limit'] * 0.9:
                    print(f"  Warning: You're close to exceeding the budget for {result['name']}")
                    
        except sqlite3.Error as e:
            print(f" Error checking budget: {e}")
    
    def list_categories(self) -> List[sqlite3.Row]:
        """
        Retrieve all categories along with total spent in each.
        :return: List of category rows.
        """
        try:
            # Use LEFT JOIN to include categories with no expenses
            self.cursor.execute('''
                SELECT c.id, c.name, c.budget_limit,
                       COALESCE(SUM(e.amount), 0) as total_spent
                FROM categories c
                LEFT JOIN expenses e ON c.id = e.category_id
                GROUP BY c.id
                ORDER BY c.id
            ''')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f" Error listing categories: {e}")
            return []
    
    def export_to_file(self, filename: str = "expense_report.txt"):
        """
        Export a formatted expense report to a text file.
        Includes total spending, category summary, and recent expenses.
        :param filename: Name of the output file.
        :return: True if successful, False otherwise.
        """
        try:
            # Open the file in write mode (will create/overwrite)
            with open(filename, 'w') as f:
                f.write("=" * 50 + "\n")
                f.write("EXPENSE TRACKER REPORT\n")
                f.write(f"Generated: {datetime.datetime.now()}\n")
                f.write("=" * 50 + "\n\n")
                
                # Total Spending
                total = self.get_total_spending()
                f.write(f"TOTAL SPENDING: ${total:.2f}\n\n")
                
                # Spending Summary by Category
                f.write("SPENDING SUMMARY BY CATEGORY:\n")
                f.write("-" * 50 + "\n")
                summary = self.get_spending_summary()
                for row in summary:
                    # Safely access each column with fallback to default if missing
                    # This handles potential variations in row structure
                    category = row['category'] if 'category' in row.keys() else 'Unknown'
                    transaction_count = row['transaction_count'] if 'transaction_count' in row.keys() else 0
                    total_spent = row['total_spent'] if 'total_spent' in row.keys() else 0
                    budget_limit = row['budget_limit'] if 'budget_limit' in row.keys() else 0
                    remaining_budget = row['remaining_budget'] if 'remaining_budget' in row.keys() else budget_limit
                    percent_used = row['percent_used'] if 'percent_used' in row.keys() else 0
                    
                    f.write(f"{category}:\n")
                    f.write(f"  Transactions: {transaction_count}\n")
                    f.write(f"  Total Spent: ${total_spent or 0:.2f}\n")
                    if budget_limit > 0:
                        f.write(f"  Budget Limit: ${budget_limit:.2f}\n")
                        f.write(f"  Remaining: ${remaining_budget or budget_limit:.2f}\n")
                        f.write(f"  Percent Used: {percent_used or 0}%\n")
                    f.write("\n")
                
                # Recent Expenses (last 20)
                f.write("\nRECENT EXPENSES (last 20):\n")
                f.write("-" * 50 + "\n")
                expenses = self.view_all_expenses(20)
                for exp in expenses:
                    # Safely access expense fields
                    exp_id = exp['id'] if 'id' in exp.keys() else 'N/A'
                    exp_date = exp['date'] if 'date' in exp.keys() else 'N/A'
                    exp_category = exp['category'] if 'category' in exp.keys() else 'Unknown'
                    exp_amount = exp['amount'] if 'amount' in exp.keys() else 0
                    exp_description = exp['description'] if 'description' in exp.keys() else ''
                    
                    f.write(f"[{exp_id}] {exp_date} - {exp_category}\n")
                    f.write(f"  Amount: ${exp_amount:.2f}\n")
                    if exp_description:
                        f.write(f"  Description: {exp_description}\n")
                    f.write("\n")
            
            print(f" Report exported to '{filename}'")
            return True
            
        except Exception as e:
            print(f" Error exporting to file: {e}")
            return False


# ============================================
# Menu Display Function
# ============================================
def display_menu():
    """Display the main menu options for the user."""
    print("\n" + "=" * 50)
    print("EXPENSE TRACKER - SQL RELATIONAL DATABASE SYSTEM")
    print("=" * 50)
    print("1. Add New Expense")
    print("2. View All Expenses")
    print("3. Update Expense")
    print("4. Delete Expense")
    print("5. Search by Category")
    print("6. Filter by Date Range")
    print("7. Search by Description")
    print("8. View Spending Summary")
    print("9. View Monthly Report")
    print("10. List Categories")
    print("11. Export to File")
    print("12. View Total Spending")
    print("0. Exit")
    print("=" * 50)


# ============================================
# Helper Functions for Displaying Data Safely
# ============================================
def safe_get(row, key, default=None):
    """
    Safely get a value from a sqlite3.Row or tuple.
    Tries dictionary-style access first; if that fails, returns default.
    This is a fallback in case the row is not a Row object.
    """
    try:
        # Check if it's a Row and has the key
        if hasattr(row, '__getitem__') and isinstance(row, sqlite3.Row):
            if key in row.keys():
                return row[key]
    except:
        pass
    
    # If anything fails, return default
    return default


def display_expenses(expenses, title="EXPENSES"):
    """
    Display a list of expenses in a formatted table.
    Handles both sqlite3.Row objects and plain tuples.
    :param expenses: List of expense records.
    :param title: Title to print above the table.
    """
    if not expenses:
        print(f"No {title.lower()} found.")
        return
    
    print(f"\n{title}:")
    print("-" * 80)
    print(f"{'ID':<4} {'Date':<12} {'Category':<15} {'Amount':<10} {'Description'}")
    print("-" * 80)
    
    total = 0
    for exp in expenses:
        # Try to extract values assuming it's a dictionary-like row
        try:
            exp_id = exp['id']
            exp_date = exp['date']
            exp_category = exp['category']
            exp_amount = exp['amount']
            exp_description = exp['description'] if exp['description'] is not None else ''
        except (KeyError, TypeError):
            # If dictionary access fails, fall back to tuple indexing
            if isinstance(exp, (tuple, list)):
                # Assume the order: id, amount, category, description, date (or similar)
                # This is brittle but used as last resort
                exp_id = exp[0] if len(exp) > 0 else 'N/A'
                exp_date = exp[4] if len(exp) > 4 else 'N/A'  # date is typically 5th element
                exp_category = exp[2] if len(exp) > 2 else 'Unknown'  # category name is 3rd
                exp_amount = exp[1] if len(exp) > 1 else 0  # amount is 2nd
                exp_description = exp[3] if len(exp) > 3 and exp[3] is not None else ''
            else:
                # If all else fails, assign default values
                exp_id = 'N/A'
                exp_date = 'N/A'
                exp_category = 'Unknown'
                exp_amount = 0
                exp_description = ''
        
        print(f"{exp_id:<4} {exp_date:<12} {exp_category:<15} "
              f"${exp_amount:<9.2f} {exp_description}")
        total += exp_amount
    
    print("-" * 80)
    print(f"TOTAL: ${total:.2f} ({len(expenses)} transactions)")
    print()


# ============================================
# Main Program Entry Point
# ============================================
def main():
    """Main application loop: initializes database and handles user interaction."""
    print("Initializing Expense Tracker System...")
    
    # Check if the database file already exists
    if not os.path.exists('expenses.db'):
        print("Database not found. Creating database with default categories...")
        try:
            # Create a temporary connection to set up tables
            conn = sqlite3.connect('expenses.db')
            cursor = conn.cursor()
            
            # Create categories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    budget_limit DECIMAL(10, 2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create expenses table with foreign key referencing categories
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount DECIMAL(10, 2) NOT NULL,
                    category_id INTEGER NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            ''')
            
            # Insert some default categories with sample budget limits
            default_categories = [
                ('Food', 500.00),
                ('Transportation', 200.00),
                ('Entertainment', 100.00),
                ('Utilities', 300.00),
                ('Shopping', 150.00),
                ('Healthcare', 100.00),
                ('Education', 200.00),
                ('Miscellaneous', 50.00)
            ]
            
            # Use executemany to insert all rows, IGNORE duplicates if any
            cursor.executemany(
                'INSERT OR IGNORE INTO categories (name, budget_limit) VALUES (?, ?)',
                default_categories
            )
            
            conn.commit()
            conn.close()
            print(" Database created successfully with default categories!")
        except Exception as e:
            print(f"Error creating database: {e}")
            return  # Exit if database creation fails
    
    # Initialize the ExpenseTracker object (this will connect to the database)
    tracker = ExpenseTracker()
    
    # Main menu loop
    while True:
        display_menu()
        
        try:
            choice = input("\nEnter your choice (0-12): ").strip()
            
            # Exit
            if choice == "0":
                print("Thank you for using Expense Tracker!")
                break
            
            # Option 1: Add New Expense
            elif choice == "1":
                print("\n ADD NEW EXPENSE")
                print("Available Categories:")
                categories = tracker.list_categories()
                # Display each category with its ID, name, and budget
                for cat in categories:
                    # Safely access category data
                    try:
                        cat_id = cat['id']
                        name = cat['name']
                        budget = cat['budget_limit']
                    except (KeyError, TypeError):
                        # Fallback to tuple indexing if needed
                        if isinstance(cat, (tuple, list)):
                            cat_id = cat[0] if len(cat) > 0 else 0
                            name = cat[1] if len(cat) > 1 else "Unknown"
                            budget = cat[2] if len(cat) > 2 else 0.0
                        else:
                            cat_id = 0
                            name = "Unknown"
                            budget = 0.0
                    print(f"  {cat_id}. {name} (Budget: ${budget:.2f})")
                
                # Get user input
                try:
                    amount = float(input("Enter amount: $"))
                    category_id = int(input("Enter category ID: "))
                    description = input("Enter description (optional): ")
                    date = input("Enter date (YYYY-MM-DD, leave blank for today): ")
                    
                    if not date.strip():
                        date = None
                    
                    tracker.add_expense(amount, category_id, description, date)
                    
                except ValueError:
                    print(" Invalid input. Please enter valid numbers.")
            
            # Option 2: View All Expenses
            elif choice == "2":
                expenses = tracker.view_all_expenses()
                display_expenses(expenses, "ALL EXPENSES")
            
            # Option 3: Update Expense
            elif choice == "3":
                print("\n UPDATE EXPENSE")
                try:
                    expense_id = int(input("Enter expense ID to update: "))
                except ValueError:
                    print(" Please enter a valid expense ID (number)")
                    continue
                
                # Retrieve current details to show the user
                tracker.cursor.execute('''
                    SELECT e.*, c.name as category_name 
                    FROM expenses e 
                    JOIN categories c ON e.category_id = c.id 
                    WHERE e.id = ?
                ''', (expense_id,))
                expense = tracker.cursor.fetchone()
                
                if not expense:
                    print(f" No expense found with ID {expense_id}")
                    continue
                
                print(f"\nCurrent details:")
                try:
                    print(f"  Amount: ${expense['amount']:.2f}")
                    print(f"  Category: {expense['category_name']} (ID: {expense['category_id']})")
                    print(f"  Description: {expense['description']}")
                    print(f"  Date: {expense['date']}")
                except KeyError:
                    print(" Error reading expense details")
                    continue
                
                # Ask for new values; leave blank to keep current
                print("\nEnter new values (leave blank to keep current):")
                try:
                    amount_str = input("New amount: $")
                    amount = float(amount_str) if amount_str.strip() else None
                    
                    category_str = input("New category ID: ")
                    category_id = int(category_str) if category_str.strip() else None
                    
                    description = input("New description: ").strip()
                    if description == "":
                        description = None
                    
                    date = input("New date (YYYY-MM-DD): ").strip()
                    if date == "":
                        date = None
                    
                    tracker.update_expense(expense_id, amount, category_id, description, date)
                    
                except ValueError:
                    print(" Invalid input format.")
            
            # Option 4: Delete Expense
            elif choice == "4":
                print("\n DELETE EXPENSE")
                try:
                    expense_id = int(input("Enter expense ID to delete: "))
                except ValueError:
                    print(" Please enter a valid expense ID (number)")
                    continue
                
                # Confirm deletion with user
                confirm = input(f"Are you sure you want to delete expense {expense_id}? (yes/no): ")
                if confirm.lower() == 'yes':
                    tracker.delete_expense(expense_id)
                else:
                    print("Deletion cancelled.")
            
            # Option 5: Search by Category
            elif choice == "5":
                print("\n SEARCH BY CATEGORY")
                categories = tracker.list_categories()
                # Display categories for reference
                for cat in categories:
                    try:
                        cat_id = cat['id']
                        name = cat['name']
                    except (KeyError, TypeError):
                        if isinstance(cat, (tuple, list)):
                            cat_id = cat[0] if len(cat) > 0 else 0
                            name = cat[1] if len(cat) > 1 else "Unknown"
                        else:
                            cat_id = 0
                            name = "Unknown"
                    print(f"  {cat_id}. {name}")
                
                # Ask user whether to search by ID or name
                search_by = input("Search by (1) ID or (2) Name? Enter 1 or 2: ")
                
                if search_by == "1":
                    try:
                        category_id = int(input("Enter category ID: "))
                        expenses = tracker.search_by_category(category_id=category_id)
                    except ValueError:
                        print(" Please enter a valid category ID (number)")
                        continue
                elif search_by == "2":
                    category_name = input("Enter category name: ")
                    expenses = tracker.search_by_category(category_name=category_name)
                else:
                    print(" Invalid choice")
                    continue
                
                display_expenses(expenses, f"EXPENSES IN CATEGORY")
            
            # Option 6: Filter by Date Range
            elif choice == "6":
                print("\n FILTER BY DATE RANGE")
                start_date = input("Enter start date (YYYY-MM-DD): ")
                end_date = input("Enter end date (YYYY-MM-DD): ")
                
                expenses = tracker.filter_by_date_range(start_date, end_date)
                display_expenses(expenses, f"EXPENSES FROM {start_date} TO {end_date}")
            
            # Option 7: Search by Description
            elif choice == "7":
                print("\n SEARCH BY DESCRIPTION")
                keyword = input("Enter search keyword: ")
                
                expenses = tracker.search_by_description(keyword)
                display_expenses(expenses, f"EXPENSES CONTAINING '{keyword}'")
            
            # Option 8: Spending Summary
            elif choice == "8":
                print("\n SPENDING SUMMARY BY CATEGORY")
                summary = tracker.get_spending_summary()
                
                if not summary:
                    print("No spending data available.")
                    continue
                
                print("-" * 80)
                print(f"{'Category':<15} {'Transactions':<12} {'Total Spent':<12} "
                      f"{'Budget':<10} {'Remaining':<10} {'% Used':<8}")
                print("-" * 80)
                
                for row in summary:
                    # Safely extract summary values
                    try:
                        category = row['category'][:14] if row['category'] else 'Unknown'
                        transactions = row['transaction_count'] or 0
                        total = row['total_spent'] or 0
                        budget = row['budget_limit'] or 0
                        remaining = row['remaining_budget'] or budget
                        percent_used = row['percent_used'] or 0
                    except (KeyError, TypeError):
                        # Fallback to tuple indexing if row is a tuple
                        if isinstance(row, (tuple, list)):
                            category = (row[0][:14] if row[0] else 'Unknown') if len(row) > 0 else 'Unknown'
                            transactions = row[1] if len(row) > 1 else 0
                            total = row[2] if len(row) > 2 else 0
                            budget = row[3] if len(row) > 3 else 0
                            remaining = row[4] if len(row) > 4 else budget
                            percent_used = row[5] if len(row) > 5 else 0
                        else:
                            category = 'Unknown'
                            transactions = 0
                            total = 0
                            budget = 0
                            remaining = 0
                            percent_used = 0
                    
                    print(f"{category:<15} {transactions:<12} ${total:<11.2f} "
                          f"${budget:<9.2f} ${remaining:<9.2f} {percent_used:<7}%")
                
                total_spent = tracker.get_total_spending()
                print("-" * 80)
                print(f"GRAND TOTAL: ${total_spent:.2f}")
            
            # Option 9: Monthly Report
            elif choice == "9":
                print("\n MONTHLY SPENDING REPORT")
                year = input("Enter year (YYYY, leave blank for current year): ")
                month = input("Enter month (1-12, leave blank for current month): ")
                
                try:
                    year = int(year) if year.strip() else None
                    month = int(month) if month.strip() else None
                    
                    monthly_data = tracker.get_monthly_spending(year, month)
                    
                    if not monthly_data:
                        print("No expenses found for this period.")
                        continue
                    
                    current_year = year or datetime.date.today().year
                    current_month = month or datetime.date.today().month
                    month_name = datetime.date(1900, current_month, 1).strftime('%B')
                    
                    print(f"\nMonthly Report: {month_name} {current_year}")
                    print("-" * 50)
                    
                    total_monthly = 0
                    for row in monthly_data:
                        # Safely extract monthly data
                        try:
                            category = row['category']
                            monthly_total = row['monthly_total']
                            transaction_count = row['transaction_count']
                        except (KeyError, TypeError):
                            if isinstance(row, (tuple, list)):
                                category = row[0] if len(row) > 0 else "Unknown"
                                monthly_total = row[1] if len(row) > 1 else 0
                                transaction_count = row[2] if len(row) > 2 else 0
                            else:
                                category = "Unknown"
                                monthly_total = 0
                                transaction_count = 0
                        
                        print(f"{category}:")
                        print(f"  Total: ${monthly_total:.2f}")
                        print(f"  Transactions: {transaction_count}")
                        total_monthly += monthly_total
                    
                    print("-" * 50)
                    print(f"MONTHLY TOTAL: ${total_monthly:.2f}")
                    
                except ValueError:
                    print(" Invalid date input.")
            
            # Option 10: List Categories
            elif choice == "10":
                print("\n AVAILABLE CATEGORIES")
                categories = tracker.list_categories()
                
                if not categories:
                    print("No categories found.")
                    continue
                
                print("-" * 60)
                print(f"{'ID':<4} {'Category':<15} {'Budget':<12} {'Spent':<12} {'Remaining':<12}")
                print("-" * 60)
                
                for cat in categories:
                    # Safely extract category data
                    try:
                        cat_id = cat['id']
                        name = cat['name']
                        budget = cat['budget_limit']
                        spent = cat['total_spent'] or 0
                    except (KeyError, TypeError):
                        if isinstance(cat, (tuple, list)):
                            cat_id = cat[0] if len(cat) > 0 else 0
                            name = cat[1] if len(cat) > 1 else "Unknown"
                            budget = cat[2] if len(cat) > 2 else 0.0
                            spent = cat[3] if len(cat) > 3 else 0.0
                        else:
                            cat_id = 0
                            name = "Unknown"
                            budget = 0.0
                            spent = 0.0
                    
                    remaining = budget - spent
                    
                    print(f"{cat_id:<4} {name:<15} ${budget:<11.2f} "
                          f"${spent:<11.2f} ${remaining:<11.2f}")
            
            # Option 11: Export to File
            elif choice == "11":
                filename = input("Enter filename (default: expense_report.txt): ").strip()
                if not filename:
                    filename = "expense_report.txt"
                
                tracker.export_to_file(filename)
            
            # Option 12: View Total Spending
            elif choice == "12":
                total = tracker.get_total_spending()
                print(f"\n TOTAL SPENDING: ${total:.2f}")
            
            else:
                print(" Invalid choice. Please enter a number between 0 and 12.")
        
        # Handle various exceptions that may occur during user interaction
        except ValueError as e:
            print(f" Invalid input: {e}")
        except sqlite3.Error as e:
            print(f" Database error: {e}")
        except KeyboardInterrupt:
            print("\n\n Program interrupted. Goodbye!")
            break
        except Exception as e:
            print(f" Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    # Cleanup: close the database connection before exiting
    tracker.close_db()


# ============================================
# Script Entry Point
# ============================================
if __name__ == "__main__":
    main()