import sqlite3
import pandas as pd

db_path = "d:\\bishe\\one\\backend\\test.db"

def check_data():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ["teachers", "courses", "students", "course_selections", "grades"]
    print("\n--- Data Verification ---")
    for table in tables:
        try:
            count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table}", conn).iloc[0]['count']
            print(f"Table '{table}': {count} records")
            
            if count > 0:
                print(f"Sample data from {table}:")
                df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 3", conn)
                print(df.to_string(index=False))
                print("-" * 30)
        except Exception as e:
            print(f"Error checking {table}: {e}")
            
    conn.close()

import os
if __name__ == "__main__":
    check_data()
