import sqlite3
import pandas as pd

db_path = "d:\\bishe\\one\\backend\\test.db"

tables = ["sys_users", "teachers", "students", "courses", "classrooms", "schedules", "grades", "course_selections"]

print("=== Database Verification ===\n")
conn = sqlite3.connect(db_path)

for table in tables:
    try:
        count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table}", conn).iloc[0]['count']
        print(f"[OK] {table}: {count} records")
    except Exception as e:
        print(f"[ERR] {table}: Error - {e}")

print("\n=== Sample Users ===")
df = pd.read_sql_query("SELECT id, username, password, role FROM sys_users", conn)
print(df.to_string(index=False))

conn.close()
