import cv2
import time
import os
from datetime import datetime, timedelta
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
import random
import msvcrt

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
        self.load_config()
        
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
        
        # Tambahkan state untuk debounce
        self.last_button_press = 0
        self.debounce_delay = 1.0  # Ubah menjadi 1 detik
        self.button_mode = "keyboard"  # Default to keyboard mode
        
        # Add additional timing parameters
        self.camera_initialization_delay = 2.0
        self.button_check_interval = 0.05
        
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
        
        # Initialize counter and capture time
        self.load_counter()
        self.last_capture_time = 0
        
        # Initialize image comparison parameters
        self.last_image = None
        self.min_image_diff = 0.15
        self.check_similar_images = False
        
        logger.info("Sistem parkir berhasil diinisialisasi")

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
            
            self.config = config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise Exception(f"Gagal membaca konfigurasi: {str(e)}")

    def setup_camera(self):
        """Setup koneksi ke kamera"""
        try:
            print("\nMencoba koneksi ke kamera...")
            
            # Coba koneksi ke kamera IP terlebih dahulu
            if self.config['camera']['type'] == 'ip':
                try:
                    ip = self.config['camera']['ip']
                    username = self.config['camera']['username']
                    password = self.config['camera']['password']
                    main_stream = self.config['camera']['main_stream']
                    
                    # Format URL RTSP
                    rtsp_url = main_stream.format(username=username, password=password, ip=ip)
                    print(f"Mencoba koneksi ke kamera IP {ip}...")
                    
                    self.camera = cv2.VideoCapture(rtsp_url)
                    if self.camera.isOpened():
                        # Set resolusi kamera
                        width = int(self.config['image']['width'])
                        height = int(self.config['image']['height'])
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        
                        # Test ambil gambar
                        ret, frame = self.camera.read()
                        if ret:
                            print(f"✅ Kamera IP terdeteksi")
                            print(f"✅ Resolusi: {width}x{height}")
                            self.connection_status['is_connected'] = True
                            self.connection_status['last_connected'] = datetime.now()
                            self.connection_status['camera_type'] = 'IP Dahua'
                            return
                        else:
                            self.camera.release()
                            raise Exception("Gagal membaca frame dari kamera IP")
                    else:
                        raise Exception("Gagal membuka koneksi RTSP")
                except Exception as e:
                    logger.error(f"Gagal koneksi ke kamera IP: {str(e)}")
                    print(f"❌ Error koneksi kamera IP: {str(e)}")
            
            # Jika kamera IP gagal atau tidak dikonfigurasi, coba kamera lokal
            print("\nMencoba kamera lokal...")
            for i in range(4):
                try:
                    self.camera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if self.camera.isOpened():
                        # Set resolusi kamera
                        width = int(self.config['image']['width'])
                        height = int(self.config['image']['height'])
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        
                        # Test ambil gambar
                        ret, frame = self.camera.read()
                        if ret:
                            print(f"✅ Kamera lokal terdeteksi pada device {i}")
                            print(f"✅ Resolusi: {width}x{height}")
                            self.connection_status['is_connected'] = True
                            self.connection_status['last_connected'] = datetime.now()
                            self.connection_status['camera_type'] = 'Local'
                            return
                        else:
                            self.camera.release()
                except Exception as e:
                    logger.error(f"Gagal koneksi ke device {i}: {str(e)}")
                    continue
            
            # Jika tidak ada kamera yang terdeteksi, gunakan mode dummy
            print("\n⚠️ Tidak ada kamera yang terdeteksi")
            print("✅ Beralih ke mode dummy")
            self.camera = None
            self.connection_status['is_connected'] = False
            self.connection_status['camera_type'] = 'Dummy'
            
        except Exception as e:
            logger.error(f"Error setting up camera: {str(e)}")
            raise Exception(f"Gagal setup kamera: {str(e)}")

    def capture_image(self):
        """Ambil gambar dari kamera atau buat dummy image jika kamera tidak tersedia"""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            counter = self.load_counter()
            filename = f"{timestamp}_{counter:04d}.jpg"
            filepath = os.path.join(self.capture_dir, filename)
            
            # Coba ambil gambar dari kamera jika tersedia
            if self.camera:
                print("\n📸 Mengambil gambar dari kamera...")
                
                # Stabilize camera - read beberapa frame
                for _ in range(5):
                    ret = self.camera.read()[0]
                
                # Capture frame
                ret, frame = self.camera.read()
                
                if ret:
                    # Resize untuk mengurangi ukuran file
                    height = int(self.config['image']['height'])
                    width = int(self.config['image']['width'])
                    frame = cv2.resize(frame, (width, height))
                    
                    # Simpan dengan kompresi
                    cv2.imwrite(filepath, frame, [
                        cv2.IMWRITE_JPEG_QUALITY, 90,
                        cv2.IMWRITE_JPEG_OPTIMIZE, 1
                    ])
                    
                    # Hitung ukuran file dalam KB
                    file_size = os.path.getsize(filepath) / 1024
                    print(f"✅ File disimpan: {filename} ({file_size:.1f} KB)")
                    
                    # Simpan metadata
                    metadata = {
                        "timestamp": timestamp,
                        "counter": counter,
                        "mode": "camera",
                        "resolution": {
                            "width": width,
                            "height": height
                        },
                        "file_size": f"{file_size:.1f} KB"
                    }
                    
                    with open(filepath + ".json", 'w') as f:
                        json.dump(metadata, f, indent=4)
                    
                    self.last_capture_time = time.time()
                    return True, filename
                else:
                    print("❌ Gagal mengambil gambar dari kamera")
                    logger.error("Camera capture returned False")
            
            # Jika kamera tidak tersedia atau capture gagal, buat dummy image
            print("📸 Menggunakan mode dummy (tanpa kamera)")
            
            # Buat dummy image dengan informasi
            height = int(self.config['image']['height'])
            width = int(self.config['image']['width'])
            dummy_image = np.zeros((height, width, 3), dtype=np.uint8)
            dummy_image.fill(255)  # Background putih
            
            # Tambahkan text ke gambar
            cv2.putText(dummy_image, "DUMMY IMAGE - NO CAMERA", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(dummy_image, f"Ticket: {filename}", (50, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(dummy_image, timestamp, (50, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            # Simpan dummy image
            cv2.imwrite(filepath, dummy_image, [
                cv2.IMWRITE_JPEG_QUALITY, 90,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1
            ])
            
            print(f"✅ File dummy disimpan: {filename}")
            
            # Simpan metadata
            metadata = {
                "timestamp": timestamp,
                "counter": counter,
                "mode": "dummy",
                "resolution": {
                    "width": width,
                    "height": height
                }
            }
            
            with open(filepath + ".json", 'w') as f:
                json.dump(metadata, f, indent=4)
            
            self.last_capture_time = time.time()
            return True, filename

        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
            return False, None

    def setup_button(self):
        """Setup push button connection"""
        logging.info("\nMencoba koneksi ke pushbutton di port COM7...")
        try:
            self.button = serial.Serial('COM7', 9600, timeout=1)
            logging.info("✅ Push button terkoneksi")
        except Exception as e:
            logging.warning(f"\n⚠️ Error koneksi push button: {str(e)}")
            logging.info("ℹ️ Menggunakan keyboard sebagai input alternatif (tekan '1')")
            self.button = None

    def setup_printer(self):
        """Setup printer thermal menggunakan win32print"""
        try:
            self.printer_available = False
            
            print("\nMencari printer thermal...")
            
            try:
                # Get default printer
                self.printer_name = win32print.GetDefaultPrinter()
                if not self.printer_name:
                    print("❌ Tidak ada default printer yang diset")
                    return
                    
                # Test printer
                test_handle = win32print.OpenPrinter(self.printer_name)
                win32print.ClosePrinter(test_handle)
                
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
                print("5. Coba restart printer")
            
        except Exception as e:
            logger.error(f"Setup printer error: {str(e)}")
            print(f"\n❌ Setup printer error: {str(e)}")
            self.printer_available = False

    def setup_database(self):
        """Setup koneksi ke database PostgreSQL"""
        self.db_conn = None
        try:
            # Periksa apakah bagian database ada di config
            if 'database' not in self.config:
                logger.warning("Bagian database tidak ditemukan di config.ini - mode tanpa database aktif")
                print("ℹ️ Mode tanpa database aktif")
                return

            db_config = self.config['database']
            self.db_conn = psycopg2.connect(
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host']
            )
            
            # Buat tabel jika belum ada
            self.create_tables()
            
            logger.info("Koneksi ke database berhasil")
            print("✅ Database terkoneksi")
        except Exception as e:
            logger.warning(f"Gagal koneksi ke database: {str(e)}")
            print(f"ℹ️ Mode tanpa database aktif - {str(e)}")
            self.db_conn = None

    def create_tables(self):
        """Buat tabel yang diperlukan jika belum ada"""
        if not self.db_conn:
            return
            
        try:
            cursor = self.db_conn.cursor()
            
            # Buat tabel tickets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    ticket_id VARCHAR(50) UNIQUE NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    image_path VARCHAR(255),
                    status VARCHAR(20) NOT NULL,
                    vehicle_type VARCHAR(20),
                    license_plate VARCHAR(20),
                    fee INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            self.db_conn.commit()
            cursor.close()
            logger.info("Tabel tickets berhasil dibuat/diperiksa")
            
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            if self.db_conn:
                self.db_conn.rollback()

    def print_ticket(self, ticket_id):
        """Cetak tiket parkir dengan barcode"""
        if not self.printer_available:
            print("❌ Printer tidak tersedia")
            return False
            
        try:
            # Set harga tetap
            price = 2500  # Harga default Rp 2.500
            
            print(f"\nMencoba mencetak ke printer: {self.printer_name}")
            printer_handle = win32print.OpenPrinter(self.printer_name)
            print("✅ Printer berhasil dibuka")
            
            # Initialize printer commands
            commands = bytearray()
            
            # Reset printer
            commands.extend(b"\x1B\x40")  # ESC @ - Initialize printer
            
            # Select character code table (PC437 USA)
            commands.extend(b"\x1B\x74\x00")  # ESC t 0
            
            # Set line spacing to 30 dots
            commands.extend(b"\x1B\x33\x1E")  # ESC 3 30
            
            # Center alignment
            commands.extend(b"\x1B\x61\x01")  # ESC a 1
            
            # Double width & height
            commands.extend(b"\x1D\x21\x11")  # GS ! 17
            
            # Format tiket with simpler text
            ticket_text = (
                "\x1B\x21\x30"  # Select double width/height
                "TIKET PARKIR\n\n"
                "\x1B\x21\x00"  # Reset text size
                f"No: {ticket_id}\n"
                f"Tgl: {datetime.now().strftime('%d/%m/%Y')}\n"
                f"Jam: {datetime.now().strftime('%H:%M:%S')}\n"
                f"Tarif: Rp {price:,}\n\n"
            ).encode('ascii', errors='replace')
            
            # Prepare barcode data (clean up non-supported characters)
            barcode_data = ''.join(c for c in ticket_id if c.isalnum())
            
            # Set up barcode
            barcode_commands = bytearray()
            barcode_commands.extend(b"\x1D\x68\x50")  # GS h 80 - Set barcode height to 80 dots
            barcode_commands.extend(b"\x1D\x77\x02")  # GS w 2 - Set barcode width (2=medium)
            barcode_commands.extend(b"\x1D\x48\x02")  # GS H 2 - Print HRI characters below barcode
            barcode_commands.extend(b"\x1D\x66\x00")  # GS f 0 - Select font for HRI characters
            
            # Print barcode (CODE128)
            barcode_commands.extend(b"\x1D\x6B\x49")  # GS k I - Select CODE128
            barcode_commands.extend(bytes([len(barcode_data)]))  # Length of data
            barcode_commands.extend(barcode_data.encode('ascii'))  # Barcode data
            
            print("Memulai pencetakan...")
            
            # Start print job
            job = win32print.StartDocPrinter(printer_handle, 1, ("Tiket Parkir", None, "RAW"))
            if job == 0:
                raise Exception("StartDocPrinter failed")
            print("✅ Print job dimulai")
            
            win32print.StartPagePrinter(printer_handle)
            print("✅ Halaman dimulai")
            
            # Send initialization and commands
            bytes_written = win32print.WritePrinter(printer_handle, commands)
            print(f"✅ Command dikirim: {bytes_written} bytes")
            
            # Send ticket text
            bytes_written = win32print.WritePrinter(printer_handle, ticket_text)
            print(f"✅ Teks tiket dikirim: {bytes_written} bytes")
            
            # Send barcode
            bytes_written = win32print.WritePrinter(printer_handle, barcode_commands)
            print(f"✅ Barcode dikirim: {bytes_written} bytes")
            
            # Footer text
            footer_text = (
                "\n\nSimpan tiket ini\n"
                "Kehilangan tiket akan\n"
                "dikenakan denda\n"
                "================\n\n"
            ).encode('ascii')
            
            bytes_written = win32print.WritePrinter(printer_handle, footer_text)
            print(f"✅ Footer dikirim: {bytes_written} bytes")
            
            # Feed and cut
            cut_commands = (
                b"\x1B\x64\x05"  # Feed 5 lines (ESC d 5)
                b"\x1D\x56\x41\x03"  # Cut paper with feed (GS V A 3)
            )
            bytes_written = win32print.WritePrinter(printer_handle, cut_commands)
            print(f"✅ Perintah potong kertas dikirim: {bytes_written} bytes")
            
            # End print job properly
            win32print.EndPagePrinter(printer_handle)
            print("✅ Halaman selesai")
            
            win32print.EndDocPrinter(printer_handle)
            print("✅ Print job selesai")
            
            win32print.ClosePrinter(printer_handle)
            print("✅ Printer ditutup")
            
            logger.info(f"Tiket {ticket_id} berhasil dicetak")
            return True
            
        except Exception as e:
            print(f"❌ Gagal mencetak tiket: {str(e)}")
            logger.error(f"Print error: {str(e)}")
            if 'printer_handle' in locals():
                try:
                    win32print.ClosePrinter(printer_handle)
                except:
                    pass
            return False

    def run(self):
        """Main loop program"""
        print("""
================================
    SISTEM PARKIR RSI BNA    
================================
""")
        if self.connection_status['camera_type'] == 'IP Dahua':
            print("Mode: Kamera IP Dahua")
            print(f"IP: {self.config['camera']['ip']}")
            print(f"Resolution: 1920x1080 (Main) / 704x576 (Sub)")
        else:
            print("Mode: Pushbutton (Tanpa Kamera)")
            
        print("Status: Menunggu input dari pushbutton...")
        print()
        
        try:
            while True:
                if self.check_button():  # Pushbutton ditekan
                    self.process_button_press()
                
                # Delay kecil untuk mengurangi CPU usage
                time.sleep(self.button_check_interval)
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
        finally:
            self.cleanup()

    def check_button(self):
        """Cek status pushbutton dan keyboard dengan debounce dan toleransi"""
        try:
            current_time = time.time()
            button_pressed = False
            
            # Cek keyboard input
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'1':  # Jika tombol '1' ditekan
                    print("\n⌨️ Tombol '1' terdeteksi")
                    if current_time - self.last_button_press >= self.debounce_delay:
                        self.last_button_press = current_time
                        button_pressed = True
                        logger.info("Tombol keyboard '1' terdeteksi")
                        return True
                    else:
                        remaining = self.debounce_delay - (current_time - self.last_button_press)
                        print(f"\n⏳ Mohon tunggu {remaining:.1f} detik lagi...")
                        return False
            
            # Cek pushbutton fisik jika tersedia
            if hasattr(self, 'button') and self.button is not None and self.button.in_waiting:
                data = self.button.read_all().decode().strip()
                if data and current_time - self.last_button_press >= self.debounce_delay:
                    print("\n🔘 Push button fisik terdeteksi")
                    self.last_button_press = current_time
                    button_pressed = True
                    logger.info("Push button terdeteksi")
                    return True
                    
            return button_pressed
            
        except Exception as e:
            logger.error(f"Error membaca input: {str(e)}")
            return False

    def process_button_press(self):
        """Proses ketika tombol ditekan - ambil gambar, cetak tiket, dan simpan ke database"""
        try:
            # Tambah delay kecil untuk stabilisasi
            time.sleep(0.1)
            
            print("\n\nMemproses... Mohon tunggu...\n")
            print("1. Mengambil gambar...")
            logger.info("Mulai proses capture gambar")
            
            # Cek apakah ada capture yang masih diproses
            current_time = time.time()
            if hasattr(self, 'last_capture_time') and self.last_capture_time:
                time_since_last = current_time - self.last_capture_time
                if time_since_last < 0.5:  # Minimal jeda 0.5 detik antara capture
                    print("⚠️ Terlalu cepat! Mohon tunggu...\n")
                    logger.warning(f"Capture terlalu cepat, interval: {time_since_last:.1f}s")
                    return
            
            # Ambil gambar
            success, filename = self.capture_image()
            
            if success:
                print("\n2. Menyimpan ke database...")
                # Simpan ke database
                ticket_number = filename.replace('.jpg', '')
                image_path = os.path.join(self.config['storage']['capture_dir'], filename)
                self.save_to_database(ticket_number, image_path)
                
                # Update timestamp capture terakhir
                self.last_capture_time = current_time
                
                # Cetak tiket jika printer tersedia
                print(f"\n3. Status printer: {'Tersedia' if self.printer_available else 'Tidak tersedia'}")
                if self.printer_available:
                    print("\n4. Mencoba cetak tiket...")
                    self.print_ticket(ticket_number)
                else:
                    print("\n❌ Printer tidak tersedia, tiket tidak bisa dicetak")
                
                # Tambah delay setelah proses selesai
                time.sleep(0.1)
                print("\n\nStatus: Menunggu input berikutnya...\n")
                logger.info("Proses capture selesai dengan sukses")
            else:
                print("\n❌ Gagal mengambil gambar!\n")
                logger.error("Gagal melakukan capture gambar")
                
        except Exception as e:
            logger.error(f"Error dalam process_button_press: {str(e)}")
            print(f"\n❌ Error saat memproses: {str(e)}\n")

    def cleanup(self):
        """Bersihkan resources"""
        try:
            if hasattr(self, 'camera') and self.camera is not None:
                self.camera.release()
            if hasattr(self, 'button') and self.button_mode == "serial":
                self.button.close()
            if hasattr(self, 'db_conn') and self.db_conn is not None:
                self.db_conn.close()
            logger.info("Cleanup berhasil")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def load_counter(self):
        """Load atau inisialisasi counter untuk nomor urut file"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    self.counter = int(f.read().strip())
            else:
                self.counter = 0
                with open(self.counter_file, 'w') as f:
                    f.write(str(self.counter))
            logger.info(f"Counter loaded: {self.counter}")
            return self.counter
        except Exception as e:
            logger.error(f"Error loading counter: {str(e)}")
            self.counter = 0
            return self.counter

    def save_counter(self):
        """Simpan nilai counter ke file"""
        try:
            with open(self.counter_file, 'w') as f:
                f.write(str(self.counter))
            logger.info(f"Counter saved: {self.counter}")
        except Exception as e:
            logger.error(f"Error saving counter: {str(e)}")

    def save_to_database(self, ticket_number, image_path):
        """Simpan data tiket ke database"""
        if not self.db_conn:
            print("ℹ️ Mode tanpa database aktif")
            return
            
        try:
            cursor = self.db_conn.cursor()
            
            # Buat query insert
            query = """
                INSERT INTO tickets 
                (ticket_id, entry_time, image_path, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            
            # Data yang akan disimpan
            data = (
                ticket_number,
                datetime.now(),
                image_path,
                'ACTIVE'
            )
            
            # Eksekusi query
            cursor.execute(query, data)
            self.db_conn.commit()
            cursor.close()
            
            print("✅ Data tiket berhasil disimpan ke database")
            logger.info(f"Tiket {ticket_number} berhasil disimpan ke database")
            
        except Exception as e:
            print(f"⚠️ Gagal menyimpan ke database: {str(e)}")
            logger.error(f"Database error: {str(e)}")
            if self.db_conn:
                self.db_conn.rollback()

if __name__ == "__main__":
    try:
        parking = ParkingCamera()
        parking.run()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 