import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    url = f"{BASE_URL}/api/health"
    print(f"Testing Health Check: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            print(f"✅ Health Check Passed: {data}")
            return True
    except urllib.error.URLError as e:
        print(f"❌ Health Check Failed: {e}")
        return False

def test_user_list_access_without_token():
    url = f"{BASE_URL}/api/user/list"
    print(f"\nTesting User List (No Token): {url}")
    try:
        urllib.request.urlopen(url)
        print("❌ Should have failed with 401, but succeeded!")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"✅ Correctly rejected with 401: {e}")
        else:
            print(f"⚠️ Unexpected error code: {e.code}")
    except urllib.error.URLError as e:
        print(f"❌ Connection failed: {e}")

def test_admin_login_and_list(username, password):
    login_url = f"{BASE_URL}/token"
    print(f"\nTesting Admin Login: {username}")
    
    data = urllib.parse.urlencode({
        "username": username,
        "password": password,
        "grant_type": "password" # OAuth2 standard
    }).encode('utf-8')
    
    req = urllib.request.Request(login_url, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    token = None
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.load(response)
            token = resp_data.get("access_token")
            print(f"✅ Login Successful! Token: {token[:10]}...")
    except urllib.error.HTTPError as e:
        print(f"❌ Login Failed: {e}")
        print(e.read().decode())
        return

    if token:
        list_url = f"{BASE_URL}/api/user/list"
        print(f"\nTesting User List (With Token): {list_url}")
        req = urllib.request.Request(list_url)
        req.add_header("Authorization", f"Bearer {token}")
        
        try:
            with urllib.request.urlopen(req) as response:
                users = json.load(response)
                print(f"✅ User List Retrieved! Count: {len(users)}")
                if len(users) > 0:
                    print("Sample User:", users[0])
        except urllib.error.HTTPError as e:
            print(f"❌ User List Failed: {e}")
            print(e.read().decode())

if __name__ == "__main__":
    print("--- Frontend-Backend Connection Test ---")
    if not test_health():
        print("\n⚠️ Backend seems down. Please start it first.")
        sys.exit(1)
    
    test_user_list_access_without_token()
    
    # Replace with valid credentials if known, or ask user to edit
    # Default admin/123456 often used in dev
    print("\nAttempting login with default admin credentials (admin/123456)...")
    test_admin_login_and_list("admin", "123456")
