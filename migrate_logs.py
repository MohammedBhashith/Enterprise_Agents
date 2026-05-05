from database import get_connection


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        print(f"Added column: {column_name}")
    else:
        print(f"Column already exists: {column_name}")


def migrate_logs_table():
    conn = get_connection()
    cur = conn.cursor()

    add_column_if_missing(cur, "logs", "intent", "TEXT")
    add_column_if_missing(cur, "logs", "response_time", "REAL")

    conn.commit()
    conn.close()

    print("Logs migration completed successfully.")


if __name__ == "__main__":
    migrate_logs_table()