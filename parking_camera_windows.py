import cv2
import time
import os
from datetime import datetime
import logging
import shutil
import requests
from urllib.parse import quote
import configparser
import json
import numpy as np
import serial
import win32print
import psycopg2
from psycopg2 import Error

# Setup logging
logging.basicConfig(
    filename='parking.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_system')

class ParkingCamera:
    def __init__(self):
        # Load konfigurasi
        self.config = self.load_config()
        
        # Inisialisasi folder dan file
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.capture_dir = os.path.join(self.base_dir, self.config['storage']['capture_dir'])
        self.counter_file = os.path.join(self.base_dir, self.config['system']['counter_file'])
        
        # Status koneksi
        self.connection_status = {
            'is_connected': False,
            'last_connected': None,
            'reconnect_attempts': 0,
            'current_url': None,
            'camera_type': 'Dahua'
        }
        
        # Buat folder jika belum ada
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
            logger.info(f"Folder capture dibuat: {self.capture_dir}")
        
        # Setup kamera
        self.setup_camera()
        
        # Setup button
        self.setup_button()
        
        # Setup printer
        self.setup_printer()
        
        # Setup database
        self.setup_database()
        
        # Load counter
        self.load_counter()
        
        logger.info("Sistem parkir berhasil diinisialisasi")

    def setup_camera(self):
        """Setup koneksi ke kamera Dahua menggunakan RTSP"""
        try:
            camera_config = self.config['camera']
            
            # Format RTSP URL untuk Dahua
            rtsp_urls = [
                f"rtsp://{camera_config['username']}:{quote(camera_config['password'])}@{camera_config['ip']}:{camera_config['port']}/cam/realmonitor?channel=1&subtype=0",
                f"rtsp://{camera_config['username']}:{quote(camera_config['password'])}@{camera_config['ip']}:{camera_config['port']}/cam/realmonitor?channel=1&subtype=1",
                f"rtsp://{camera_config['username']}:{quote(camera_config['password'])}@{camera_config['ip']}:{camera_config['port']}/cam/realmonitor?channel=1",
                f"rtsp://{camera_config['username']}:{quote(camera_config['password'])}@{camera_config['ip']}:{camera_config['port']}/h264/ch1/main/av_stream"
            ]
            
            print("\nMencoba koneksi ke kamera Dahua menggunakan RTSP...")
            
            for url in rtsp_urls:
                try:
                    print(f"Mencoba URL: {url}")
                    self.camera = cv2.VideoCapture(url)
                    
                    if self.camera.isOpened():
                        # Coba ambil frame untuk memastikan koneksi benar-benar berhasil
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            self.connection_status.update({
                                'is_connected': True,
                                'last_connected': datetime.now(),
                                'reconnect_attempts': 0,
                                'current_url': url
                            })
                            
                            # Set resolusi kamera
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.config['image']['width']))
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.config['image']['height']))
                            
                            logger.info(f"Koneksi ke kamera Dahua berhasil dengan URL: {url}")
                            print("✅ Kamera Dahua terdeteksi dan terhubung")
                            return
                        else:
                            print("❌ Koneksi terbuka tapi tidak bisa membaca frame")
                            self.camera.release()
                    else:
                        print("❌ Gagal membuka koneksi")
                        
                except Exception as e:
                    print(f"❌ Error mencoba URL {url}: {str(e)}")
                    if hasattr(self, 'camera'):
                        self.camera.release()
                    continue
            
            raise Exception("Tidak dapat terhubung ke kamera dengan semua URL yang dicoba")
                
        except Exception as e:
            self.connection_status['is_connected'] = False
            logger.error(f"Gagal setup kamera: {str(e)}")
            raise Exception(f"Gagal setup kamera: {str(e)}")

    def capture_image(self):
        """Ambil gambar dari kamera dan simpan"""
        try:
            # Cek storage sebelum capture
            if not self.check_storage():
                raise Exception("Storage penuh!")
                
            # Increment counter
            self.counter += 1
            
            # Generate nama file
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"TKT{timestamp}_{str(self.counter).zfill(4)}.jpg"
            filepath = os.path.join(self.capture_dir, filename)
            
            # Ambil beberapa frame untuk stabilisasi
            for _ in range(3):
                ret, frame = self.camera.read()
                if not ret:
                    raise Exception("Gagal membaca frame dari kamera")
                time.sleep(0.1)
            
            # Ambil dan simpan gambar
            ret, frame = self.camera.read()
            if ret and frame is not None:
                # Simpan dengan kualitas sesuai konfigurasi
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, int(self.config['image']['quality'])])
                
                logger.info(f"Gambar berhasil disimpan: {filename}")
                print(f"\n✅ Gambar disimpan: {filename}")
                
                # Update status koneksi
                self.connection_status.update({
                    'is_connected': True,
                    'last_connected': datetime.now()
                })
                
                # Simpan metadata
                self.save_metadata(filename, frame.shape)
                
                # Simpan counter baru
                self.save_counter()
                return True, filename
            else:
                logger.error("Gagal mengambil gambar dari kamera")
                return False, None
                
        except Exception as e:
            logger.error(f"Error saat capture gambar: {str(e)}")
            return False, None

    def load_config(self):
        """Load konfigurasi dari file config.ini"""
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            # Validasi konfigurasi
            required_sections = ['camera', 'image', 'storage', 'system']
            for section in required_sections:
                if section not in config:
                    raise Exception(f"Bagian {section} tidak ditemukan dalam config.ini")
            
            return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise Exception(f"Gagal membaca konfigurasi: {str(e)}")

    def load_counter(self):
        """Load atau inisialisasi counter untuk nomor urut file"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    self.counter = int(f.read().strip())
            else:
                self.counter = 0
                self.save_counter()
        except Exception as e:
            logger.error(f"Error loading counter: {str(e)}")
            self.counter = 0

    def save_counter(self):
        """Simpan nilai counter ke file"""
        try:
            with open(self.counter_file, 'w') as f:
                f.write(str(self.counter))
        except Exception as e:
            logger.error(f"Error saving counter: {str(e)}")

    def save_metadata(self, filename, shape):
        """Simpan metadata gambar"""
        try:
            metadata = {
                'filename': filename,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'resolution': {
                    'width': shape[1],
                    'height': shape[0],
                    'channels': shape[2]
                },
                'camera_info': {
                    'ip': self.config['camera']['ip'],
                    'connection_status': {
                        'is_connected': self.connection_status['is_connected'],
                        'last_connected': self.connection_status['last_connected'].strftime('%Y-%m-%d %H:%M:%S') if self.connection_status['last_connected'] else None,
                        'reconnect_attempts': self.connection_status['reconnect_attempts'],
                        'current_url': self.connection_status['current_url']
                    }
                }
            }
            
            metadata_file = os.path.join(self.capture_dir, f"{filename}.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=4)
                
            logger.info(f"Metadata tersimpan: {metadata_file}")
            
        except Exception as e:
            logger.error(f"Gagal menyimpan metadata: {str(e)}")

    def check_storage(self):
        """Cek kapasitas storage"""
        try:
            total, used, free = shutil.disk_usage(self.base_dir)
            free_gb = free // (2**30)  # Convert to GB
            min_free_space = float(self.config['storage']['min_free_space_gb'])
            
            if free_gb < min_free_space:
                logger.warning(f"Storage tersisa kurang dari {min_free_space}GB: {free_gb}GB")
                print(f"\n⚠️ Peringatan: Storage tersisa {free_gb}GB")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking storage: {str(e)}")
            return False

    def display_status(self):
        """Tampilkan status sistem"""
        status = f"""
Status Sistem:
-------------
Kamera: {'Terhubung' if self.connection_status['is_connected'] else 'Terputus'}
IP: {self.config['camera']['ip']}
Resolusi: {self.config['image']['width']}x{self.config['image']['height']}
Total Gambar: {self.counter}
Last Connected: {self.connection_status['last_connected']}
"""
        print(status)

    def setup_button(self):
        """Setup koneksi ke pushbutton melalui serial"""
        try:
            button_config = self.config['button']
            if button_config['type'] == 'serial':
                # Coba koneksi langsung ke port yang dikonfigurasi
                try:
                    print(f"\nMencoba koneksi ke pushbutton di port {button_config['port']}...")
                    self.button = serial.Serial(
                        port=button_config['port'],
                        baudrate=int(button_config['baudrate']),
                        timeout=0.1
                    )
                    
                    # Tunggu Arduino siap
                    time.sleep(2)
                    
                    # Test koneksi dengan mengirim perintah
                    self.button.write(b'test\n')
                    time.sleep(0.1)
                    response = self.button.readline().decode().strip()
                    
                    if response:
                        logger.info(f"Koneksi serial ke pushbutton berhasil di port {button_config['port']}")
                        print(f"✅ Pushbutton terhubung di port {button_config['port']}")
                        self.button_mode = "serial"
                        return
                    else:
                        print("⚠️ Tidak ada respons dari perangkat, menggunakan mode simulasi")
                        self.button_mode = "simulation"
                        if hasattr(self, 'button'):
                            self.button.close()
                        return
                        
                except serial.SerialException as e:
                    if "PermissionError" in str(e):
                        print(f"\n⚠️ Port {button_config['port']} sedang digunakan oleh aplikasi lain")
                        print("Tutup aplikasi lain yang mungkin menggunakan port tersebut")
                    elif "FileNotFoundError" in str(e):
                        print(f"\n⚠️ Port {button_config['port']} tidak ditemukan")
                        # Coba port COM lain
                        for i in range(10):
                            test_port = f"COM{i}"
                            if test_port != button_config['port']:
                                try:
                                    print(f"Mencoba port {test_port}...")
                                    self.button = serial.Serial(test_port, int(button_config['baudrate']), timeout=0.1)
                                    time.sleep(2)
                                    self.button.write(b'test\n')
                                    time.sleep(0.1)
                                    response = self.button.readline().decode().strip()
                                    if response:
                                        print(f"✅ Pushbutton ditemukan di port {test_port}")
                                        self.button_mode = "serial"
                                        return
                                except:
                                    continue
                    else:
                        print(f"\n⚠️ Gagal koneksi ke port {button_config['port']}: {str(e)}")
                    
                    # Jika semua port gagal, gunakan mode simulasi
                    print("⚠️ Tidak dapat terhubung ke pushbutton, menggunakan mode simulasi keyboard")
                    self.button_mode = "simulation"
                    return
            else:
                # Mode selain serial, gunakan simulasi
                print("⚠️ Mode pushbutton tidak dikenali, menggunakan mode simulasi keyboard")
                self.button_mode = "simulation"
                return
                
        except Exception as e:
            logger.error(f"Setup pushbutton warning: {str(e)}")
            print("⚠️ Menggunakan mode simulasi keyboard untuk pushbutton")
            self.button_mode = "simulation"

    def check_button(self):
        """Cek status pushbutton"""
        try:
            if self.button_mode == "serial":
                if self.button.in_waiting:
                    data = self.button.readline().decode().strip()
                    try:
                        # Coba parse sebagai angka (untuk kompatibilitas dengan kode lama)
                        counter = int(data)
                        return True
                    except ValueError:
                        # Jika bukan angka, cek apakah "1" (untuk kompatibilitas dengan kode baru)
                        if data == "1":
                            return True
                return False
            elif self.button_mode == "simulation":
                # Mode simulasi - cek keyboard
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Jika user menekan spasi atau enter
                    if key in [b' ', b'\r']:
                        print("⚠️ Tombol keyboard terdeteksi sebagai pengganti pushbutton")
                        return True
                return False
        except Exception as e:
            logger.error(f"Error membaca pushbutton: {str(e)}")
            return False

    def setup_printer(self):
        """Setup printer thermal menggunakan win32print"""
        try:
            self.printer_available = False
            
            print("\nMencari printer thermal...")
            
            try:
                # Get default printer
                self.printer_name = win32print.GetDefaultPrinter()
                print(f"✅ Printer terdeteksi: {self.printer_name}")
                self.printer_available = True
                return
                
            except Exception as e:
                print(f"❌ Gagal mendapatkan default printer: {str(e)}")
                print("\nTroubleshooting printer:")
                print("1. Pastikan printer thermal terhubung ke USB")
                print("2. Pastikan driver printer terinstall")
                print("3. Pastikan printer diset sebagai default printer")
                print("4. Pastikan printer menyala dan kertas tersedia")
            
        except Exception as e:
            logger.error(f"Setup printer error: {str(e)}")
            print(f"\n❌ Setup printer error: {str(e)}")
            self.printer_available = False

    def print_ticket(self, filename):
        """Cetak tiket parkir menggunakan win32print"""
        if not self.printer_available:
            logger.info("Melewati pencetakan tiket - printer tidak tersedia")
            return

        try:
            # Buka koneksi ke printer
            printer_handle = win32print.OpenPrinter(self.printer_name)
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Tiket Parkir", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)

            # Format tiket dengan ESC/POS commands
            timestamp = datetime.now()
            ticket_number = filename.replace('.jpg','')
            
            # Jika tiket panjang, gunakan versi pendek untuk barcode
            barcode_ticket = ticket_number
            if len(ticket_number) > 15 and ticket_number.startswith("TKT"):
                barcode_ticket = ticket_number[-10:]
            
            # Kombinasikan semua perintah dalam satu bytearray
            commands = bytearray()
            
            # Initialize printer
            commands.extend(b"\x1B\x40")  # ESC @ - Initialize printer
            
            # Center alignment
            commands.extend(b"\x1B\x61\x01")  # ESC a 1 - Center alignment
            
            # Header text
            commands.extend(b"\x1B\x21\x30")  # Double width/height
            commands.extend("RSI BANJARNEGARA\n".encode())
            commands.extend(b"\x1B\x21\x00")  # Normal font
            commands.extend("TIKET PARKIR\n".encode())
            commands.extend("--------------------------------\n".encode())
            
            # Left alignment untuk detail tiket
            commands.extend(b"\x1B\x61\x00")  # ESC a 0 - Left alignment
            
            # Details
            commands.extend(f"Tanggal : {timestamp.strftime('%d-%m-%Y')}\n".encode())
            commands.extend(f"Jam     : {timestamp.strftime('%H:%M:%S')}\n".encode())
            commands.extend(f"No.     : {ticket_number}\n".encode())
            commands.extend("--------------------------------\n\n".encode())
            
            # Center untuk barcode
            commands.extend(b"\x1B\x61\x01")  # Center alignment
            
            # Barcode info
            commands.extend(b"\x1D\x68\x50")  # GS h 80 - Barcode height 80 dots
            commands.extend(b"\x1D\x77\x02")  # GS w 2 - Barcode width multiplier (2)
            commands.extend(b"\x1D\x48\x02")  # GS H 2 - HRI below barcode
            
            # Print barcode type CODE39
            commands.extend(b"\x1D\x6B\x04")  # GS k 4 - CODE39 barcode
            commands.append(len(barcode_ticket))  # Length byte
            commands.extend(barcode_ticket.encode('ascii'))  # Barcode data
            
            # Footer
            commands.extend(b"\n\n")
            commands.extend(b"\x1B\x61\x01")  # Center alignment
            commands.extend("Terima Kasih\n".encode())
            commands.extend("Simpan Tiket Anda\n\n\n".encode())
            
            # Cut paper
            commands.extend(b"\x1D\x56\x42")  # GS V B - Cut paper
            
            # Kirim semua data ke printer
            win32print.WritePrinter(printer_handle, commands)

            # Selesaikan job printing
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            
            logger.info(f"Tiket berhasil dicetak: {filename}")
            print("✅ Tiket berhasil dicetak")
            
        except Exception as e:
            logger.error(f"Gagal mencetak tiket: {str(e)}")
            print(f"❌ Gagal mencetak tiket: {str(e)}")

    def setup_database(self):
        """Setup koneksi ke database PostgreSQL"""
        try:
            db_config = self.config['database']
            self.db_conn = psycopg2.connect(
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host']
            )
            logger.info("Koneksi ke database berhasil")
            print("✅ Database terkoneksi")
        except Exception as e:
            logger.error(f"Gagal koneksi ke database: {str(e)}")
            raise Exception(f"Gagal koneksi ke database: {str(e)}")

    def save_to_database(self, ticket_number, image_path):
        """Simpan data tiket ke database"""
        try:
            cur = self.db_conn.cursor()
            
            # Query untuk insert data
            sql = """
            INSERT INTO public."CaptureTickets" 
            ("TicketNumber", "ImagePath") 
            VALUES (%s, %s)
            """
            
            # Eksekusi query
            cur.execute(sql, (ticket_number, image_path))
            self.db_conn.commit()
            
            logger.info(f"Data tiket {ticket_number} berhasil disimpan ke database")
            print("✅ Data tersimpan di database")
            
        except Exception as e:
            logger.error(f"Gagal menyimpan ke database: {str(e)}")
            print(f"❌ Gagal menyimpan ke database: {str(e)}")
            self.db_conn.rollback()
        finally:
            cur.close()

    def process_button_press(self):
        """Proses ketika tombol ditekan - ambil gambar, cetak tiket, dan simpan ke database"""
        print("\nMemproses... Mohon tunggu...")
        
        # Ambil gambar
        success, filename = self.capture_image()
        
        if success:
            # Simpan ke database
            ticket_number = filename.replace('.jpg', '')
            image_path = os.path.join(self.config['storage']['capture_dir'], filename)
            self.save_to_database(ticket_number, image_path)
            
            # Cetak tiket jika printer tersedia
            if self.printer_available:
                self.print_ticket(filename)
            
            print("Status: Menunggu input berikutnya...")
        else:
            print("❌ Gagal mengambil gambar!")

    def cleanup(self):
        """Bersihkan resources"""
        try:
            if hasattr(self, 'camera'):
                self.camera.release()
            if hasattr(self, 'button'):
                self.button.close()
            if hasattr(self, 'printer'):
                self.printer.close()
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
            logger.info("Cleanup berhasil")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def run(self):
        """Main loop program"""
        print("""
================================
    SISTEM PARKIR RSI BNA    
================================
Mode: Pushbutton
Status: Menunggu input dari pushbutton...
        """)
        
        try:
            while True:
                if self.check_button():  # Pushbutton ditekan
                    self.process_button_press()
                    # Delay untuk debounce
                    time.sleep(0.5)
                
                # Delay kecil untuk mengurangi CPU usage
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    try:
        parking = ParkingCamera()
        parking.run()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 