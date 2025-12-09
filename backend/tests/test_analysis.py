import requests
import json

def test_analysis():
    url = "http://localhost:8000/api/analysis/student/warning"
    payload = {
        "grade": "2023",
        "major": "CS" # Optional
    }
    
    print("Sending analysis request...")
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print("Success!")
            print(f"Warning List Size: {len(data['warning_list'])}")
            print(f"Cluster Plot: {data['cluster_plot_url']}")
            print(f"Stat Plot: {data['warning_stat_plot_url']}")
            print(f"Report URL: {data['report_download_url']}")
            
            if len(data['warning_list']) > 0:
                print("Sample Student:", data['warning_list'][0])
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_analysis()
