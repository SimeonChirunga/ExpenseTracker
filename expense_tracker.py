import sqlite3
import datetime
import os
from typing import Optional, List, Tuple

class ExpenseTracker:
    def __init__(self, db_path: str = 'expenses.db'):
        """Initialize the Expense Tracker with database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect_db()
        
    def connect_db(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Set row factory FIRST for dictionary-like access
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            # Enable foreign key constraints
            self.cursor.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    # ========== CORE CRUD OPERATIONS ==========
    
    def add_expense(self, amount: float, category_id: int, 
                   description: str = "", date: str = None) -> bool:
        """
        Insert a new expense record into the database.
        Demonstrates SQL INSERT operation with parameterized query.
        """
        if amount <= 0:
            print("❌ Amount must be greater than 0")
            return False
        
        if not date:
            date = datetime.date.today().isoformat()
        
        try:
            # Validate category exists
            self.cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
            if not self.cursor.fetchone():
                print(f"❌ Category ID {category_id} does not exist")
                return False
            
            # Parameterized query to prevent SQL injection
            self.cursor.execute('''
                INSERT INTO expenses (amount, category_id, description, date)
                VALUES (?, ?, ?, ?)
            ''', (amount, category_id, description, date))
            
            self.conn.commit()
            print(f"✅ Expense of ${amount:.2f} added successfully!")
            
            # Check budget limit
            self.check_budget_limit(category_id)
            
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error adding expense: {e}")
            self.conn.rollback()
            return False
    
    def view_all_expenses(self, limit: int = 50) -> List[sqlite3.Row]:
        """
        Retrieve all expenses with category names.
        Demonstrates SQL SELECT with JOIN.
        """
        try:
            # JOIN to get category names
            self.cursor.execute('''
                SELECT e.id, e.amount, c.name as category, 
                       e.description, e.date, e.created_at
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                ORDER BY e.date DESC, e.created_at DESC
                LIMIT ?
            ''', (limit,))
            
            expenses = self.cursor.fetchall()
            return expenses
            
        except sqlite3.Error as e:
            print(f"❌ Error retrieving expenses: {e}")
            return []
    
    def update_expense(self, expense_id: int, amount: float = None,
                      category_id: int = None, description: str = None,
                      date: str = None) -> bool:
        """
        Modify an existing expense record.
        Demonstrates SQL UPDATE operation.
        """
        try:
            # Build dynamic UPDATE query based on provided parameters
            updates = []
            params = []
            
            if amount is not None:
                if amount <= 0:
                    print("❌ Amount must be greater than 0")
                    return False
                updates.append("amount = ?")
                params.append(amount)
            
            if category_id is not None:
                # Validate category exists
                self.cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
                if not self.cursor.fetchone():
                    print(f"❌ Category ID {category_id} does not exist")
                    return False
                updates.append("category_id = ?")
                params.append(category_id)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if date is not None:
                updates.append("date = ?")
                params.append(date)
            
            if not updates:
                print("❌ No fields to update")
                return False
            
            # Add expense_id to parameters
            params.append(expense_id)
            
            # Build and execute the UPDATE query
            query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            
            if self.cursor.rowcount == 0:
                print(f"❌ No expense found with ID {expense_id}")
                return False
            
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
        Demonstrates SQL DELETE operation.
        """
        try:
            self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            
            if self.cursor.rowcount == 0:
                print(f"❌ No expense found with ID {expense_id}")
                return False
            
            self.conn.commit()
            print(f"✅ Expense ID {expense_id} deleted successfully!")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error deleting expense: {e}")
            self.conn.rollback()
            return False
    
    # ========== QUERY OPERATIONS ==========
    
    def search_by_category(self, category_id: int = None, 
                          category_name: str = None) -> List[sqlite3.Row]:
        """
        Query expenses by category.
        Demonstrates filtering with WHERE clause.
        """
        try:
            if category_name:
                # Get category ID from name
                self.cursor.execute(
                    "SELECT id FROM categories WHERE name LIKE ?", 
                    (f"%{category_name}%",)
                )
                result = self.cursor.fetchone()
                if not result:
                    print(f"❌ No category found with name '{category_name}'")
                    return []
                category_id = result['id']
            
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
            print(f"❌ Error searching by category: {e}")
            return []
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> List[sqlite3.Row]:
        """
        Retrieve expenses within a date range.
        Demonstrates date filtering and BETWEEN operator.
        """
        try:
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
            print(f"❌ Error filtering by date: {e}")
            return []
    
    def search_by_description(self, keyword: str) -> List[sqlite3.Row]:
        """
        Search expenses by description keyword.
        Demonstrates text search with LIKE operator.
        """
        try:
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
            print(f"❌ Error searching by description: {e}")
            return []
    
    # ========== DATA ANALYSIS & REPORTING ==========
    
    def get_spending_summary(self) -> List[sqlite3.Row]:
        """
        Generate spending summary by category.
        Demonstrates GROUP BY and aggregate functions.
        """
        try:
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
            print(f"❌ Error generating spending summary: {e}")
            return []
    
    def get_monthly_spending(self, year: int = None, month: int = None) -> List[sqlite3.Row]:
        """
        Generate monthly spending report.
        Demonstrates date functions and grouping.
        """
        try:
            if year is None:
                year = datetime.date.today().year
            if month is None:
                month = datetime.date.today().month
            
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
            ''', (str(year), f"{month:02d}"))
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            print(f"❌ Error generating monthly report: {e}")
            return []
    
    def get_total_spending(self) -> float:
        """Calculate total spending across all categories."""
        try:
            self.cursor.execute('SELECT SUM(amount) as total FROM expenses')
            result = self.cursor.fetchone()
            # Access result safely
            if result and result['total'] is not None:
                return float(result['total'])
            return 0.0
        except sqlite3.Error as e:
            print(f"❌ Error calculating total spending: {e}")
            return 0.0
    
    # ========== HELPER FUNCTIONS ==========
    
    def check_budget_limit(self, category_id: int):
        """Check if spending exceeds budget limit for a category."""
        try:
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
            if result and result['budget_limit'] > 0:
                spent = result['spent'] or 0
                if spent > result['budget_limit']:
                    print(f"⚠️  Warning: You've exceeded the budget for {result['name']}!")
                    print(f"   Budget: ${result['budget_limit']:.2f}, Spent: ${spent:.2f}")
                elif spent > result['budget_limit'] * 0.9:
                    print(f"⚠️  Warning: You're close to exceeding the budget for {result['name']}")
                    
        except sqlite3.Error as e:
            print(f"❌ Error checking budget: {e}")
    
    def list_categories(self) -> List[sqlite3.Row]:
        """Display all available categories."""
        try:
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
            print(f"❌ Error listing categories: {e}")
            return []
    
    def export_to_file(self, filename: str = "expense_report.txt"):
        """
        Export expense data and summary to a text file.
        Demonstrates file I/O integration.
        """
        try:
            with open(filename, 'w') as f:
                f.write("=" * 50 + "\n")
                f.write("EXPENSE TRACKER REPORT\n")
                f.write(f"Generated: {datetime.datetime.now()}\n")
                f.write("=" * 50 + "\n\n")
                
                # Total Spending
                total = self.get_total_spending()
                f.write(f"TOTAL SPENDING: ${total:.2f}\n\n")
                
                # Spending Summary
                f.write("SPENDING SUMMARY BY CATEGORY:\n")
                f.write("-" * 50 + "\n")
                summary = self.get_spending_summary()
                for row in summary:
                    # Access row data safely
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
                
                # Recent Expenses
                f.write("\nRECENT EXPENSES (last 20):\n")
                f.write("-" * 50 + "\n")
                expenses = self.view_all_expenses(20)
                for exp in expenses:
                    # Access row data safely
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
            
            print(f"✅ Report exported to '{filename}'")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting to file: {e}")
            return False


def display_menu():
    """Display the main menu."""
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


def safe_get(row, key, default=None):
    """Safely get a value from a sqlite3.Row or tuple."""
    try:
        # Try dictionary-style access first
        if hasattr(row, '__getitem__') and isinstance(row, sqlite3.Row):
            if key in row.keys():
                return row[key]
    except:
        pass
    
    # Fall back to default
    return default


def display_expenses(expenses, title="EXPENSES"):
    """Display a list of expenses in formatted table."""
    if not expenses:
        print(f"No {title.lower()} found.")
        return
    
    print(f"\n{title}:")
    print("-" * 80)
    print(f"{'ID':<4} {'Date':<12} {'Category':<15} {'Amount':<10} {'Description'}")
    print("-" * 80)
    
    total = 0
    for exp in expenses:
        # Safely extract values
        try:
            exp_id = exp['id']
            exp_date = exp['date']
            exp_category = exp['category']
            exp_amount = exp['amount']
            exp_description = exp['description'] if exp['description'] is not None else ''
        except (KeyError, TypeError):
            # If dictionary access fails, try tuple access
            if isinstance(exp, (tuple, list)):
                exp_id = exp[0] if len(exp) > 0 else 'N/A'
                exp_date = exp[4] if len(exp) > 4 else 'N/A'  # date is typically 4th column
                exp_category = exp[2] if len(exp) > 2 else 'Unknown'  # category is 3rd column
                exp_amount = exp[1] if len(exp) > 1 else 0  # amount is 2nd column
                exp_description = exp[3] if len(exp) > 3 and exp[3] is not None else ''
            else:
                # Fallback
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


def main():
    """Main application loop."""
    print("🚀 Initializing Expense Tracker System...")
    
    # Check if database exists, run setup if not
    if not os.path.exists('expenses.db'):
        print("Database not found. Creating database with default categories...")
        try:
            # Create database and tables
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
            
            # Create expenses table
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
            
            # Insert default categories
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
            
            cursor.executemany(
                'INSERT OR IGNORE INTO categories (name, budget_limit) VALUES (?, ?)',
                default_categories
            )
            
            conn.commit()
            conn.close()
            print("✅ Database created successfully with default categories!")
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return
    
    # Initialize tracker
    tracker = ExpenseTracker()
    
    while True:
        display_menu()
        
        try:
            choice = input("\nEnter your choice (0-12): ").strip()
            
            if choice == "0":
                print("👋 Thank you for using Expense Tracker!")
                break
            
            elif choice == "1":
                # Add New Expense
                print("\n➕ ADD NEW EXPENSE")
                print("Available Categories:")
                categories = tracker.list_categories()
                # Safely display categories
                for cat in categories:
                    try:
                        cat_id = cat['id']
                        name = cat['name']
                        budget = cat['budget_limit']
                    except (KeyError, TypeError):
                        # Fallback to tuple access
                        if isinstance(cat, (tuple, list)):
                            cat_id = cat[0] if len(cat) > 0 else 0
                            name = cat[1] if len(cat) > 1 else "Unknown"
                            budget = cat[2] if len(cat) > 2 else 0.0
                        else:
                            cat_id = 0
                            name = "Unknown"
                            budget = 0.0
                    print(f"  {cat_id}. {name} (Budget: ${budget:.2f})")
                
                try:
                    amount = float(input("Enter amount: $"))
                    category_id = int(input("Enter category ID: "))
                    description = input("Enter description (optional): ")
                    date = input("Enter date (YYYY-MM-DD, leave blank for today): ")
                    
                    if not date.strip():
                        date = None
                    
                    tracker.add_expense(amount, category_id, description, date)
                    
                except ValueError:
                    print("❌ Invalid input. Please enter valid numbers.")
            
            elif choice == "2":
                # View All Expenses
                expenses = tracker.view_all_expenses()
                display_expenses(expenses, "ALL EXPENSES")
            
            elif choice == "3":
                # Update Expense
                print("\n✏️ UPDATE EXPENSE")
                try:
                    expense_id = int(input("Enter expense ID to update: "))
                except ValueError:
                    print("❌ Please enter a valid expense ID (number)")
                    continue
                
                # Show current expense details
                tracker.cursor.execute('''
                    SELECT e.*, c.name as category_name 
                    FROM expenses e 
                    JOIN categories c ON e.category_id = c.id 
                    WHERE e.id = ?
                ''', (expense_id,))
                expense = tracker.cursor.fetchone()
                
                if not expense:
                    print(f"❌ No expense found with ID {expense_id}")
                    continue
                
                print(f"\nCurrent details:")
                try:
                    print(f"  Amount: ${expense['amount']:.2f}")
                    print(f"  Category: {expense['category_name']} (ID: {expense['category_id']})")
                    print(f"  Description: {expense['description']}")
                    print(f"  Date: {expense['date']}")
                except KeyError:
                    print("❌ Error reading expense details")
                    continue
                
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
                    print("❌ Invalid input format.")
            
            elif choice == "4":
                # Delete Expense
                print("\n🗑️ DELETE EXPENSE")
                try:
                    expense_id = int(input("Enter expense ID to delete: "))
                except ValueError:
                    print("❌ Please enter a valid expense ID (number)")
                    continue
                
                # Confirm deletion
                confirm = input(f"Are you sure you want to delete expense {expense_id}? (yes/no): ")
                if confirm.lower() == 'yes':
                    tracker.delete_expense(expense_id)
                else:
                    print("Deletion cancelled.")
            
            elif choice == "5":
                # Search by Category
                print("\n🔍 SEARCH BY CATEGORY")
                categories = tracker.list_categories()
                # Safely display categories
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
                
                search_by = input("Search by (1) ID or (2) Name? Enter 1 or 2: ")
                
                if search_by == "1":
                    try:
                        category_id = int(input("Enter category ID: "))
                        expenses = tracker.search_by_category(category_id=category_id)
                    except ValueError:
                        print("❌ Please enter a valid category ID (number)")
                        continue
                elif search_by == "2":
                    category_name = input("Enter category name: ")
                    expenses = tracker.search_by_category(category_name=category_name)
                else:
                    print("❌ Invalid choice")
                    continue
                
                display_expenses(expenses, f"EXPENSES IN CATEGORY")
            
            elif choice == "6":
                # Filter by Date Range
                print("\n📅 FILTER BY DATE RANGE")
                start_date = input("Enter start date (YYYY-MM-DD): ")
                end_date = input("Enter end date (YYYY-MM-DD): ")
                
                expenses = tracker.filter_by_date_range(start_date, end_date)
                display_expenses(expenses, f"EXPENSES FROM {start_date} TO {end_date}")
            
            elif choice == "7":
                # Search by Description
                print("\n🔍 SEARCH BY DESCRIPTION")
                keyword = input("Enter search keyword: ")
                
                expenses = tracker.search_by_description(keyword)
                display_expenses(expenses, f"EXPENSES CONTAINING '{keyword}'")
            
            elif choice == "8":
                # Spending Summary
                print("\n📊 SPENDING SUMMARY BY CATEGORY")
                summary = tracker.get_spending_summary()
                
                if not summary:
                    print("No spending data available.")
                    continue
                
                print("-" * 80)
                print(f"{'Category':<15} {'Transactions':<12} {'Total Spent':<12} "
                      f"{'Budget':<10} {'Remaining':<10} {'% Used':<8}")
                print("-" * 80)
                
                for row in summary:
                    # Safely extract values
                    try:
                        category = row['category'][:14] if row['category'] else 'Unknown'
                        transactions = row['transaction_count'] or 0
                        total = row['total_spent'] or 0
                        budget = row['budget_limit'] or 0
                        remaining = row['remaining_budget'] or budget
                        percent_used = row['percent_used'] or 0
                    except (KeyError, TypeError):
                        # Fallback to tuple access
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
            
            elif choice == "9":
                # Monthly Report
                print("\n📈 MONTHLY SPENDING REPORT")
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
                        # Safely extract values
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
                    print("❌ Invalid date input.")
            
            elif choice == "10":
                # List Categories
                print("\n📋 AVAILABLE CATEGORIES")
                categories = tracker.list_categories()
                
                if not categories:
                    print("No categories found.")
                    continue
                
                print("-" * 60)
                print(f"{'ID':<4} {'Category':<15} {'Budget':<12} {'Spent':<12} {'Remaining':<12}")
                print("-" * 60)
                
                for cat in categories:
                    # Safely extract values
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
            
            elif choice == "11":
                # Export to File
                filename = input("Enter filename (default: expense_report.txt): ").strip()
                if not filename:
                    filename = "expense_report.txt"
                
                tracker.export_to_file(filename)
            
            elif choice == "12":
                # View Total Spending
                total = tracker.get_total_spending()
                print(f"\n💰 TOTAL SPENDING: ${total:.2f}")
            
            else:
                print("❌ Invalid choice. Please enter a number between 0 and 12.")
        
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
        except KeyboardInterrupt:
            print("\n\n👋 Program interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    # Cleanup
    tracker.close_db()

if __name__ == "__main__":
    main()