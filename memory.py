from datetime import datetime
from database import get_connection


def save_memory(user_id: str, key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO memory (user_id, key, value, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, key, value, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_user_memory(user_id: str, limit: int = 5):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT key, value, created_at
        FROM memory
        WHERE user_id = ?
        ORDER BY memory_id DESC
        LIMIT ?
    """, (user_id, limit))

    rows = cur.fetchall()
    conn.close()
    return rows