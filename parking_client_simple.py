import serial
import win32print
import time
import requests
import json
import logging
import os
from datetime import datetime
import random
import string
import sys

# Setup logging
logging.basicConfig(
    filename='parking_client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_client')

# API Configuration
API_BASE_URL = "http://192.168.2.6:5051/api"

# Arduino Configuration
ARDUINO_PORT = "COM7"
ARDUINO_BAUDRATE = 9600

# Create images directory if it doesn't exist
if not os.path.exists('images'):
    os.makedirs('images')

def print_ticket(data):
    """Print a ticket using direct ESC/POS commands"""
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        logger.info(f"Printing to: {printer_name}")
        print(f"🖨️ Mencetak ke printer: {printer_name}")

        # Extract data
        ticket_number = data['tiket']
        plate_number = data['plat']
        timestamp = data['waktu']
        
        # For longer ticket numbers (like TKT202503290219527426), use a shorter version for barcode
        barcode_ticket = ticket_number
        if len(ticket_number) > 15 and ticket_number.startswith("TKT"):
            # Extract just the numeric portion or the last 10 characters
            barcode_ticket = ticket_number[-10:]
            logger.info(f"Using shortened barcode ticket: {barcode_ticket} from {ticket_number}")

        # Open printer directly
        handle = win32print.OpenPrinter(printer_name)
        
        try:
            # Start a document
            job = win32print.StartDocPrinter(handle, 1, ("Parking Ticket", None, "RAW"))
            
            try:
                # Start a page
                win32print.StartPagePrinter(handle)
                
                # --- WRITE EACH COMMAND SEPARATELY ---
                
                # Initialize printer
                win32print.WritePrinter(handle, b"\x1B\x40")  # ESC @ - Initialize printer
                
                # Center align
                win32print.WritePrinter(handle, b"\x1B\x61\x01")  # ESC a 1 - Center alignment
                
                # Title with large font
                win32print.WritePrinter(handle, b"\x1B\x21\x30")  # ESC ! 0x30 - Double width/height
                win32print.WritePrinter(handle, "PARKIR RSI BNA\n".encode('ascii'))
                
                # Normal font
                win32print.WritePrinter(handle, b"\x1B\x21\x00")  # ESC ! 0x00 - Normal font
                
                # Line separator
                win32print.WritePrinter(handle, "====================\n\n".encode('ascii'))
                
                # Ticket info - display the full ticket number
                win32print.WritePrinter(handle, f"TIKET: {ticket_number}\n".encode('ascii'))
                win32print.WritePrinter(handle, f"PLAT : {plate_number}\n".encode('ascii'))
                win32print.WritePrinter(handle, f"WAKTU: {timestamp}\n\n".encode('ascii'))
                
                # Barcode (CODE39 format)
                win32print.WritePrinter(handle, b"\x1D\x48\x02")  # GS H 2 - HRI below barcode
                win32print.WritePrinter(handle, b"\x1D\x68\x50")  # GS h 80 - Barcode height 80 dots
                win32print.WritePrinter(handle, b"\x1D\x77\x02")  # GS w 2 - Barcode width (multiplier 2)
                win32print.WritePrinter(handle, b"\x1D\x6B\x04")  # GS k 4 - CODE39 barcode
                
                # Use the shortened barcode version for the actual barcode
                win32print.WritePrinter(handle, bytes([len(barcode_ticket)]))  # Length byte
                win32print.WritePrinter(handle, barcode_ticket.encode('ascii'))  # Barcode data
                
                # Line feeds after barcode
                win32print.WritePrinter(handle, b"\n\n")
                
                # Footer
                win32print.WritePrinter(handle, "Terima kasih\nJangan hilangkan tiket ini\n\n".encode('ascii'))
                
                # Cut paper
                win32print.WritePrinter(handle, b"\x1D\x56\x42")  # GS V B - Cut paper
                
                # End the page
                win32print.EndPagePrinter(handle)
                
                logger.info("Ticket printed successfully!")
                return True
            finally:
                # End the document
                win32print.EndDocPrinter(handle)
        finally:
            # Close the printer
            win32print.ClosePrinter(handle)
        
    except Exception as e:
        logger.error(f"Error printing ticket: {e}")
        print(f"❌ Error printing ticket: {e}")
        
        # FALLBACK METHOD - try a simpler approach with text only
        try:
            print("Mencoba metode cetak alternatif...")
            printer_name = win32print.GetDefaultPrinter()
            
            # Create a text file with ticket data
            with open("temp_ticket.txt", "w") as f:
                f.write(f"PARKIR RSI BNA\n\n")
                f.write(f"TIKET: {data['tiket']}\n")
                f.write(f"PLAT : {data['plat']}\n")
                f.write(f"WAKTU: {data['waktu']}\n\n")
                f.write(f"Terima kasih\n")
            
            # Print the text file directly
            with open("temp_ticket.txt", "rb") as f:
                text_data = f.read()
            
            # Send to printer
            handle = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(handle, 1, ("Text Ticket", None, "RAW"))
                try:
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, text_data)
                    win32print.EndPagePrinter(handle)
                    print("✅ Cetak alternatif berhasil")
                    return True
                finally:
                    win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
                
                # Delete temp file
                if os.path.exists("temp_ticket.txt"):
                    os.remove("temp_ticket.txt")
                    
        except Exception as e2:
            logger.error(f"Alternative printing also failed: {e2}")
            print(f"❌ Semua metode cetak gagal: {str(e2)}")
            return False

def test_connection():
    """Test connection to the API server"""
    try:
        response = requests.get(f"{API_BASE_URL}/test", timeout=5)
        if response.ok:
            data = response.json()
            logger.info(f"Connected to server. Response: {json.dumps(data)}")
            return True, data
        else:
            logger.error(f"Server error: {response.status_code}")
            return False, {"message": f"Server error: {response.status_code}"}
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return False, {"message": f"Connection error: {str(e)}"}

def process_vehicle(plate):
    """Process vehicle entry and print ticket"""
    try:
        # Prepare data
        data = {
            "plat": plate,
            "vehicleType": "Motor",
            "vehicleTypeId": 2,
            "isParked": True
        }
        
        logger.info(f"Sending data to server: {json.dumps(data)}")
        
        # Send to API
        response = requests.post(
            f"{API_BASE_URL}/masuk",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.ok:
            result = response.json()
            logger.info(f"Server response: {json.dumps(result)}")
            
            if result.get('success'):
                # Extract ticket data
                ticket_data = {
                    'tiket': result['data']['ticket'],
                    'plat': plate,
                    'waktu': result['data']['waktu']
                }
                
                # Print ticket
                if print_ticket(ticket_data):
                    print("✅ Tiket berhasil dicetak")
                else:
                    print("❌ Gagal mencetak tiket")
                
                return True, ticket_data
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Server error: {error_msg}")
                return False, error_msg
        else:
            logger.error(f"Server error: {response.status_code}")
            return False, f"Server error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error processing vehicle: {str(e)}")
        return False, f"Error: {str(e)}"

def generate_random_plate():
    """Generate a random plate number"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"{letters}{numbers}"

def test_server_ticket():
    """Test printing with a specific server ticket format"""
    # Example ticket from server
    sample_data = {
        'tiket': 'TKT202503290219527426',
        'plat': 'QB1234',
        'waktu': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print("\n===== TEST SERVER TICKET FORMAT =====")
    print(f"Ticket: {sample_data['tiket']}")
    print(f"Plate : {sample_data['plat']}")
    print(f"Time  : {sample_data['waktu']}")
    
    success = print_ticket(sample_data)
    if success:
        print("✅ Test server format berhasil")
    else:
        print("❌ Test server format gagal")
    
    return success

def main():
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test-server-ticket":
        test_server_ticket()
        return
        
    # Print header
    print("""
==================================================
     SISTEM PARKIR RSI BANJARNEGARA       
==================================================
Mode: Metode Cetak Sederhana
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

    # Try to open Arduino connection
    arduino = None
    try:
        arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        print(f"✅ Arduino terdeteksi pada port {ARDUINO_PORT}")
        simulate_mode = False
    except Exception as e:
        print(f"❌ Gagal koneksi ke Arduino: {str(e)}")
        print("👉 Jalankan dalam mode simulasi keyboard (tekan ENTER untuk memicu)")
        simulate_mode = True

    if simulate_mode:
        # Simulation mode
        try:
            while True:
                key = input("\nTekan ENTER untuk memproses kendaraan atau ketik 'exit' untuk keluar: ")
                if key.lower() == 'exit':
                    break
                
                # Generate random plate number
                plate = generate_random_plate()
                print(f"\n👉 Memproses kendaraan dengan plat: {plate}")
                
                # Process vehicle
                success, result = process_vehicle(plate)
                
                if success:
                    print("\n✅ Tiket Berhasil Dibuat:")
                    print(f"Nomor Tiket : {result['tiket']}")
                    print(f"Nomor Plat  : {result['plat']}")
                    print(f"Waktu Masuk : {result['waktu']}")
                else:
                    print(f"\n❌ Gagal: {result}")
                
                print("\nSiap memproses kendaraan berikutnya...")
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
    else:
        # Arduino mode
        try:
            print("\nSiap memproses kendaraan...")
            print("Status: Menunggu input dari tombol...")
            
            while True:
                # Check for incoming data from Arduino
                if arduino.in_waiting > 0:
                    received_data = arduino.readline().decode('utf-8').strip()
                    
                    if received_data:
                        print(f"\nMenerima input: {received_data}")
                        
                        # If the data is "READY" or similar simple message, generate a random plate
                        if len(received_data) < 4 or received_data.upper() == "READY":
                            plate = generate_random_plate()
                            print(f"Menggunakan nomor plat otomatis: {plate}")
                        else:
                            plate = received_data
                            print(f"Menggunakan nomor plat dari input: {plate}")
                        
                        # Process vehicle
                        success, result = process_vehicle(plate)
                        
                        if success:
                            print("\n✅ Tiket Berhasil Dibuat:")
                            print(f"Nomor Tiket : {result['tiket']}")
                            print(f"Nomor Plat  : {result['plat']}")
                            print(f"Waktu Masuk : {result['waktu']}")
                        else:
                            print(f"\n❌ Gagal: {result}")
                        
                        print("\nSiap memproses kendaraan berikutnya...")
                
                # Short delay to reduce CPU usage
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
        finally:
            if arduino and arduino.is_open:
                arduino.close()

if __name__ == "__main__":
    main() 