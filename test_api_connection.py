import requests
import json
from datetime import datetime

def test_api_connection():
    """Test connection to the parking API server"""
    base_url = "http://192.168.2.6:5051"
    
    print("=== Testing Parking API Connection ===")
    
    # 1. Test basic connection
    try:
        print("\n1. Testing connection to /api/test")
        response = requests.get(f"{base_url}/api/test")
        print(f"Status code: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print(f"Total kendaraan: {data.get('total_kendaraan', 'N/A')}")
            connection_ok = True
        else:
            print(f"Failed to connect: {response.text}")
            connection_ok = False
            
        # Only continue if first test was successful
        if connection_ok:
            # 2. Test vehicle entry
            print("\n2. Testing vehicle entry at /api/masuk")
            # Generate a unique plate number for testing
            test_plate = f"TEST{datetime.now().strftime('%H%M%S')}"
            
            entry_data = {
                "plat": test_plate,
                "vehicleType": "Motor",
                "vehicleTypeId": 2,
                "isParked": True
            }
            
            print(f"Sending data: {json.dumps(entry_data, indent=2)}")
            
            response = requests.post(
                f"{base_url}/api/masuk", 
                json=entry_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status code: {response.status_code}")
            if response.ok:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get('success'):
                    ticket_number = data['data']['ticket']
                    vehicle_id = data['data']['id']
                    print(f"\nSuccessfully created vehicle entry:")
                    print(f"- Ticket: {ticket_number}")
                    print(f"- Vehicle ID: {vehicle_id}")
                    print(f"- Timestamp: {data['data']['waktu']}")
                    
                    # 3. Test vehicle exit
                    print("\n3. Testing vehicle exit at /api/keluar")
                    exit_data = {
                        "tiket": ticket_number
                    }
                    
                    print(f"Sending data: {json.dumps(exit_data, indent=2)}")
                    
                    response = requests.post(
                        f"{base_url}/api/keluar", 
                        json=exit_data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    print(f"Status code: {response.status_code}")
                    if response.ok:
                        data = response.json()
                        print(f"Response: {json.dumps(data, indent=2)}")
                        
                        if data.get('success'):
                            print(f"\nSuccessfully processed vehicle exit:")
                            print(f"- Plate: {data['data']['plat']}")
                            print(f"- Entry time: {data['data']['waktu_masuk']}")
                            print(f"- Exit time: {data['data']['waktu_keluar']}")
                    else:
                        print(f"Vehicle exit failed: {response.text}")
                        
                    # 4. Get vehicle list
                    print("\n4. Getting recent vehicles at /api/kendaraan")
                    response = requests.get(f"{base_url}/api/kendaraan")
                    
                    print(f"Status code: {response.status_code}")
                    if response.ok:
                        data = response.json()
                        print(f"Found {data.get('jumlah', 0)} recent vehicles")
                        # Print shortened version to avoid too much output
                        if data.get('data'):
                            for i, vehicle in enumerate(data['data'][:3]):  # Show only first 3
                                print(f"\nVehicle {i+1}:")
                                print(f"- ID: {vehicle.get('Id')}")
                                print(f"- Plate: {vehicle.get('VehicleNumber')}")
                                print(f"- Ticket: {vehicle.get('TicketNumber')}")
                                print(f"- Entry Time: {vehicle.get('EntryTime')}")
                    else:
                        print(f"Failed to get vehicle list: {response.text}")
            else:
                print(f"Vehicle entry failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Cannot reach the server")
        print(f"Make sure the server is running at {base_url}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_api_connection() 