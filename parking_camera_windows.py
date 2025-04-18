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
import barcode
from barcode.writer import ImageWriter

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
        """Setup koneksi ke pushbutton melalui serial Arduino dengan fitur auto-reconnect"""
        print("\nMencoba koneksi ke Arduino pushbutton...")
        logging.info("Mencoba koneksi ke pushbutton...")
        
        # Inisialisasi variabel reconnect
        self.last_reconnect_attempt = 0
        self.reconnect_delay = 30  # 30 detik delay antar percobaan reconnect
        self.max_reconnect_attempts = 5  # Maksimal 5 kali percobaan reconnect sebelum fallback ke keyboard
        self.reconnect_attempts = 0
        self.last_port_found = None
        
        try:
            # Coba ambil port terakhir yang berhasil dari file
            if os.path.exists("arduino_port.txt"):
                with open("arduino_port.txt", "r") as f:
                    saved_port = f.read().strip()
                    if saved_port:
                        self.last_port_found = saved_port
                        print(f"Port Arduino terakhir yang berhasil digunakan: {saved_port}")
                        try:
                            # Coba hubungkan ke port yang tersimpan terlebih dahulu
                            self.button = serial.Serial(
                                port=saved_port,
                                baudrate=9600,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=1,
                                write_timeout=1  # Tambahkan write timeout
                            )
                            time.sleep(2)  # Berikan waktu Arduino untuk reset
                            
                            # Bersihkan buffer
                            try:
                                if self.button.in_waiting:
                                    self.button.read_all()
                            except Exception as e:
                                logger.warning(f"Error membersihkan buffer: {str(e)}")
                                
                            # Kirim perintah test
                            try:
                                self.button.write(b'test\n')
                                time.sleep(1)  # Tunggu respons lebih lama
                                
                                # Baca respons
                                if self.button.in_waiting:
                                    response = self.button.read_all().decode(errors='ignore').strip()
                                    print(f"Respons dari {saved_port}: {response}")
                                    if any(signal in response.upper() for signal in ['READY', 'OK', 'ARDUINO']):
                                        print(f"✅ Arduino terdeteksi di port {saved_port}")
                                        logging.info(f"Push button Arduino terkoneksi di port {saved_port}")
                                        self.button_mode = "arduino"
                                        self.current_port = saved_port
                                        
                                        # Simpan port yang berhasil
                                        with open("arduino_port.txt", "w") as f:
                                            f.write(saved_port)
                                            
                                        return
                            except Exception as e:
                                logger.warning(f"Error saat komunikasi dengan port tersimpan: {str(e)}")
                            
                            # Jika tidak berhasil, tutup koneksi
                            if hasattr(self, 'button') and self.button and self.button.is_open:
                                self.button.close()
                        except Exception as e:
                            logger.warning(f"Error mencoba port tersimpan {saved_port}: {str(e)}")
                            if hasattr(self, 'button') and self.button and self.button.is_open:
                                self.button.close()
            
            # Jika koneksi ke port tersimpan gagal atau tidak ada port tersimpan,
            # lakukan pencarian di semua port
            for port_num in range(1, 11):
                port = f'COM{port_num}'
                try:
                    print(f"Mencoba port {port}...")
                    self.button = serial.Serial(
                        port=port,
                        baudrate=9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1,
                        write_timeout=1  # Tambahkan write timeout
                    )
                    time.sleep(2)  # Berikan waktu Arduino untuk reset
                    
                    # Bersihkan buffer
                    try:
                        if self.button.in_waiting:
                            self.button.read_all()
                    except Exception as e:
                        logger.warning(f"Error membersihkan buffer port {port}: {str(e)}")
                        continue
                        
                    # Kirim perintah test
                    try:
                        self.button.write(b'test\n')
                        time.sleep(1)  # Tunggu respons lebih lama
                        
                        # Baca respons
                        if self.button.in_waiting:
                            response = self.button.read_all().decode(errors='ignore').strip()
                            print(f"Respons dari {port}: {response}")
                            if any(signal in response.upper() for signal in ['READY', 'OK', 'ARDUINO']):
                                print(f"✅ Arduino terdeteksi di port {port}")
                                logging.info(f"Push button Arduino terkoneksi di port {port}")
                                self.button_mode = "arduino"
                                self.current_port = port
                                self.last_port_found = port
                                
                                # Simpan port yang berhasil
                                with open("arduino_port.txt", "w") as f:
                                    f.write(port)
                                    
                                return
                    except Exception as e:
                        logger.warning(f"Error saat komunikasi dengan port {port}: {str(e)}")
                    
                    # Jika tidak ada respons yang valid, tutup port
                    if hasattr(self, 'button') and self.button and self.button.is_open:
                        self.button.close()
                    
                except serial.SerialException as se:
                    print(f"Port {port} tidak tersedia: {str(se)}")
                    continue
                except Exception as e:
                    print(f"Error pada port {port}: {str(e)}")
                    if hasattr(self, 'button') and self.button and self.button.is_open:
                        self.button.close()
                    continue
                    
            # Jika tidak ada Arduino yang terdeteksi
            print("\n⚠️ Tidak ada Arduino yang terdeteksi")
            self.button_mode = "keyboard"
            
        except Exception as e:
            print(f"⚠️ Error koneksi push button: {str(e)}")
            logging.warning(f"Error koneksi push button: {str(e)}")
            
        # Mode fallback ke keyboard
        logging.info("Menggunakan keyboard sebagai input alternatif")
        print("\n⚠️ Pushbutton Arduino tidak terdeteksi")
        print("ℹ️ Menggunakan mode keyboard:")
        print("  - Tombol '1' pada keyboard")
        print("  - Tombol SPASI pada keyboard")
        print("  - Tombol ENTER pada keyboard")
        self.button = None
        self.button_mode = "keyboard"

    def reconnect_arduino(self):
        """Mencoba menghubungkan kembali ke Arduino jika koneksi terputus"""
        current_time = time.time()
        
        # Cek jika sudah waktunya untuk mencoba reconnect
        if (current_time - self.last_reconnect_attempt) < self.reconnect_delay:
            return False
            
        # Catat waktu percobaan reconnect
        self.last_reconnect_attempt = current_time
        self.reconnect_attempts += 1
        
        # Jika sudah melebihi batas percobaan, tetap gunakan keyboard
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.warning(f"Melebihi batas {self.max_reconnect_attempts} percobaan reconnect. Tetap menggunakan keyboard.")
            return False
            
        logger.info(f"Mencoba reconnect Arduino (Percobaan ke-{self.reconnect_attempts})...")
        print(f"\n🔄 Mencoba menghubungkan kembali ke Arduino (Percobaan ke-{self.reconnect_attempts})...")
        
        # Jika ada port terakhir yang berhasil, coba itu terlebih dahulu
        if self.last_port_found:
            try:
                # Pastikan tidak ada koneksi yang masih terbuka
                if hasattr(self, 'button') and self.button and self.button.is_open:
                    self.button.close()
                    
                # Buka koneksi baru
                self.button = serial.Serial(
                    port=self.last_port_found,
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1
                )
                time.sleep(2)  # Berikan waktu Arduino untuk reset
                
                # Test koneksi
                if self.button.is_open:
                    try:
                        self.button.write(b'test\n')
                        time.sleep(1)
                        
                        if self.button.in_waiting:
                            response = self.button.read_all().decode(errors='ignore').strip()
                            if any(signal in response.upper() for signal in ['READY', 'OK', 'ARDUINO']):
                                print(f"✅ Reconnect berhasil di port {self.last_port_found}")
                                logger.info(f"Reconnect Arduino berhasil di port {self.last_port_found}")
                                self.button_mode = "arduino"
                                self.current_port = self.last_port_found
                                self.reconnect_attempts = 0  # Reset counter percobaan
                                return True
                    except Exception as e:
                        logger.warning(f"Error saat test koneksi reconnect: {str(e)}")
                        
                # Jika gagal, tutup koneksi
                if hasattr(self, 'button') and self.button and self.button.is_open:
                    self.button.close()
                    
            except Exception as e:
                logger.warning(f"Reconnect gagal: {str(e)}")
                if hasattr(self, 'button') and self.button and self.button.is_open:
                    self.button.close()
                    
        # Jika reconnect gagal, tetap gunakan keyboard
        return False

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
        """Setup koneksi ke database PostgreSQL dengan fitur auto-reconnect"""
        self.db_conn = None
        self.db_last_connect_attempt = 0
        self.db_reconnect_delay = 60  # 1 menit antar percobaan
        self.db_max_retry = 3  # Maksimal 3 kali percobaan
        self.db_retry_count = 0
        self.db_config = None
        
        try:
            # Periksa apakah bagian database ada di config
            if 'database' not in self.config:
                logger.warning("Bagian database tidak ditemukan di config.ini - mode tanpa database aktif")
                print("ℹ️ Mode tanpa database aktif")
                return

            self.db_config = self.config['database']
            self.connect_to_database()
            
        except Exception as e:
            logger.warning(f"Gagal koneksi ke database: {str(e)}")
            print(f"ℹ️ Mode tanpa database aktif - {str(e)}")
            self.db_conn = None
    
    def connect_to_database(self):
        """Buat koneksi ke database dan tangani error dengan lebih baik"""
        if not self.db_config:
            return False
            
        try:
            # Catat waktu percobaan koneksi
            self.db_last_connect_attempt = time.time()
            
            # Buat koneksi dengan timeout
            self.db_conn = psycopg2.connect(
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                host=self.db_config['host'],
                connect_timeout=10  # 10 detik timeout
            )
            
            # Set koneksi untuk auto-commit (opsional)
            self.db_conn.autocommit = False
            
            # Tes koneksi dengan SELECT sederhana
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0] == 1:
                # Reset counter retry
                self.db_retry_count = 0
                
                # Buat tabel jika belum ada
                self.create_tables()
                
                logger.info("Koneksi ke database berhasil")
                print("✅ Database terkoneksi")
                return True
            else:
                raise Exception("Koneksi berhasil tapi test query gagal")
                
        except Exception as e:
            logger.warning(f"Gagal koneksi ke database: {str(e)}")
            print(f"⚠️ Gagal koneksi ke database: {str(e)}")
            self.db_conn = None
            return False
            
    def reconnect_database(self):
        """Coba menghubungkan kembali ke database jika koneksi terputus"""
        # Jika tidak ada konfigurasi database, jangan coba reconnect
        if not self.db_config:
            return False
            
        # Cek jika sudah waktunya untuk mencoba reconnect
        current_time = time.time()
        if (current_time - self.db_last_connect_attempt) < self.db_reconnect_delay:
            return False
            
        # Jika sudah melebihi jumlah maksimum percobaan
        if self.db_retry_count >= self.db_max_retry:
            logger.warning(f"Melebihi batas {self.db_max_retry} percobaan reconnect database")
            return False
            
        # Increment counter dan coba reconnect
        self.db_retry_count += 1
        logger.info(f"Mencoba reconnect database (Percobaan ke-{self.db_retry_count})...")
        print(f"\n🔄 Mencoba menghubungkan kembali ke database (Percobaan ke-{self.db_retry_count})...")
        
        # Tutup koneksi lama jika masih ada
        if self.db_conn:
            try:
                self.db_conn.close()
            except:
                pass
            self.db_conn = None
            
        # Coba buat koneksi baru
        return self.connect_to_database()
        
    def is_db_connected(self):
        """Cek apakah koneksi database masih aktif"""
        if not self.db_conn:
            return False
            
        try:
            # Test koneksi dengan query sederhana
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            return result and result[0] == 1
        except Exception as e:
            logger.warning(f"Koneksi database terputus: {str(e)}")
            return False

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

    def print_ticket(self, filename):
        """Cetak tiket parkir menggunakan win32print"""
        if not self.printer_available:
            logger.info("Melewati pencetakan tiket - printer tidak tersedia")
            return

        try:
            # Parse data dari filename
            ticket_number = filename.replace('.jpg', '')
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\nMencetak tiket:")
            print(f"Nomor: {ticket_number}")
            print(f"Waktu: {timestamp}")
            
            # Buka printer
            printer_handle = win32print.OpenPrinter(self.printer_name)
            print("✅ Berhasil membuka koneksi printer")
            
            # Start document
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Initialize printer dan reset
            win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
            
            # Center alignment
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            
            # Header - double height & width
            win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width & height
            win32print.WritePrinter(printer_handle, b"RSI BANJARNEGARA\n")
            win32print.WritePrinter(printer_handle, b"TIKET PARKIR\n")
            win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
            win32print.WritePrinter(printer_handle, b"================================\n")
            
            # Ticket details - left align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left alignment
            win32print.WritePrinter(printer_handle, f"Nomor : {ticket_number}\n".encode())
            win32print.WritePrinter(printer_handle, f"Waktu : {timestamp}\n".encode())
            win32print.WritePrinter(printer_handle, b"================================\n\n")
            
            # Center untuk barcode
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            
            # Reset text size to normal before barcode
            win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
            
            # Barcode configuration - CODE39
            win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")  # HRI below barcode
            win32print.WritePrinter(printer_handle, b"\x1D\x68\x50")  # Barcode height = 80 dots
            win32print.WritePrinter(printer_handle, b"\x1D\x77\x02")  # Barcode width = 2
            
            # Use CODE39 with clear format
            win32print.WritePrinter(printer_handle, b"\x1D\x6B\x04")  # Select CODE39
            
            # Simplify ticket number for better scanning
            simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number[-10:]
            barcode_data = f"*{simple_number}*".encode()  # Format CODE39
            win32print.WritePrinter(printer_handle, barcode_data)
            
            # Extra space after barcode
            win32print.WritePrinter(printer_handle, b"\n\n")
            
            # Footer - center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            win32print.WritePrinter(printer_handle, b"Terima kasih\n")
            win32print.WritePrinter(printer_handle, b"Jangan hilangkan tiket ini\n")
            
            # Feed and cut
            win32print.WritePrinter(printer_handle, b"\x1B\x64\x05")  # Feed 5 lines
            win32print.WritePrinter(printer_handle, b"\x1D\x56\x41\x00")  # Cut paper
            
            print("✅ Berhasil mengirim data ke printer")
            
            # Close printer
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            
            logger.info(f"Tiket berhasil dicetak: {filename}")
            print("✅ Tiket berhasil dicetak")
            
        except Exception as e:
            logger.error(f"Gagal mencetak tiket: {str(e)}")
            print(f"❌ Gagal mencetak tiket: {str(e)}")

    def run(self):
        """Main loop program"""
        print("""
================================
    SISTEM PARKIR RSI BNA    
================================
""")
        
        # Tampilkan mode operasi
        if self.connection_status['camera_type'] == 'IP Dahua':
            print("Mode Kamera: IP Dahua")
            print(f"IP: {self.config['camera']['ip']}")
            print(f"Resolution: 1920x1080 (Main) / 704x576 (Sub)")
        elif self.connection_status['camera_type'] == 'Local':
            print("Mode Kamera: Local Camera")
        else:
            print("Mode Kamera: Dummy (Tanpa Kamera)")
        
        # Tampilkan mode input    
        if hasattr(self, 'button_mode'):
            if self.button_mode == "arduino":
                print("\nMode Input: Arduino Pushbutton")
            else:
                print("\nMode Input: Keyboard")
        else:
            print("\nMode Input: Keyboard")
            
        # Tampilkan status printer
        print(f"\nStatus Printer: {'Tersedia - ' + self.printer_name if self.printer_available else 'Tidak Tersedia'}")
            
        # Tampilkan petunjuk input
        print("\nStatus: Menunggu input...")
        print("\nPesan untuk operator:")
        print("1. Gunakan salah satu metode berikut untuk mencetak tiket:")
        
        if hasattr(self, 'button_mode') and self.button_mode == "arduino":
            print("   - Tekan tombol fisik pada perangkat pushbutton")
        
        print("   - Tekan tombol '1' pada keyboard")
        print("   - Tekan tombol SPASI pada keyboard")
        print("   - Tekan tombol ENTER pada keyboard")
        
        print("\n2. Jangan tekan tombol terlalu cepat (minimal jeda 1 detik)")
        print("3. Pastikan printer dalam keadaan siap (kertas tersedia)")
        
        print("\n" + "="*32)
        
        try:
            while True:
                if self.check_button():  # Pushbutton ditekan
                    self.process_button_press()
                
                # Delay kecil untuk mengurangi CPU usage
                time.sleep(self.button_check_interval)
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan dengan Ctrl+C...")
        finally:
            self.cleanup()

    def check_button(self):
        """Cek status pushbutton dan keyboard dengan debounce dan reconnect otomatis"""
        try:
            current_time = time.time()
            
            # Cek keyboard input (selalu aktif)
            if msvcrt.kbhit():
                key = msvcrt.getch()
                # Menerima tombol '1', spasi (32), atau enter (13)
                if key in [b'1', b' ', b'\r']:
                    key_name = "1" if key == b'1' else "SPASI" if key == b' ' else "ENTER"
                    
                    # Cek debounce
                    if current_time - self.last_button_press >= self.debounce_delay:
                        print(f"\n⌨️ Tombol {key_name} terdeteksi")
                        self.last_button_press = current_time
                        logger.info(f"Tombol keyboard {key_name} terdeteksi")
                        
                        # Jika Arduino terhubung, kirim signal untuk gate
                        if self.button_mode == "arduino" and hasattr(self, 'button') and self.button and self.button.is_open:
                            try:
                                self.button.write(b'trigger\n')
                                logger.info("Trigger command sent to Arduino")
                            except Exception as e:
                                logger.error(f"Error mengirim trigger ke Arduino: {str(e)}")
                                # Tidak perlu langsung reconnect jika hanya error pada pengiriman trigger
                        return True
                    else:
                        remaining = self.debounce_delay - (current_time - self.last_button_press)
                        print(f"\n⏳ Mohon tunggu {remaining:.1f} detik...")
                        return False
            
            # Cek pushbutton Arduino jika dalam mode arduino
            if self.button_mode == "arduino" and hasattr(self, 'button') and self.button:
                try:
                    # Periksa apakah port masih terbuka, jika tidak coba reconnect
                    if not self.button.is_open:
                        logger.warning("Port Arduino tidak terbuka, mencoba reconnect...")
                        if self.reconnect_arduino():
                            logger.info("Reconnect berhasil, lanjutkan operasi normal")
                        else:
                            return False
                    
                    # Baca data dari Arduino
                    if self.button.in_waiting:
                        data = self.button.read_all().decode(errors='ignore').strip()
                        print(f"Data dari Arduino: {data}")  # Debug print
                        
                        # Cek berbagai format trigger
                        if any(signal in data.upper() for signal in ['PRESS', 'BUTTON', 'TRIGGER', '1', 'ON']):
                            # Cek debounce
                            if current_time - self.last_button_press >= self.debounce_delay:
                                print("\n🔘 Push button terdeteksi")
                                self.last_button_press = current_time
                                logger.info("Push button Arduino terdeteksi")
                                
                                # Clear buffer
                                self.button.reset_input_buffer()
                                return True
                            else:
                                remaining = self.debounce_delay - (current_time - self.last_button_press)
                                print(f"\n⏳ Mohon tunggu {remaining:.1f} detik...")
                                self.button.reset_input_buffer()
                                return False
                                
                except serial.SerialException as se:
                    # Error spesifik SerialException biasanya menandakan masalah koneksi
                    logger.error(f"Serial error dengan Arduino: {str(se)}")
                    print(f"\n⚠️ Masalah koneksi Arduino: {str(se)}")
                    
                    # Coba reconnect
                    if self.reconnect_arduino():
                        logger.info("Reconnect berhasil setelah serial exception")
                        return False  # Kembalikan False untuk skip proses saat ini
                    else:
                        # Jika reconnect gagal, beralih ke mode keyboard
                        print("⚠️ Gagal reconnect, beralih ke mode keyboard")
                        self.button_mode = "keyboard"
                        if hasattr(self, 'button') and self.button and self.button.is_open:
                            try:
                                self.button.close()
                            except:
                                pass
                        self.button = None
                        return False
                        
                except Exception as e:
                    logger.error(f"Error umum membaca Arduino: {str(e)}")
                    print(f"\n⚠️ Error pada Arduino: {str(e)}")
                    
                    # Hanya coba reconnect untuk error koneksi atau timeout
                    if "timeout" in str(e).lower() or "connection" in str(e).lower() or "i/o" in str(e).lower():
                        if self.reconnect_arduino():
                            logger.info("Reconnect berhasil setelah error umum")
                            return False
                    
                    # Untuk error lain yang lebih serius, beralih ke mode keyboard
                    print("⚠️ Beralih ke mode keyboard")
                    self.button_mode = "keyboard"
                    if hasattr(self, 'button') and self.button:
                        try:
                            self.button.close()
                        except:
                            pass
                        self.button = None
                    return False
            
            return False
            
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
                    self.print_ticket(filename)
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
        """Simpan data tiket ke database dengan auto-reconnect"""
        if not self.db_config:
            print("ℹ️ Mode tanpa database aktif")
            return
            
        try:
            # Periksa apakah koneksi masih aktif
            if not self.is_db_connected():
                print("⚠️ Koneksi database terputus, mencoba reconnect...")
                if not self.reconnect_database():
                    print("❌ Gagal reconnect ke database, tiket tidak disimpan")
                    return
            
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
            
        except psycopg2.OperationalError as oe:
            # Error koneksi, coba reconnect
            logger.error(f"Database operational error: {str(oe)}")
            print(f"⚠️ Database operational error: {str(oe)}")
            
            if self.reconnect_database():
                # Jika reconnect berhasil, coba simpan lagi
                print("✅ Reconnect berhasil, mencoba simpan data lagi...")
                try:
                    self.save_to_database(ticket_number, image_path)
                except Exception as e2:
                    logger.error(f"Gagal simpan data setelah reconnect: {str(e2)}")
                    print(f"❌ Gagal simpan data setelah reconnect: {str(e2)}")
            else:
                print("❌ Gagal reconnect ke database, tiket tidak disimpan")
                if self.db_conn:
                    try:
                        self.db_conn.rollback()
                    except:
                        pass
        
        except Exception as e:
            print(f"⚠️ Gagal menyimpan ke database: {str(e)}")
            logger.error(f"Database error: {str(e)}")
            if self.db_conn:
                try:
                    self.db_conn.rollback()
                except:
                    pass

if __name__ == "__main__":
    try:
        parking = ParkingCamera()
        parking.run()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 