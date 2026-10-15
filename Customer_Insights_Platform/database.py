import sqlite3
import os
import shutil
from datetime import datetime

DB_NAME = "customer_insights.db"

def get_db_connection():
    """Returns a sqlite3 connection object."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, DB_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes all SQLite database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        email TEXT,
        phone TEXT,
        occupation TEXT,
        registration_date TEXT,
        loyalty_status TEXT,
        clv REAL,
        churn_risk_score REAL,
        purchase_frequency REAL
    )
    """)
    
    # 3. Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Products (
        product_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL,
        category TEXT,
        rating REAL
    )
    """)
    
    # 4. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        order_date TEXT,
        total_amount REAL,
        payment_method TEXT,
        status TEXT,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )
    """)
    
    # 5. Transactions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Transactions (
        transaction_id TEXT PRIMARY KEY,
        order_id TEXT,
        transaction_date TEXT,
        amount REAL,
        status TEXT,
        FOREIGN KEY(order_id) REFERENCES Orders(order_id)
    )
    """)
    
    # 6. Recommendations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Recommendations (
        recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT,
        recommended_products TEXT, -- Store JSON or comma-separated values
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )
    """)
    
    # 7. Predictions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT,
        churn_risk_score REAL,
        clv REAL,
        predicted_purchases REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )
    """)
    
    # 8. Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_path TEXT
    )
    """)
    
    # 9. ActivityLogs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ActivityLogs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def log_activity(username, action):
    """Inserts a user activity event into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO ActivityLogs (username, action, timestamp) VALUES (?, ?, ?)",
            (username, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Logging error: {e}")
    finally:
        conn.close()

def is_db_seeded():
    """Checks if data already exists in the Customers table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Customers")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# --- User Management Helper Functions ---

def add_user(username, email, password_hash, role):
    """Creates a new user record in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role)
        )
        conn.commit()
        log_activity(username, "User registered successfully.")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    """Retrieves a user by username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_users():
    """Retrieves all users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, created_at FROM Users")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_user_role(username, new_role, changer):
    """Updates the role of a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()
        log_activity(changer, f"Updated role of {username} to {new_role}.")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def delete_user(username, changer):
    """Deletes a user from the system."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
        conn.commit()
        log_activity(changer, f"Deleted user account: {username}.")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def update_password(username, new_password_hash):
    """Updates a user's password hash."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Users SET password_hash = ? WHERE username = ?", (new_password_hash, username))
        conn.commit()
        log_activity(username, "Updated security credentials (password).")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_activity_logs(limit=100):
    """Retrieves list of latest activity logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ActivityLogs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def backup_database():
    """Creates a timestamped backup of the SQLite database in a 'backups' folder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, DB_NAME)
    
    if not os.path.exists(db_path):
        return None, "Source database file does not exist."
        
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"customer_insights_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        return backup_path, None
    except Exception as e:
        return None, str(e)
