import os
import psycopg2
import json
import requests
import time
from datetime import datetime
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='parking_client.log'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.2.6'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'parkir2'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# API Configuration
API_URL = os.getenv('API_URL', "http://192.168.2.6:5050")
API_AUTH = (os.getenv('API_USERNAME', 'admin'), os.getenv('API_PASSWORD', 'admin'))

class ParkingClient:
    def __init__(self, use_api=True):
        """Initialize parking client with either API or direct DB connection"""
        self.use_api = use_api
        self.conn = None
        
        if not use_api:
            self._connect_to_db()
    
    def _connect_to_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return False
    
    def _disconnect_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def test_connection(self):
        """Test connection to server"""
        if self.use_api:
            try:
                response = requests.get(f"{API_URL}/api/test-connection", auth=API_AUTH)
                if response.status_code == 200:
                    logger.info(f"API connection test successful: {response.json()}")
                    return True
                else:
                    logger.error(f"API connection test failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"API connection error: {str(e)}")
                return False
        else:
            if not self.conn:
                return self._connect_to_db()
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                logger.info("Database connection test successful")
                return True
            except Exception as e:
                logger.error(f"Database connection test failed: {str(e)}")
                return False
    
    def add_vehicle(self, vehicle_number, vehicle_type="Motorcycle"):
        """Add a vehicle to the parking system"""
        timestamp = datetime.now()
        ticket_number = f"TKT{timestamp.strftime('%Y%m%d%H%M%S%f')[:18]}"
        
        # Determine vehicle type ID
        vehicle_type_id = 2 if vehicle_type.lower() == "motorcycle" else 1 if vehicle_type.lower() == "car" else 0
        
        if self.use_api:
            # Use API to add vehicle
            try:
                payload = {
                    "vehicleId": f"{vehicle_number.replace(' ', '')}-{timestamp.strftime('%Y%m%d%H%M%S')}",
                    "plateNumber": vehicle_number,
                    "vehicleType": vehicle_type,
                    "timestamp": timestamp.isoformat()
                }
                
                logger.info(f"Sending data to API: {json.dumps(payload)}")
                
                response = requests.post(
                    f"{API_URL}/api/parking",
                    json=payload,
                    auth=API_AUTH,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Vehicle added via API: {response.json()}")
                    return True, response.json()
                else:
                    logger.error(f"Failed to add vehicle via API: {response.status_code} - {response.text}")
                    return False, {"error": f"API error: {response.status_code}"}
            except Exception as e:
                logger.error(f"API request error: {str(e)}")
                return False, {"error": str(e)}
        else:
            # Use direct database connection
            if not self.conn:
                self._connect_to_db()
            
            if not self.conn:
                return False, {"error": "No database connection"}
            
            try:
                cursor = self.conn.cursor()
                
                # Insert new vehicle record
                query = """
                INSERT INTO public."Vehicles" (
                    "VehicleNumber", "VehicleType", "TicketNumber", 
                    "VehicleTypeId", "EntryTime"
                ) VALUES (%s, %s, %s, %s, %s) RETURNING "Id"
                """
                
                cursor.execute(
                    query, 
                    (vehicle_number, vehicle_type, ticket_number, vehicle_type_id, timestamp)
                )
                
                vehicle_id = cursor.fetchone()[0]
                self.conn.commit()
                cursor.close()
                
                logger.info(f"Vehicle added directly to database with ID: {vehicle_id}")
                return True, {
                    "id": vehicle_id,
                    "vehicleNumber": vehicle_number,
                    "ticketNumber": ticket_number,
                    "entryTime": timestamp.isoformat()
                }
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Database error when adding vehicle: {str(e)}")
                return False, {"error": str(e)}
    
    def verify_vehicle_saved(self, vehicle_number):
        """Verify if a vehicle with the given number was saved"""
        if self.use_api:
            try:
                response = requests.get(f"{API_URL}/api/vehicles", auth=API_AUTH)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        for vehicle in data["data"]:
                            if vehicle.get("VehicleNumber") == vehicle_number:
                                logger.info(f"Vehicle verified via API: {vehicle_number}")
                                return True, vehicle
                    logger.warning(f"Vehicle not found via API: {vehicle_number}")
                    return False, {"error": "Vehicle not found"}
                else:
                    logger.error(f"Failed to verify vehicle via API: {response.status_code}")
                    return False, {"error": f"API error: {response.status_code}"}
            except Exception as e:
                logger.error(f"API request error: {str(e)}")
                return False, {"error": str(e)}
        else:
            if not self.conn:
                self._connect_to_db()
            
            if not self.conn:
                return False, {"error": "No database connection"}
            
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    'SELECT * FROM public."Vehicles" WHERE "VehicleNumber" = %s ORDER BY "Id" DESC LIMIT 1',
                    (vehicle_number,)
                )
                vehicle = cursor.fetchone()
                cursor.close()
                
                if vehicle:
                    column_names = [desc[0] for desc in cursor.description]
                    vehicle_dict = dict(zip(column_names, vehicle))
                    logger.info(f"Vehicle verified in database: {vehicle_number}")
                    return True, vehicle_dict
                else:
                    logger.warning(f"Vehicle not found in database: {vehicle_number}")
                    return False, {"error": "Vehicle not found"}
            except Exception as e:
                logger.error(f"Database error when verifying vehicle: {str(e)}")
                return False, {"error": str(e)}
    
    def close(self):
        """Close connections"""
        self._disconnect_db()

class DBConnector:
    def __init__(self):
        """Initialize database connection"""
        self.db_config = {
            'host': '192.168.2.6',
            'port': '5432',
            'database': 'parkir2',
            'user': 'postgres',
            'password': 'postgres'
        }
    
    def connect(self):
        """Create database connection"""
        try:
            logger.info(f"Connecting to database at {self.db_config['host']}:{self.db_config['port']}")
            connection = psycopg2.connect(**self.db_config)
            logger.info("Database connection successful")
            return connection
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            logger.error(f"Connection details: host={self.db_config['host']}, port={self.db_config['port']}, db={self.db_config['database']}")
            raise
    
    def insert_vehicle(self, plate_number, vehicle_type):
        """Insert vehicle entry record
        
        Args:
            plate_number (str): Vehicle plate number
            vehicle_type (str): Either "Motor" or "Mobil"
        """
        connection = None
        try:
            # Generate ticket number
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ticket_number = f"PK-{timestamp}"
            
            # Connect to database
            connection = self.connect()
            cursor = connection.cursor()
            
            # Insert vehicle data
            query = """
                INSERT INTO Vehicles 
                (Id, VehicleType, IsParked, EntryTime, TicketNumber) 
                VALUES (%s, %s, %s, %s, %s)
                RETURNING Id;
            """
            
            vehicle_type_id = 1 if vehicle_type.lower() == "motor" else 2
            
            cursor.execute(query, (
                plate_number,
                vehicle_type_id,
                True,
                datetime.now(),
                ticket_number
            ))
            
            # Get the inserted ID
            inserted_id = cursor.fetchone()[0]
            
            # Commit transaction
            connection.commit()
            
            logger.info(f"Vehicle entry recorded: {plate_number}")
            
            # Return data for ticket printing
            return True, {
                "data": {
                    "plat": plate_number,
                    "tiket": ticket_number,
                    "waktu_masuk": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "jenis": vehicle_type.title()
                }
            }
            
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Error inserting vehicle: {e}")
            return False, {"error": str(e)}
            
        finally:
            if connection:
                connection.close()
    
    def get_vehicle_count(self):
        """Get total number of parked vehicles"""
        connection = None
        try:
            connection = self.connect()
            cursor = connection.cursor()
            
            query = "SELECT COUNT(*) FROM Vehicles WHERE IsParked = true;"
            cursor.execute(query)
            
            count = cursor.fetchone()[0]
            return True, {"total_kendaraan": count}
            
        except Exception as e:
            logger.error(f"Error getting vehicle count: {e}")
            return False, {"error": str(e)}
            
        finally:
            if connection:
                connection.close() 