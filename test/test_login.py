import requests
import json

def test_admin_login():
    url = "http://127.0.0.1:8000/token"
    # Using the credentials provided by the user
    payload = {
        "username": "admin",
        "password": "123456"
    }
    
    print(f"Attempting login with username: {payload['username']}")
    
    try:
        # The backend expects form data for OAuth2 password flow, but let's try both json and form data
        # Standard OAuth2 uses form data
        response = requests.post(url, data=payload)
        
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Login Successful!")
            token_data = response.json()
            print(f"Access Token: {token_data.get('access_token')[:20]}...")
            print(f"Token Type: {token_data.get('token_type')}")
            return True
        else:
            print("Login Failed!")
            print(f"Response Body: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the backend server. Is it running on http://127.0.0.1:8000?")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    test_admin_login()
