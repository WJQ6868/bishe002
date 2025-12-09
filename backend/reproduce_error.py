import requests
import json

BASE_URL = "http://localhost:8000"

def reproduce():
    # 1. Login
    print("Logging in...")
    try:
        response = requests.post(f"{BASE_URL}/token", data={
            "username": "20230001",
            "password": "123456"
        })
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json()["access_token"]
        print(f"Got token: {token[:20]}...")
        
        # 2. Call Cert List
        print("Calling /api/cert/list...")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/cert/list", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reproduce()
