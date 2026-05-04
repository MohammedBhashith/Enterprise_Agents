import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/enterprise.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        manager_id TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        manager_id TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_balances (
        user_id TEXT PRIMARY KEY,
        casual_balance INTEGER DEFAULT 12,
        sick_balance INTEGER DEFAULT 10
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS it_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Open',
        assigned_engineer TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Manager Pending',
        manager_status TEXT DEFAULT 'Pending',
        it_status TEXT DEFAULT 'Pending',
        inventory_status TEXT DEFAULT 'Pending',
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_type TEXT NOT NULL,
        request_id INTEGER NOT NULL,
        approver_id TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        comments TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        query TEXT,
        agent TEXT,
        tool_used TEXT,
        response TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS known_outages (
        outage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_type TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_schedule (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        system_name TEXT NOT NULL,
        description TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'Scheduled'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        asset_type TEXT PRIMARY KEY,
        available_count INTEGER NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    users = [
        ("EMP001", "Bhashith", "Mohammed.Bhashith@novigosolutions.com", "Employee", "Engineering", "MGR001"),
        ("EMP002", "Aman", "aman@company.com", "Employee", "HR", "MGR001"),
        ("MGR001", "Hisham", "mohdbhashith313@gmail.com", "Manager", "Engineering", None),
        ("HR001", "Sara", "sara@company.com", "HR Team", "HR", None),
        ("IT001", "John", "john@company.com", "IT Team", "IT", None),
        ("ADMIN001", "Admin", "admin@company.com", "Admin", "Admin", None),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO users 
    (user_id, name, email, role, department, manager_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, users)

    inventory_items = [
        ("Laptop", 5),
        ("Monitor", 8),
        ("Keyboard", 10),
        ("Mouse", 15),
        ("VPN Token", 4),
        ("Software License", 6),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO inventory 
    (asset_type, available_count)
    VALUES (?, ?)
    """, inventory_items)

    cursor.execute("""
    INSERT OR IGNORE INTO known_outages
    (outage_id, issue_type, description, status, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        1,
        "VPN",
        "VPN service is currently facing intermittent login failures.",
        "Active",
        datetime.now().isoformat()
    ))

    cursor.execute("""
    INSERT OR IGNORE INTO maintenance_schedule
    (maintenance_id, system_name, description, start_time, end_time, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        1,
        "Outlook",
        "Outlook maintenance scheduled this weekend.",
        "2026-05-04 22:00",
        "2026-05-05 02:00",
        "Scheduled"
    ))

    leave_balances = [
        ("EMP001", 12, 10),
        ("EMP002", 12, 10),
        ("MGR001", 12, 10),
        ("HR001", 12, 10),
        ("IT001", 12, 10),
        ("ADMIN001", 12, 10),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO leave_balances
    (user_id, casual_balance, sick_balance)
    VALUES (?, ?, ?)
    """, leave_balances)

    conn.commit()
    conn.close()


def get_user(user_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "name": row[1],
        "email": row[2],
        "role": row[3],
        "department": row[4],
        "manager_id": row[5],
    }


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()

    conn.close()

    return rows


def setup_database():
    init_db()
    seed_data()
    print("Database created and seeded successfully.")



if __name__ == "__main__":
    setup_database()