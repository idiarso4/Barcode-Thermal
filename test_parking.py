import requests
import json
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parking_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('parking_test')

class ParkingClient:
    def __init__(self):
        self.base_url = 'http://192.168.2.6:5051/api'
        self.headers = {'Content-Type': 'application/json'}
    
    def test_connection(self):
        """Test koneksi ke server"""
        try:
            response = requests.get(f"{self.base_url}/test")
            result = response.json()
            
            print("\nTest Koneksi:")
            print("-" * 40)
            print(f"Status: {'Sukses' if response.ok else 'Gagal'}")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            logger.info(f"Connection test: {json.dumps(result, indent=2)}")
            return response.ok
            
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            print(f"Error: {str(e)}")
            return False
    
    def input_kendaraan(self, plat, jenis):
        """Input data kendaraan baru"""
        try:
            # Validate input
            if not plat or len(plat) < 4:
                raise ValueError("Nomor plat tidak valid")
            
            if jenis not in ['Motor', 'Mobil']:
                raise ValueError("Jenis kendaraan harus 'Motor' atau 'Mobil'")
            
            data = {
                'plat': plat,
                'jenis': jenis
            }
            
            print("\nMengirim Data Kendaraan:")
            print("-" * 40)
            print(f"Data: {json.dumps(data, indent=2)}")
            
            logger.info(f"Sending vehicle data: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/masuk",
                json=data,
                headers=self.headers,
                timeout=5
            )
            
            result = response.json()
            
            print("\nHasil:")
            print("-" * 40)
            print(f"Status: {'Sukses' if response.ok else 'Gagal'}")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if response.ok and result.get('data', {}).get('ticket'):
                success_msg = f"Tiket berhasil dibuat: {result['data']['ticket']}"
                print(f"\n{success_msg}")
                logger.info(success_msg)
            else:
                error_msg = f"Gagal membuat tiket: {result.get('message', 'Unknown error')}"
                print(f"\n{error_msg}")
                logger.error(error_msg)
            
            return result
            
        except ValueError as ve:
            error_msg = f"Validation error: {str(ve)}"
            logger.error(error_msg)
            print(f"Error: {str(ve)}")
            return None
            
        except requests.exceptions.Timeout:
            error_msg = "Server timeout - no response after 5 seconds"
            logger.error(error_msg)
            print(f"Error: {error_msg}")
            return None
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            return None

def validate_plat(plat):
    """Validate license plate format"""
    if not plat:
        return False
    # Basic validation - can be enhanced based on requirements
    return len(plat) >= 4 and len(plat) <= 10

def main():
    client = ParkingClient()
    
    # 1. Test Koneksi
    logger.info("Starting parking test client")
    if not client.test_connection():
        logger.error("Failed to connect to server")
        print("Gagal koneksi ke server!")
        return
    
    # 2. Input Data Kendaraan
    while True:
        print("\nInput Kendaraan Baru:")
        print("-" * 40)
        plat = input("Nomor Plat (atau 'q' untuk keluar): ").upper()
        
        if plat.lower() == 'q':
            break
        
        if not validate_plat(plat):
            print("Error: Format plat nomor tidak valid!")
            logger.warning(f"Invalid plate number attempted: {plat}")
            continue
        
        jenis = input("Jenis (Motor/Mobil): ").capitalize()
        if jenis not in ['Motor', 'Mobil']:
            print("Error: Jenis kendaraan tidak valid!")
            logger.warning(f"Invalid vehicle type attempted: {jenis}")
            continue
        
        result = client.input_kendaraan(plat, jenis)
        
        lanjut = input("\nInput kendaraan lagi? (y/n): ")
        if lanjut.lower() != 'y':
            break
    
    logger.info("Parking test client terminated")

if __name__ == "__main__":
    main() 