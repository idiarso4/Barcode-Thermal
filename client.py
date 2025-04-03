import requests
import json
import logging
from datetime import datetime
from config import API_CONFIG, LOG_CONFIG
from printer_utils import TicketPrinter
import os

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG['level']),
    format=LOG_CONFIG['format']
)

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_CONFIG['file']), exist_ok=True)

# Add file handler
file_handler = logging.FileHandler(LOG_CONFIG['file'])
file_handler.setFormatter(logging.Formatter(LOG_CONFIG['format']))
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)

class ParkingClient:
    def __init__(self):
        self.base_url = API_CONFIG['base_url']
        self.timeout = API_CONFIG['timeout']
        self.max_retries = API_CONFIG['max_retries']
        self.session = requests.Session()
        self.printer = TicketPrinter()
    
    def _make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}{endpoint}"
        retries = 0
        
        while retries < self.max_retries:
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=self.timeout)
                elif method == 'POST':
                    response = self.session.post(url, json=data, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.RequestException as e:
                retries += 1
                logger.error(f"Request failed (attempt {retries}/{self.max_retries}): {str(e)}")
                
                if retries == self.max_retries:
                    raise
    
    def test_connection(self):
        """Test connection to the server"""
        try:
            return self._make_request('GET', '/api/test-connection')
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def send_vehicle_data(self, plate_number, vehicle_type="Motor"):
        """Send vehicle data to server and print ticket"""
        data = {
            'plateNumber': plate_number,
            'vehicleType': vehicle_type,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            response = self._make_request('POST', '/api/tickets', data=data)
            
            if response.get('success'):
                # Prepare ticket data for printing
                ticket_data = {
                    'ticket_number': response['data']['ticketNumber'],
                    'plate_number': plate_number,
                    'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'vehicle_type': vehicle_type
                }
                
                # Print ticket
                if self.printer.print_ticket(ticket_data):
                    logger.info(f"Ticket printed successfully for plate {plate_number}")
                else:
                    logger.error(f"Failed to print ticket for plate {plate_number}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send vehicle data: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_vehicle_status(self, ticket_number):
        """Get vehicle status by ticket number"""
        try:
            return self._make_request('GET', f'/api/tickets/{ticket_number}')
        except Exception as e:
            logger.error(f"Failed to get vehicle status: {str(e)}")
            return {'success': False, 'message': str(e)}

def main():
    client = ParkingClient()
    
    # Test connection
    print("Testing connection to server...")
    result = client.test_connection()
    print(f"Connection test result: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        # Send test vehicle data
        plate = f"TEST-{datetime.now().strftime('%H%M%S')}"
        print(f"\nSending test vehicle data (plate: {plate})...")
        result = client.send_vehicle_data(plate)
        print(f"Send result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            # Get vehicle status
            ticket = result['data']['ticketNumber']
            print(f"\nGetting vehicle status for ticket {ticket}...")
            result = client.get_vehicle_status(ticket)
            print(f"Status result: {json.dumps(result, indent=2)}")

if __name__ == '__main__':
    main() 