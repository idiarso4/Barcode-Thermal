import logging
import json
import os
import time
import requests
import win32print
import win32ui
import win32con
from PIL import Image, ImageDraw, ImageFont, ImageWin
import barcode
from barcode.writer import ImageWriter
from datetime import datetime
import serial
import serial.tools.list_ports
import random
import string
import tempfile

# Setup logging
logging.basicConfig(
    filename='parking_client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_client')

class ParkingClientWin32Print:
    def __init__(self):
        self.base_url = "http://192.168.2.6:5051/api"
        self.offline_file = "offline_data.json"
        self.counter_file = "counter.txt"
        self.arduino = None
        self.printer_name = None
        self.simulate_mode = False
        self.initialize_devices()

    def find_arduino_port(self):
        """Mencari port Arduino yang terhubung"""
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            # Log semua port yang ditemukan
            logger.info(f"Port ditemukan: {port.device} - {port.description}")
            # Arduino biasanya terdeteksi dengan nama "Arduino" atau "CH340"
            if "arduino" in port.description.lower() or "ch340" in port.description.lower():
                return port.device
        return None

    def initialize_devices(self):
        # Inisialisasi printer
        try:
            # Mendapatkan daftar printer
            printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)]
            logger.info(f"Printer tersedia: {printers}")
            
            # Mencari printer EPSON
            for printer_name in printers:
                if "EPSON" in printer_name.upper() or "TM-T" in printer_name.upper():
                    self.printer_name = printer_name
                    logger.info(f"Printer EPSON ditemukan: {printer_name}")
                    print(f"✅ Printer terdeteksi: {printer_name}")
                    break
            
            if not self.printer_name:
                logger.warning("Printer EPSON tidak ditemukan")
                print("❌ Printer EPSON tidak ditemukan")
                # Mencoba menggunakan printer default
                self.printer_name = win32print.GetDefaultPrinter()
                if self.printer_name:
                    print(f"ℹ️ Menggunakan printer default: {self.printer_name}")
                
        except Exception as e:
            logger.error(f"Gagal menginisialisasi printer: {str(e)}")
            print("❌ Gagal menginisialisasi printer")
            self.printer_name = None

        # Inisialisasi koneksi Arduino
        try:
            arduino_port = "COM7"  # Menggunakan port tetap untuk saat ini
            
            # Jika port default gagal, coba cari Arduino secara otomatis
            if not arduino_port:
                arduino_port = self.find_arduino_port()
                
            if not arduino_port:
                logger.error("Perangkat Arduino tidak ditemukan")
                print("❌ Perangkat Arduino tidak ditemukan")
                print("👉 Jalankan dalam mode simulasi keyboard (tekan ENTER untuk memicu)")
                self.simulate_mode = True
                return
                
            try:
                self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
                time.sleep(2)  # Tunggu Arduino reset
                logger.info(f"Koneksi Arduino berhasil pada port {arduino_port}")
                print(f"✅ Arduino terdeteksi pada port {arduino_port}")
                self.simulate_mode = False
            except Exception as e:
                logger.error(f"Gagal koneksi ke Arduino: {str(e)}")
                print(f"❌ Gagal koneksi ke Arduino: {str(e)}")
                print("👉 Jalankan dalam mode simulasi keyboard (tekan ENTER untuk memicu)")
                self.arduino = None
                self.simulate_mode = True
                
        except Exception as e:
            logger.error(f"Error dalam inisialisasi Arduino: {str(e)}")
            print(f"❌ Error: {str(e)}")
            self.arduino = None
            self.simulate_mode = True

    def print_ticket_escpos(self, data):
        """Print a ticket using direct ESC/POS commands for thermal printers"""
        try:
            printer_name = self.printer_name or win32print.GetDefaultPrinter()
            if not printer_name:
                logger.error("No printer available")
                return False
                
            # Opening the printer directly
            handle = win32print.OpenPrinter(printer_name)
            
            try:
                # Generate ESC/POS commands
                commands = self.generate_escpos_commands(data)
                
                # Start a print job
                job = win32print.StartDocPrinter(handle, 1, ("Parking Ticket", None, "RAW"))
                try:
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, commands)
                    win32print.EndPagePrinter(handle)
                    logger.info(f"Ticket printed successfully: {data['tiket']}")
                    return True
                finally:
                    win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
                
        except Exception as e:
            logger.error(f"Error printing ticket with ESC/POS: {str(e)}")
            print(f"❌ Gagal mencetak tiket: {str(e)}")
            
            # Save a copy of ticket image as fallback
            self.create_ticket_image(data)
            return False
            
    def generate_escpos_commands(self, data):
        """Generate ESC/POS commands for thermal printer"""
        # Initialize command bytes
        commands = bytearray()
        
        # Reset printer
        commands.extend(b"\x1B\x40")
        
        # Center alignment
        commands.extend(b"\x1B\x61\x01")
        
        # Title - double height and width
        commands.extend(b"\x1B\x21\x30")  # Double width, double height
        commands.extend(b"=== PARKIR RSI BNA ===\n")
        
        # Reset text format
        commands.extend(b"\x1B\x21\x00")
        commands.extend(b"\n")
        
        # Ticket details - normal text
        commands.extend(b"TIKET: ")
        commands.extend(data['tiket'].encode())
        commands.extend(b"\n")
        
        commands.extend(b"PLAT : ")
        commands.extend(data['plat'].encode())
        commands.extend(b"\n")
        
        commands.extend(b"WAKTU: ")
        commands.extend(data['waktu'].encode())
        commands.extend(b"\n\n")
        
        # Center alignment for barcode
        commands.extend(b"\x1B\x61\x01")
        
        # Barcode settings - from note.md
        ticket_number = data['tiket']
        
        # Fix for bytes object error - use individual command extensions
        commands.extend(b"\x1D\x48\x02")  # HRI position - below barcode
        commands.extend(b"\x1D\x68\x50")  # Barcode height = 80 dots
        commands.extend(b"\x1D\x77\x02")  # Barcode width multiplier (2)
        commands.extend(b"\x1D\x6B\x04")  # Select CODE39
        
        # Properly encode ticket number with length byte
        data_length = len(ticket_number)
        commands.append(data_length)  # Single byte for length
        commands.extend(ticket_number.encode())  # Add the data
        
        # Add line feeds after barcode
        commands.extend(b"\n\n")
        
        # Footer
        commands.extend(b"Terima kasih\n")
        commands.extend(b"Jangan hilangkan tiket ini\n\n")
        
        # Cut paper
        commands.extend(b"\x1D\x56\x41\x03")  # Cut with 3-dot feed
        
        return commands

    def print_ticket_win32(self, data):
        """Print a ticket using win32print directly"""
        try:
            # Try ESC/POS printing first (recommended for thermal printers)
            if self.print_ticket_escpos(data):
                return True
                
            # If ESC/POS fails, try image-based printing as fallback
            logger.warning("ESC/POS printing failed, falling back to image-based printing")
            
            # Create ticket image
            ticket_image = self.create_ticket_image(data)
            if not ticket_image:
                logger.error("Failed to create ticket image")
                return False
                
            # Save temporary file
            temp_file = "temp_ticket.bmp"
            ticket_image.save(temp_file)
            
            # Get printer handle
            printer_name = self.printer_name or win32print.GetDefaultPrinter()
            logger.info(f"Using printer: {printer_name}")
            
            try:
                # Standard Win32 printing with RAW mode
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("Parking Ticket", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hPrinter)
                        
                        # Open the image and convert to bitmap data
                        with open(temp_file, 'rb') as f:
                            img_data = f.read()
                        
                        # Write the bitmap data to the printer
                        win32print.WritePrinter(hPrinter, img_data)
                        win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)
                
                logger.info(f"Ticket printed successfully: {data['tiket']}")
                    
                # Clean up temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
                return True
                
            except Exception as e:
                # If all printing methods fail, just save the image
                logger.error(f"All printing methods failed: {str(e)}")
                print(f"❌ Gagal mencetak tiket: {str(e)}")
                
                # Ensure image is saved
                image_path = f"images/ticket_{data['tiket']}.png"
                print(f"💾 Tiket disimpan: {image_path}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error printing ticket: {str(e)}")
            print(f"❌ Gagal mencetak tiket: {str(e)}")
            
            # Save the image so at least we have a record
            try:
                if not os.path.exists('images'):
                    os.makedirs('images')
                    
                image_path = f"images/ticket_{data['tiket']}.png"
                logger.info(f"Saving ticket image to {image_path} as fallback")
                print(f"💾 Tiket disimpan: {image_path}")
            except Exception as save_err:
                logger.error(f"Error saving ticket image: {str(save_err)}")
                
            return False

    def create_ticket_image(self, data):
        """Create an image of the ticket for printing"""
        # Create image with white background
        width = 400
        height = 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to load a nice font, fallback to default if not found
            try:
                font_header = ImageFont.truetype("arial.ttf", 24)
                font_normal = ImageFont.truetype("arial.ttf", 18) 
            except:
                font_header = ImageFont.load_default()
                font_normal = ImageFont.load_default()

            # Header
            draw.text((width//2, 20), "RSI BANJARNEGARA", font=font_header, fill='black', anchor='mt')
            draw.text((width//2, 50), "================", font=font_header, fill='black', anchor='mt')

            # Ticket details
            draw.text((20, 100), f"TIKET: {data['tiket']}", font=font_normal, fill='black')
            draw.text((20, 130), f"PLAT : {data['plat']}", font=font_normal, fill='black')
            draw.text((20, 160), f"WAKTU: {data['waktu']}", font=font_normal, fill='black')

            # Generate barcode
            barcode_class = barcode.get_barcode_class('code39')
            barcode_instance = barcode_class(data['tiket'], writer=ImageWriter())
            barcode_image = barcode_instance.render()
            
            # Resize barcode to fit ticket width
            barcode_image = barcode_image.resize((width-40, 100))
            
            # Paste barcode
            image.paste(barcode_image, (20, 200))
            
            # Add additional text
            draw.text((width//2, 320), "Mohon simpan tiket ini", font=font_normal, fill='black', anchor='mt')
            draw.text((width//2, 350), "sampai keluar area parkir", font=font_normal, fill='black', anchor='mt')
            
            # Add contact information at bottom
            draw.text((width//2, height-40), "Terima Kasih", font=font_normal, fill='black', anchor='mt')
            draw.text((width//2, height-20), "RSI Banjarnegara", font=font_normal, fill='black', anchor='mt')
            
            # Save a copy in images directory for reference
            if not os.path.exists('images'):
                os.makedirs('images')
                
            image_path = f"images/ticket_{data['tiket']}.png"
            image.save(image_path)
            logger.info(f"Ticket image saved to {image_path}")

            return image

        except Exception as e:
            logger.error(f"Error creating ticket image: {str(e)}")
            return None

    def test_connection(self):
        """Test API server connection"""
        try:
            response = requests.get(f"{self.base_url}/test", timeout=5)
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

    def process_vehicle(self, plate):
        """Process vehicle entry and print ticket"""
        try:
            # Prepare data according to API specification
            data = {
                "plat": plate,                # Plate number
                "vehicleType": "Motor",       # Default to motorcycle
                "vehicleTypeId": 2,           # 2 = motor, 1 = mobil
                "officeId": "OFF0001",        # Default office ID
                "isParked": True              # Vehicle is parked
            }
            
            logger.info(f"Sending data to server: {json.dumps(data)}")
            
            try:
                # Send to either /api/masuk or /api/v2/masuk
                url = f"{self.base_url}/v2/masuk"
                
                response = requests.post(
                    url, 
                    json=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=5
                )
                
                # If v2 fails, try the original endpoint
                if not response.ok and "/v2/" in url:
                    logger.warning(f"V2 endpoint failed, trying original endpoint")
                    url = f"{self.base_url}/masuk"
                    response = requests.post(
                        url, 
                        json=data,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
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
                        if self.print_ticket_win32(ticket_data):
                            print("✅ Tiket berhasil dicetak")
                        else:
                            print("❌ Gagal mencetak tiket")
                            print(f"💾 Tiket disimpan: images/ticket_{ticket_data['tiket']}.png")
                            
                        return True, ticket_data
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        logger.error(f"Server error: {error_msg}")
                        return False, error_msg
                else:
                    logger.error(f"Server error: {response.status_code} - {response.text}")
                    return False, f"Server error: {response.status_code}"
                    
            except requests.exceptions.Timeout:
                logger.error("Connection timeout")
                return False, "Connection timeout"
            except requests.exceptions.ConnectionError:
                logger.error("Connection error - server tidak dapat dijangkau")
                return False, "Connection error - server tidak dapat dijangkau"
            except Exception as e:
                logger.error(f"Error sending data: {str(e)}")
                return False, f"Error: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error processing vehicle: {str(e)}")
            return False, f"Error: {str(e)}"

    def read_arduino_data(self):
        """Read data from Arduino"""
        try:
            if self.arduino and self.arduino.in_waiting > 0:
                data = self.arduino.readline().decode('utf-8').strip()
                if data:
                    logger.info(f"Received from Arduino: {data}")
                    
                    # If data is too short to be a license plate, assume it's a button press
                    # and generate a random plate
                    if len(data) < 4:
                        # Generate random plate number
                        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
                        numbers = ''.join(random.choices(string.digits, k=4))
                        plate = f"{letters}{numbers}"
                        logger.info(f"Generated random plate from button press: {plate}")
                        return plate
                    else:
                        return data
        except Exception as e:
            logger.error(f"Error reading Arduino data: {str(e)}")
        return None

    def simulate_button_press(self):
        """Simulate a button press with auto-generated plate number"""
        # Generate random plate number
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = ''.join(random.choices(string.digits, k=4))
        plate = f"{letters}{numbers}"
        
        logger.info(f"Simulated button press - generated plate: {plate}")
        print(f"\n👉 Memproses kendaraan dengan plat: {plate}")
        
        return self.process_vehicle(plate)

def main():
    client = ParkingClientWin32Print()
    print("""
==================================================
     SISTEM PARKIR RSI BANJARNEGARA       
==================================================
Mode: ESC/POS Thermal Printing
Status: Menunggu Kendaraan...
    """)
    
    # Tes koneksi API
    is_connected, data = client.test_connection()
    if is_connected:
        print("✅ Terhubung ke server")
        if data and 'total_kendaraan' in data:
            print(f"📊 Jumlah kendaraan: {data['total_kendaraan']}")
    else:
        print("❌ Tidak dapat terhubung ke server - Mode Offline Aktif")

    if client.simulate_mode:
        print("\n🔄 Mode Simulasi Aktif - Tekan ENTER untuk mensimulasikan push button")
        
        try:
            while True:
                key = input("\nTekan ENTER untuk memproses kendaraan atau ketik 'exit' untuk keluar: ")
                if key.lower() == 'exit':
                    break
                    
                success, result = client.simulate_button_press()
                
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
        if not client.arduino:
            print("❌ Arduino tidak terdeteksi! Program dihentikan.")
            return

        print("\nSiap memproses kendaraan...")
        print("Status: Menunggu input dari tombol...")
        
        try:
            while True:
                # Baca data dari Arduino
                plat = client.read_arduino_data()
                if plat:
                    print(f"\nMenerima input: {plat}")
                    
                    # Treat any input from Arduino as a button press
                    # Generate a random plate
                    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
                    numbers = ''.join(random.choices(string.digits, k=4))
                    auto_plate = f"{letters}{numbers}"
                    
                    # Use original plate if it meets minimum requirements
                    if len(plat) >= 4 and len(plat) <= 10:
                        plate_to_use = plat
                        print(f"Menggunakan nomor plat dari input: {plate_to_use}")
                    else:
                        plate_to_use = auto_plate
                        print(f"Menggunakan nomor plat otomatis: {plate_to_use}")
                        
                    success, result = client.process_vehicle(plate_to_use)
                    
                    if success:
                        print("\n✅ Tiket Berhasil Dibuat:")
                        print(f"Nomor Tiket : {result['tiket']}")
                        print(f"Nomor Plat  : {result['plat']}")
                        print(f"Waktu Masuk : {result['waktu']}")
                    else:
                        print(f"\n❌ Gagal: {result}")
                        
                    print("\nSiap memproses kendaraan berikutnya...")
                
                time.sleep(0.1)  # Jeda singkat untuk mengurangi beban CPU
                    
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
        finally:
            if client.arduino:
                client.arduino.close()

if __name__ == "__main__":
    main() 