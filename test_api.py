import requests
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def test_masuk():
    url = "http://192.168.2.6:5051/api/masuk"
    data = {
        "plat": "B1234XY",
        "jenis": "Motor",
        "isParked": "t",  # PostgreSQL boolean true
        "isLost": "f",    # PostgreSQL boolean false
        "isPaid": "f",
        "isValid": "t"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Sending POST request to {url}")
        logger.info(f"Request data: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, json=data, headers=headers)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        logger.info(f"Raw Response Text: {response.text}")
        
        if response.text:
            try:
                response_json = response.json()
                logger.info("Parsed Response:")
                logger.info(json.dumps(response_json, indent=2))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse response as JSON: {e}")
        else:
            logger.warning("Empty response body")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_api()
    test_masuk() 