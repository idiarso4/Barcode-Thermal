import serial
import time
import logging
import random
import string
import json
import requests
import os
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='parking_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# Configuration
API_URL = "http://localhost:8000/api"
ARDUINO_PORT = "COM7"
ARDUINO_BAUDRATE = 9600
SIMULATE = False

def connect_serial():
    """Connect to the serial port for printer"""
    try:
        ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=2)
        logger.info(f"Connected to serial port {ARDUINO_PORT}")
        print(f"✅ Terhubung ke port {ARDUINO_PORT}")
        return ser
    except Exception as e:
        logger.error(f"Failed to connect to serial port: {str(e)}")
        print(f"❌ Gagal koneksi ke serial port: {str(e)}")
        return None

def print_ticket_serial(ser, data):
    """Print ticket directly to thermal printer via serial port"""
    try:
        if not ser:
            logger.error("No serial connection available")
            print("❌ Tidak ada koneksi serial")
            return False
            
        # Extract data
        ticket_number = data['tiket']
        plate_number = data['plat']
        timestamp = data['waktu']
        
        logger.info(f"Printing ticket: {ticket_number} for plate: {plate_number}")
        print(f"🖨️ Mencetak tiket: {ticket_number} untuk plat: {plate_number}")
        
        # For longer ticket numbers, use a shortened version for barcode
        barcode_ticket = ticket_number
        if len(ticket_number) > 15 and ticket_number.startswith("TKT"):
            barcode_ticket = ticket_number[-10:]
            logger.info(f"Using shortened barcode: {barcode_ticket} from {ticket_number}")
        
        # ESC/POS commands for thermal printer
        commands = bytearray()
        
        # Initialize printer
        commands.extend(b"\x1B\x40")  # ESC @ - Initialize printer
        
        # Center align
        commands.extend(b"\x1B\x61\x01")  # ESC a 1 - Center alignment
        
        # Title with large font
        commands.extend(b"\x1B\x21\x30")  # ESC ! 0x30 - Double width/height
        commands.extend("PARKIR RSI BNA\n".encode('ascii'))
        
        # Normal font
        commands.extend(b"\x1B\x21\x00")  # ESC ! 0x00 - Normal font
        
        # Line separator
        commands.extend("====================\n\n".encode('ascii'))
        
        # Ticket info
        commands.extend(f"TIKET: {ticket_number}\n".encode('ascii'))
        commands.extend(f"PLAT : {plate_number}\n".encode('ascii'))
        commands.extend(f"WAKTU: {timestamp}\n\n".encode('ascii'))
        
        # Barcode (CODE39 format)
        commands.extend(b"\x1D\x48\x02")  # GS H 2 - HRI below barcode
        commands.extend(b"\x1D\x68\x50")  # GS h 80 - Barcode height 80 dots
        commands.extend(b"\x1D\x77\x02")  # GS w 2 - Barcode width (multiplier 2)
        commands.extend(b"\x1D\x6B\x04")  # GS k 4 - CODE39 barcode
        
        # Barcode data
        commands.append(len(barcode_ticket))  # Length byte
        commands.extend(barcode_ticket.encode('ascii'))  # Barcode data
        
        # Footer
        commands.extend(b"\n\n")
        commands.extend("Terima kasih\nJangan hilangkan tiket ini\n\n".encode('ascii'))
        
        # Cut paper
        commands.extend(b"\x1D\x56\x42")  # GS V B - Cut paper
        
        # Send commands to printer via serial port
        ser.write(commands)
        ser.flush()
        
        # Wait for printing to complete
        time.sleep(1)
        
        logger.info("Ticket printed successfully")
        print("✅ Tiket berhasil dicetak")
        return True
        
    except Exception as e:
        logger.error(f"Error printing ticket: {str(e)}")
        print(f"❌ Gagal mencetak tiket: {str(e)}")
        return False

def process_vehicle(plate_number=None):
    """Process a vehicle entry"""
    try:
        # Generate random plate if not provided
        if not plate_number:
            plate_number = generate_random_plate()
            
        logger.info(f"Processing vehicle with plate: {plate_number}")
        print(f"🚗 Memproses kendaraan dengan plat: {plate_number}")
        
        # Send API request to process entry
        url = f"{API_URL}/entry"
        payload = {"plat": plate_number}
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"API response: {data}")
            
            if 'tiket' in data and 'plat' in data and 'waktu' in data:
                return data
            else:
                logger.error("API response missing required fields")
                print("❌ Respons API tidak lengkap")
                return None
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            print(f"❌ Error API: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing vehicle: {str(e)}")
        print(f"❌ Gagal memproses kendaraan: {str(e)}")
        return None

def test_connection():
    """Test API connection"""
    try:
        url = f"{API_URL}/status"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"API status: {data}")
            return True, data
        else:
            logger.error(f"API connection error: {response.status_code}")
            return False, {"message": f"Error {response.status_code}"}
            
    except Exception as e:
        logger.error(f"API connection error: {str(e)}")
        return False, {"message": str(e)}

def generate_random_plate():
    """Generate a random license plate"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"{letters}{numbers}"

def main():
    # Print header
    print("""
==================================================
     SISTEM PARKIR RSI BANJARNEGARA       
==================================================
Mode: Cetak Via Serial Port
Status: Menunggu Kendaraan...
    """)
    
    # Test API connection
    is_connected, data = test_connection()
    if is_connected:
        print("✅ Terhubung ke server")
        if data and 'total_kendaraan' in data:
            print(f"📊 Jumlah kendaraan: {data['total_kendaraan']}")
    else:
        print("❌ Tidak dapat terhubung ke server")
        print(f"Error: {data.get('message', 'Unknown error')}")
        return

    # Try to open serial connection for printer
    ser = connect_serial()
    if not ser and not SIMULATE:
        print("❌ Gagal koneksi ke printer via serial")
        print("🔄 Ingin melanjutkan dalam mode simulasi? (y/n)")
        choice = input("> ")
        if choice.lower() != 'y':
            return
        SIMULATE = True
    
    print("\n✅ Siap memproses kendaraan")
    print("Tekan ENTER untuk memproses kendaraan atau 'q' untuk keluar")
    
    # Main processing loop
    while True:
        user_input = input("> ")
        
        if user_input.lower() == 'q':
            break
            
        # Process vehicle
        print("\n⏳ Memproses kendaraan...")
        
        # Use automatic plate
        data = process_vehicle()
        
        if data:
            print(f"✅ Kendaraan diproses: {data['plat']}")
            print(f"🎫 Nomor tiket: {data['tiket']}")
            print(f"🕒 Waktu masuk: {data['waktu']}")
            
            # Print ticket
            if ser:
                print_ticket_serial(ser, data)
            else:
                print("ℹ️ Mode simulasi - tidak ada printer")
                print(f"Tiket {data['tiket']} untuk plat {data['plat']} terbentuk")
            
        print("\nSiap untuk kendaraan berikutnya...")
    
    # Close serial connection
    if ser:
        ser.close()
        print("Serial port ditutup")
    
    print("Program selesai")

if __name__ == "__main__":
    main() 