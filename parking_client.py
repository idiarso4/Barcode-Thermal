import logging
import json
import os
from datetime import datetime
import requests
import serial
import serial.tools.list_ports
import time
import win32print
import win32ui
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter

# Setup logging
logging.basicConfig(
    filename='parking_client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_client')

class ParkingClient:
    def __init__(self):
        self.base_url = "http://192.168.2.6:5051/api"
        self.offline_file = "offline_data.json"
        self.counter_file = "counter.txt"
        self.printer = None
        self.arduino = None
        self.printer_name = None
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
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)
            logger.info(f"Printer tersedia: {printers}")
            
            # Mencari printer EPSON
            for printer in printers:
                printer_name = printer[2]
                if "EPSON" in printer_name.upper() or "TM-T" in printer_name.upper():
                    self.printer_name = printer_name
                    logger.info(f"Printer EPSON ditemukan: {printer_name}")
                    print(f"✅ Printer terdeteksi: {printer_name}")
                    break
            
            if not self.printer_name:
                logger.error("Printer EPSON tidak ditemukan")
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
            arduino_port = self.find_arduino_port()
            if arduino_port is None:
                logger.error("Perangkat Arduino tidak ditemukan")
                print("❌ Perangkat Arduino tidak ditemukan")
                return

            self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
            time.sleep(2)  # Tunggu Arduino reset
            logger.info(f"Koneksi Arduino berhasil pada port {arduino_port}")
            print(f"✅ Arduino terdeteksi pada port {arduino_port}")
        except Exception as e:
            logger.error(f"Gagal koneksi ke Arduino: {str(e)}")
            self.arduino = None

    def create_ticket_image(self, data):
        # Create image with white background
        width = 400
        height = 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to load a nice font, fallback to default if not found
            try:
                font_header = ImageFont.truetype("arial.ttf", 24)
                font_normal = ImageFont.truetype("arial.ttf", 20)
            except:
                font_header = ImageFont.load_default()
                font_normal = ImageFont.load_default()

            # Header
            draw.text((width//2, 20), "RSI BANJARNEGARA", font=font_header, fill='black', anchor='mt')
            draw.text((width//2, 50), "================", font=font_header, fill='black', anchor='mt')

            # Ticket details
            draw.text((20, 100), f"TIKET: {data['tiket']}", font=font_normal, fill='black')
            draw.text((20, 140), f"PLAT : {data['plat']}", font=font_normal, fill='black')
            draw.text((20, 180), f"WAKTU: {data['waktu']}", font=font_normal, fill='black')

            # Generate barcode
            barcode_class = barcode.get_barcode_class('code39')
            barcode_instance = barcode_class(data['tiket'], writer=ImageWriter())
            barcode_image = barcode_instance.render()
            
            # Resize barcode to fit ticket width
            barcode_image = barcode_image.resize((width-40, 100))
            
            # Paste barcode
            image.paste(barcode_image, (20, 240))

            return image

        except Exception as e:
            logger.error(f"Error creating ticket image: {str(e)}")
            return None

    def print_ticket(self, data):
        if not self.printer_name:
            logger.warning("No printer available")
            print("❌ Tidak ada printer yang tersedia")
            return False
            
        try:
            # Create ticket image
            ticket_image = self.create_ticket_image(data)
            if not ticket_image:
                return False

            # Save temporary file
            temp_file = "temp_ticket.bmp"
            ticket_image.save(temp_file)

            # Print using default Windows printer
            hprinter = win32print.OpenPrinter(self.printer_name)
            try:
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(self.printer_name)
                
                # Start print job
                hdc.StartDoc('Parking Ticket')
                hdc.StartPage()
                
                # Load and print image
                dib = ImageWin.Dib(ticket_image)
                dib.draw(hdc.GetHandleOutput(), (0, 0, ticket_image.width, ticket_image.height))
                
                # End print job
                hdc.EndPage()
                hdc.EndDoc()
                
                logger.info(f"Ticket printed successfully: {data['tiket']}")
                print("✅ Tiket berhasil dicetak")
                return True
                
            finally:
                win32print.ClosePrinter(hprinter)
                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
        except Exception as e:
            logger.error(f"Error printing ticket: {str(e)}")
            print(f"❌ Gagal mencetak tiket: {str(e)}")
            return False

    def get_next_ticket_number(self):
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    counter = int(f.read().strip())
            else:
                counter = 0
            
            counter += 1
            with open(self.counter_file, 'w') as f:
                f.write(str(counter))
            
            return counter
        except Exception as e:
            logger.error(f"Error getting ticket number: {str(e)}")
            return None

    def save_offline_data(self, data):
        try:
            offline_data = []
            if os.path.exists(self.offline_file):
                with open(self.offline_file, 'r') as f:
                    offline_data = json.load(f)
            
            offline_data.append(data)
            with open(self.offline_file, 'w') as f:
                json.dump(offline_data, f, indent=2)
            
            logger.info(f"Data saved offline: {data}")
        except Exception as e:
            logger.error(f"Error saving offline data: {str(e)}")

    def test_connection(self):
        try:
            response = requests.get(f"{self.base_url}/test")
            if response.ok:
                return True, response.json()
            return False, None
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False, None

    def process_vehicle(self, plat):
        try:
            # Try online mode first
            response = requests.post(
                f"{self.base_url}/masuk",
                json={"plat": plat},
                timeout=5
            )
            
            if response.ok:
                result = response.json()
                if result['success']:
                    data = result['data']
                    if self.printer:
                        self.print_ticket(data)
                    return True, data
                return False, result['message']
                
        except Exception as e:
            logger.warning(f"Server error, switching to offline mode: {str(e)}")
            
            # Fallback to offline mode
            offline_data = {
                "plat": plat,
                "tiket": f"OFF{str(self.get_next_ticket_number()).zfill(4)}",
                "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_offline": True
            }
            
            self.save_offline_data(offline_data)
            if self.printer:
                self.print_ticket(offline_data)
            return True, offline_data

        return False, "Gagal memproses kendaraan"

    def sync_offline_data(self):
        if not os.path.exists(self.offline_file):
            return True
            
        try:
            with open(self.offline_file, 'r') as f:
                offline_data = json.load(f)
            
            success = True
            for data in offline_data:
                try:
                    response = requests.post(
                        f"{self.base_url}/masuk",
                        json={"plat": data['plat']}
                    )
                    if not response.ok:
                        success = False
                except:
                    success = False
            
            if success:
                os.remove(self.offline_file)
            return success
            
        except Exception as e:
            logger.error(f"Error syncing offline data: {str(e)}")
            return False

    def read_arduino_data(self):
        if not self.arduino:
            return None
            
        try:
            if self.arduino.in_waiting:
                data = self.arduino.readline().decode().strip()
                # Filter pesan tes dan hanya proses nomor plat yang valid
                if data and not data in ["READY", "PRESS"]:
                    logger.info(f"Menerima nomor plat dari Arduino: {data}")
                    return data
                elif data:
                    logger.debug(f"Menerima pesan tes dari Arduino: {data}")
        except Exception as e:
            logger.error(f"Gagal membaca data Arduino: {str(e)}")
        return None

def main():
    client = ParkingClient()
    print("""
==================================================
     SISTEM PARKIR RSI BANJARNEGARA       
==================================================
Mode: Otomatis (Push Button)
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
                print(f"\nMenerima nomor plat: {plat}")
                if len(plat) < 4 or len(plat) > 10:  # Validasi dasar nomor plat
                    print("❌ Format nomor plat tidak valid!")
                    print("\nMenunggu kendaraan berikutnya...")
                    continue
                    
                success, result = client.process_vehicle(plat)
                
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
        print("\nMenyinkronkan data offline...")
        if client.sync_offline_data():
            print("✅ Sinkronisasi berhasil")
        else:
            print("❌ Sinkronisasi gagal - data tersimpan secara offline")

if __name__ == "__main__":
    main() 