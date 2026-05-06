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


def get_first_user_query(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT value, created_at
        FROM memory
        WHERE user_id = ?
        AND key = 'user_query'
        AND LOWER(value) NOT IN ('hi', 'hello', 'hey', 'thanks', 'thank you', 'bye')
        AND LOWER(value) NOT LIKE '%first query%'
        ORDER BY memory_id ASC
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return "I do not have any previous meaningful query stored for this user."

    return f"Your first meaningful saved query was: {row[0]}"