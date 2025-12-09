import requests
import json

def test_ai_stream():
    url = "http://localhost:8000/api/ai/qa/stream"
    payload = {
        "user_id": "test_user_001",
        "question": "如何申请缓考？",
        "history_flag": True
    }
    
    print(f"Asking: {payload['question']}")
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("Receiving stream...")
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            json_str = decoded_line[6:]
                            try:
                                data = json.loads(json_str)
                                print(data["content"], end="", flush=True)
                            except json.JSONDecodeError:
                                print(f"\n[Raw]: {decoded_line}")
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
        print("\n\nStream finished.")
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_ai_stream()
