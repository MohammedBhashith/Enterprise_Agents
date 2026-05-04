from datetime import datetime
from database import get_connection


def save_log(user_id: str, query: str, agent: str, tool_used: str, response: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO logs (user_id, query, agent, tool_used, response, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        query,
        agent,
        tool_used,
        response,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_logs(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, query, agent, tool_used, response, created_at
        FROM logs
        ORDER BY log_id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows