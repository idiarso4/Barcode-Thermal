import requests
import json
from datetime import datetime

def test_api():
    base_url = 'http://192.168.2.6:5051'
    
    print("Testing API connection...")
    print(f"URL: {base_url}")
    
    try:
        # Test connection
        print("\n1. Testing /api/test endpoint")
        response = requests.get(f"{base_url}/api/test")
        print(f"Status: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
            
        # Test vehicle entry
        print("\n2. Testing /api/masuk endpoint")
        data = {
            "plat": f"RSI{datetime.now().strftime('%H%M%S')}",
            "jenis": "Motor"
        }
        print("Sending data:", json.dumps(data, indent=2))
        
        response = requests.post(
            f"{base_url}/api/masuk",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Status: {response.status_code}")
        print("Raw response:", response.text)
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Server tidak dapat dijangkau")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_api() 