import requests
import json
from datetime import datetime
import logging
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='parking_client.log'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ParkingAPI:
    def __init__(self):
        """Initialize API client"""
        self.base_url = "http://192.168.2.6:5051"
        
    def test_connection(self):
        """Test connection to API server"""
        try:
            response = requests.get(f"{self.base_url}/api/test")
            logger.info(f"Test connection response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return True, data
                else:
                    return False, {'error': data.get('message', 'Unknown error')}
            else:
                return False, {'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.ConnectionError:
            return False, {'error': 'Failed to connect to server'}
        except Exception as e:
            return False, {'error': str(e)}
            
    def add_vehicle(self, plate_number, vehicle_type="Motor"):
        """Add a vehicle to the parking system
        
        Args:
            plate_number (str): Vehicle plate number
            vehicle_type (str): Either "Motor" or "Mobil", defaults to "Motor"
        """
        try:
            # Prepare request data with all necessary fields
            data = {
                "plat": plate_number,
                "jenis": vehicle_type
            }
            
            logger.info(f"Sending request to {self.base_url}/api/masuk with data: {json.dumps(data)}")
            
            # Send request with correct headers
            response = requests.post(
                f"{self.base_url}/api/masuk",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Raw response: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        # Extract ticket data from response.data
                        ticket_data = result.get('data', {})
                        return True, {
                            'plat': ticket_data.get('plat'),
                            'jenis': ticket_data.get('jenis'),
                            'tiket': ticket_data.get('TicketNumber'),  # Server returns 'TicketNumber'
                            'waktu_masuk': ticket_data.get('waktu')
                        }
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        logger.error(f"API returned error: {error_msg}")
                        # Fallback to offline mode
                        return self._handle_offline_entry(plate_number, vehicle_type)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response")
                    # Fallback to offline mode
                    return self._handle_offline_entry(plate_number, vehicle_type)
            else:
                logger.error(f"API request failed with status {response.status_code}")
                # Fallback to offline mode
                return self._handle_offline_entry(plate_number, vehicle_type)
                
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to server"
            logger.error(error_msg)
            # Fallback to offline mode
            return self._handle_offline_entry(plate_number, vehicle_type)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            # Fallback to offline mode
            return self._handle_offline_entry(plate_number, vehicle_type)
            
    def _handle_offline_entry(self, plate_number, vehicle_type):
        """Handle vehicle entry in offline mode"""
        try:
            # Generate offline ticket number
            counter_file = "counter.txt"
            counter = 1
            
            if os.path.exists(counter_file):
                with open(counter_file, "r") as f:
                    counter = int(f.read().strip())
            
            # Format: OFF0001, OFF0002, etc.
            ticket_number = f"OFF{counter:04d}"
            
            # Increment counter and save
            counter = (counter % 9999) + 1  # Reset at 9999
            with open(counter_file, "w") as f:
                f.write(str(counter))
            
            # Return offline ticket data
            return True, {
                'plat': plate_number,
                'jenis': vehicle_type,
                'tiket': ticket_number,
                'waktu_masuk': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"Error in offline mode: {e}")
            return False, {'error': str(e)}
    
    def get_vehicles(self):
        """Get list of parked vehicles"""
        try:
            response = requests.get(f"{self.base_url}/api/kendaraan")
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Retrieved {result.get('jumlah', 0)} vehicles")
                    return True, result
                else:
                    logger.error(f"Failed to get vehicles: {result.get('message', 'Unknown error')}")
                    return False, {"error": result.get('message', 'Unknown error')}
            else:
                logger.error(f"Failed to get vehicles with status {response.status_code}")
                return False, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Error getting vehicles: {str(e)}")
            return False, {"error": str(e)}
    
    def vehicle_exit(self, ticket_number):
        """Process vehicle exit
        
        Args:
            ticket_number (str): Ticket number in format PK-YYYYMMDDHHMMSS
        """
        try:
            data = {
                "tiket": ticket_number
            }
            
            logger.info(f"Processing vehicle exit: {ticket_number}")
            
            response = requests.post(
                f"{self.base_url}/api/keluar",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Vehicle exit successful: {result}")
                    return True, result['data']
                else:
                    logger.error(f"Vehicle exit failed: {result.get('message', 'Unknown error')}")
                    return False, {"error": result.get('message', 'Unknown error')}
            else:
                logger.error(f"Vehicle exit failed with status {response.status_code}")
                return False, {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error processing vehicle exit: {str(e)}")
            return False, {"error": str(e)}

# Example usage
if __name__ == "__main__":
    api = ParkingAPI()
    
    # Test connection
    print("=== Testing API Connection ===")
    success, result = api.test_connection()
    print(f"Connection {'successful' if success else 'failed'}")
    print(json.dumps(result, indent=2))
    
    if success:
        # Test vehicle entry
        print("\n=== Testing Vehicle Entry ===")
        ticket = f"PK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        success, result = api.add_vehicle(ticket, "Motor")
        print(json.dumps(result, indent=2))
        
        # Get vehicle list
        print("\n=== Getting Vehicle List ===")
        success, result = api.get_vehicles()
        print(json.dumps(result, indent=2))
        
        if success and result.get('data'):
            # Test vehicle exit with the first vehicle's ticket
            first_vehicle = result['data'][0]
            ticket = first_vehicle.get('TicketNumber')
            if ticket:
                print("\n=== Testing Vehicle Exit ===")
                success, result = api.vehicle_exit(ticket)
                print(json.dumps(result, indent=2)) 