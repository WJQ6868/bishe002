import requests
import sys

BASE_URL = "http://localhost:8000"

def test_login(username, password):
    print(f"Testing login for {username}...")
    try:
        response = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
        if response.status_code == 200:
            print(f"Login SUCCESS! Token: {response.json()['access_token'][:20]}...")
            return True
        else:
            print(f"Login FAILED! Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return False

if __name__ == "__main__":
    # Since the server might not be running, we can't test via HTTP yet unless we start it.
    # But we can check the database directly to see if users exist.
    import sqlite3
    import pandas as pd
    
    db_path = "d:\\bishe\\one\\backend\\test.db"
    print(f"Checking database at {db_path} for users...")
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT id, username, role, is_active FROM sys_users", conn)
        print(df.to_string(index=False))
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")
