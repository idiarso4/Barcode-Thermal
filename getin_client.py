from parking_api import ParkingAPI
from ticket_printer import TicketPrinter
from button_handler import ParkingButton
import time
import json
import logging
import threading
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parking.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GetInTerminal:
    def __init__(self):
        """Initialize terminal"""
        self.api = ParkingAPI()
        self.printer = TicketPrinter()
        self.printer_busy = False
        self.printer_lock = threading.Lock()
        self.button = None
    
    def process_vehicle_entry(self, plate_number, vehicle_type):
        """Process vehicle entry"""
        try:
            # Validate input
            if not plate_number:
                logger.error(f"Invalid plate number: {plate_number}")
                return False, "Nomor plat tidak valid"
            
            # Register vehicle via API
            success, result = self.api.add_vehicle(plate_number, vehicle_type)
            
            if success:
                logger.info(f"Vehicle entry processed successfully: {plate_number}")
                return True, result
            else:
                logger.error(f"Failed to register vehicle: {result}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error processing vehicle entry: {e}")
            return False, str(e)
    
    def run(self):
        """Run the terminal"""
        print("\n" + "="*50)
        print("     TERMINAL MASUK PARKIR RSI BANJARNEGARA")
        print("="*50)
        print("\nMode: Otomatis (Push Button)")
        print("Status: Menunggu kendaraan...")
        print("\nTekan Ctrl+C untuk menghentikan program")
        
        # Test API connection
        success, result = self.api.test_connection()
        if success:
            print(f"\n✅ Koneksi ke API berhasil")
            print(f"📊 Total kendaraan: {result.get('total_kendaraan', 0)}")
        else:
            print("\n❌ Gagal terhubung ke API")
            print("Silakan cek koneksi API dan coba lagi.")
            return
        
        # Initialize and start button handler
        self.button = ParkingButton(self)
        self.button.start()
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nMenghentikan program...")
        finally:
            if self.button:
                self.button.stop()
            print("Program dihentikan")

if __name__ == "__main__":
    terminal = GetInTerminal()
    terminal.run() 