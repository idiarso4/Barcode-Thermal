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

# Handle psycopg2 import with graceful fallback
try:
    import psycopg2  # type: ignore
    from psycopg2 import Error  # type: ignore
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    # Create dummy classes to prevent errors
    class Error(Exception):
        pass

# Setup logging
logging.basicConfig(
    filename='parking.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_system')

# Konstanta untuk koneksi database
DB_SERVER = "192.168.2.6"
DB_PORT = 5432
DB_NAME = "parking_db"
DB_USER = "parking_user"
DB_PASSWORD = "parking_password"

# Konstanta untuk API
API_SERVER = "192.168.2.6"
API_PORT = 5050
API_ENDPOINT = "/api/tickets"

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
        
        # Tambahkan state untuk debounce
        self.last_button_press = 0
        self.debounce_delay = 0.5  # Set ke 0.5 detik untuk balance antara responsivitas dan stabilitas
        
        # Add additional timing parameters
        self.camera_initialization_delay = 5.0  # Wait 5 seconds after camera initialization
        self.button_check_interval = 0.5  # Check button every 0.5 seconds
        
        # Inisialisasi button
        self.button = None
        
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
        
        self.last_image = None
        self.last_capture_time = None
        self.min_image_diff = 0.15  # Turunkan ke 15% perbedaan
        self.check_similar_images = False  # Nonaktifkan pengecekan gambar yang mirip
        
        logger.info("Sistem parkir berhasil diinisialisasi")

    def setup_camera(self):
        """Setup koneksi ke kamera Dahua menggunakan RTSP"""
        try:
            # Nonaktifkan kamera dan gunakan dummy camera sementara
            print("\nMelewati inisialisasi kamera (mode dummy)...")
            print("✅ Mode dummy kamera aktif - tidak melakukan capture gambar sungguhan")
            logger.info("Kamera dilewati - menggunakan dummy mode")
            
            # Setup dummy camera untuk testing
            self.camera = None
            self.connection_status.update({
                'is_connected': True,
                'last_connected': datetime.now(),
                'reconnect_attempts': 0,
                'current_url': 'dummy://camera'
            })
            
            return
            
            # Kode koneksi kamera asli (dinonaktifkan sementara)
            """
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
            """
                
        except Exception as e:
            self.connection_status['is_connected'] = False
            logger.error(f"Gagal setup kamera: {str(e)}")
            raise Exception(f"Gagal setup kamera: {str(e)}")

    def images_are_different(self, img1, img2):
        """
        Membandingkan dua gambar untuk menentukan apakah objek berbeda
        Returns: True jika gambar cukup berbeda (kendaraan berbeda)
        """
        try:
            if img1 is None or img2 is None:
                return True
                
            # Convert ke grayscale
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

            # Hitung perbedaan
            diff = cv2.absdiff(gray1, gray2)
            
            # Hitung persentase perbedaan
            total_pixels = diff.shape[0] * diff.shape[1]
            different_pixels = np.count_nonzero(diff > 30)  # threshold 30
            difference_ratio = different_pixels / total_pixels

            logger.info(f"Perbedaan gambar: {difference_ratio:.2%}")
            return difference_ratio > self.min_image_diff

        except Exception as e:
            logger.error(f"Error comparing images: {str(e)}")
            return True  # Jika error, anggap berbeda untuk safety

    def capture_image(self):
        """Ambil gambar dari kamera (dummy mode)"""
        try:
            # Buat dummy image karena kamera dinonaktifkan
            print("✅ Menggunakan gambar dummy (tanpa kamera)")
            
            # Generate nama file dengan waktu Windows yang akurat
            current_time = datetime.now()
            counter = self.get_counter()
            filename = f"TKT{current_time.strftime('%Y%m%d%H%M%S')}_{counter:04d}.jpg"
            
            # Buat file dummy kosong
            filepath = os.path.join(self.config['storage']['capture_dir'], filename)
            
            # Cek apakah OpenCV tersedia
            try:
                # Jika OpenCV tersedia, buat dummy image sederhana
                height = int(self.config['image']['height'])
                width = int(self.config['image']['width'])
                dummy_image = np.zeros((height, width, 3), dtype=np.uint8)
                
                # Tambahkan background putih
                dummy_image.fill(255)
                
                # Tambahkan timestamp ke gambar
                timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(dummy_image, "DUMMY IMAGE - NO CAMERA", (50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                cv2.putText(dummy_image, f"Ticket: {filename}", (50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                cv2.putText(dummy_image, timestamp_str, (50, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Simpan dummy image dengan kompresi
                cv2.imwrite(filepath, dummy_image, [
                    cv2.IMWRITE_JPEG_QUALITY, int(self.config['image']['quality']),
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                    cv2.IMWRITE_JPEG_PROGRESSIVE, 1
                ])
                
                # Update last image untuk konsistensi
                self.last_image = dummy_image.copy()
                
            except Exception as e:
                # Jika OpenCV tidak dapat digunakan, buat file kosong saja
                logger.warning(f"Tidak dapat membuat dummy image, menggunakan file kosong: {str(e)}")
                with open(filepath, 'w') as f:
                    f.write("Dummy image file")
            
            print(f"✅ File dummy disimpan: {filename}")
            logger.info(f"File dummy dibuat dengan timestamp: {current_time}")
            return True, filename

        except Exception as e:
            logger.error(f"Error creating dummy image: {str(e)}")
            print(f"❌ Error saat membuat file dummy: {str(e)}")
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
            # Cek apakah ada file arduino_port.txt dan baca port yang tersimpan
            if os.path.exists("arduino_port.txt"):
                with open("arduino_port.txt", "r") as f:
                    saved_port = f.read().strip()
                    print(f"\nMenggunakan port Arduino yang tersimpan: {saved_port}")
                    try:
                        self.button = serial.Serial(
                            port=saved_port,
                            baudrate=9600,
                            timeout=0.1
                        )
                        
                        # Tunggu Arduino siap
                        time.sleep(2)
                        
                        # Bersihkan buffer
                        self.button.reset_input_buffer()
                        self.button.reset_output_buffer()
                        
                        # Coba kirim beberapa perintah diagnostik
                        print("Mengirim perintah diagnostik ke Arduino...")
                        self.button.write(b'check\n')
                        time.sleep(0.1)
                        if self.button.in_waiting:
                            resp = self.button.read_all().decode(errors='ignore')
                            print(f"  Respons: {repr(resp)}")
                        
                        self.button.write(b'test\n')
                        time.sleep(0.1)
                        if self.button.in_waiting:
                            resp = self.button.read_all().decode(errors='ignore')
                            print(f"  Respons: {repr(resp)}")
                            
                        self.button.write(b'status\n')
                        time.sleep(0.1)
                        if self.button.in_waiting:
                            resp = self.button.read_all().decode(errors='ignore')
                            print(f"  Respons: {repr(resp)}")
                            
                        # Aktifkan mode debug Arduino
                        self.button.write(b'debug:1\n')
                        time.sleep(0.1)
                        
                        print(f"✅ Pushbutton terhubung di port {saved_port}")
                        print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
                        self.button_mode = "serial"
                        return
                    except Exception as e:
                        print(f"❌ Gagal koneksi ke port {saved_port}: {str(e)}")
            
            # Fallback ke mode cek apakah mode dummy aktif
            if os.path.exists("dummy_arduino.flag"):
                print("\n✅ Menggunakan mode dummy Arduino untuk pushbutton")
                print("ℹ️ Tekan tombol '1' pada keyboard untuk simulasi button press")
                self.button_mode = "dummy"
                self.button = None
                return
                
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
                    
                    # Bersihkan buffer
                    self.button.reset_input_buffer()
                    self.button.reset_output_buffer()
                    
                    # Test koneksi dengan mengirim perintah
                    self.button.write(b'test\n')
                    time.sleep(0.1)
                    response = self.button.readline().decode().strip()
                    
                    if response:
                        logger.info(f"Koneksi serial ke pushbutton berhasil di port {button_config['port']}")
                        print(f"✅ Pushbutton terhubung di port {button_config['port']}")
                        print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
                        self.button_mode = "serial"
                    else:
                        raise Exception("Tidak ada respons dari perangkat")
                        
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
                                        print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
                                        self.button_mode = "serial"
                                        return
                                except:
                                    continue
                    else:
                        print(f"\n⚠️ Gagal koneksi ke port {button_config['port']}: {str(e)}")
                    
                    # Jika semua koneksi gagal, gunakan mode dummy
                    print("\n✅ Menggunakan mode dummy Arduino untuk pushbutton (fallback)")
                    print("ℹ️ Tekan tombol '1' pada keyboard untuk simulasi button press")
                    self.button_mode = "dummy"
                    self.button = None
                    return
            else:
                raise Exception(f"Tipe button {button_config['type']} tidak didukung")
                
        except Exception as e:
            logger.error(f"Gagal setup pushbutton: {str(e)}")
            # Gunakan mode dummy sebagai fallback
            print("\n✅ Menggunakan mode dummy Arduino untuk pushbutton (error fallback)")
            print("ℹ️ Tekan tombol '1' pada keyboard untuk simulasi button press")
            self.button_mode = "dummy"
            self.button = None

    def check_button(self):
        """Cek status pushbutton dengan debounce dan toleransi"""
        try:
            # Jika mode dummy, cek keyboard input '1'
            if hasattr(self, 'button_mode') and self.button_mode == "dummy":
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore')
                    current_time = time.time()
                    
                    # Debug log
                    if key:
                        logger.debug(f"Keyboard input diterima: {repr(key)}")
                    
                    # Cek apakah sudah melewati waktu debounce
                    if current_time - self.last_button_press >= self.debounce_delay:
                        # Cek keyboard input '1' untuk simulasi button press
                        if key == '1':
                            self.last_button_press = current_time
                            logger.info("Tombol dummy terdeteksi (keyboard '1')")
                            print("\n✅ Tombol '1' terdeteksi - memproses...")
                            return True
                    else:
                        # Jika masih dalam masa debounce, tampilkan sisa waktu
                        remaining = self.debounce_delay - (current_time - self.last_button_press)
                        if key == '1':  # Hanya tampilkan jika ada aktivitas tombol
                            print(f"\n⏳ Mohon tunggu {remaining:.1f} detik lagi...\n")
                            logger.debug(f"Tombol dalam debounce, sisa waktu: {remaining:.1f}s")
                return False
            
            # Mode serial (normal) - Arduino
            # Bersihkan buffer terlebih dahulu jika terlalu banyak data
            if self.button.in_waiting > 50:
                logger.warning(f"Buffer overflow: {self.button.in_waiting} bytes, membersihkan buffer")
                self.button.reset_input_buffer()
                return False
                
            # Cek apakah ada data
            if self.button.in_waiting:
                # Baca semua data yang tersedia di buffer
                data = self.button.read_all().decode(errors='ignore').strip()
                current_time = time.time()
                
                # Debug log untuk semua data
                if data:
                    logger.debug(f"Data tombol diterima: {repr(data)}")
                    print(f"\nData dari Arduino: {repr(data)}")
                
                # Cek apakah sudah melewati waktu debounce
                if current_time - self.last_button_press >= self.debounce_delay:
                    # Cek berbagai kemungkinan input yang valid
                    if any(str(x) in data for x in range(1, 10)) or any(x in data for x in ['1', 'true', 'True', 'HIGH', 'READY']):
                        self.last_button_press = current_time
                        logger.info(f"Tombol terdeteksi: {repr(data)}")
                        print("\n✅ Tombol Arduino terdeteksi - memproses...")
                        return True
                    else:
                        # Jika ada data tapi tidak valid, coba proses juga jika tidak kosong
                        if data:
                            logger.info(f"Tombol terdeteksi dengan data tidak standar: {repr(data)}")
                            self.last_button_press = current_time
                            print("\n✅ Tombol Arduino terdeteksi (data non-standar) - memproses...")
                            return True
                else:
                    # Jika masih dalam masa debounce, tampilkan sisa waktu
                    remaining = self.debounce_delay - (current_time - self.last_button_press)
                    if data:  # Hanya tampilkan jika ada aktivitas tombol
                        print(f"\n⏳ Mohon tunggu {remaining:.1f} detik lagi...\n")
                        logger.debug(f"Tombol dalam debounce, sisa waktu: {remaining:.1f}s")
            
            # Coba polling aktif untuk Arduino
            # Kirim sinyal 'check' setiap 2 detik untuk mendapatkan status
            if hasattr(self, '_last_poll_time'):
                if time.time() - self._last_poll_time > 2:
                    try:
                        self.button.write(b'check\n')
                        self._last_poll_time = time.time()
                    except:
                        pass
            else:
                self._last_poll_time = time.time()
                
            return False
        except Exception as e:
            logger.error(f"Error membaca pushbutton: {str(e)}")
            self.last_button_press = time.time()  # Hindari error beruntun
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

    def get_counter(self):
        """Get dan increment counter"""
        self.counter += 1
        self.save_counter()
        return self.counter

    def check_printer_ready(self):
        """Check if printer is ready before printing"""
        try:
            # Simple check - rely on win32print
            if not self.printer_available:
                return False
                
            # Try to get printer status
            try:
                printer_handle = win32print.OpenPrinter(self.printer_name)
                win32print.ClosePrinter(printer_handle)
                return True
            except Exception as e:
                logger.error(f"Printer not ready: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking printer status: {e}")
            return False

    def print_ticket(self, filename):
        """Cetak tiket dengan barcode CODE39"""
        try:
            if not self.printer_available:
                print("❌ Printer tidak tersedia")
                return
                
            # Parse data dari filename
            ticket_number = filename.replace('.jpg', '')
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\nMencetak tiket:")
            print(f"Nomor: {ticket_number}")
            print(f"Waktu: {timestamp}")
            
            # Buka printer
            try:
                printer_handle = win32print.OpenPrinter(self.printer_name)
                print("✅ Berhasil membuka koneksi printer")
            except Exception as e:
                print(f"❌ Gagal membuka printer: {str(e)}")
                return
                
            try:
                # Start document
                job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
                win32print.StartPagePrinter(printer_handle)
                
                # Initialize printer
                win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
                
                # Header - double height & width
                win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width & height
                win32print.WritePrinter(printer_handle, b"RSI BANJARNEGARA\n")
                win32print.WritePrinter(printer_handle, b"TIKET PARKIR\n")
                win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
                win32print.WritePrinter(printer_handle, b"================================\n")
                
                # Ticket details - left align, normal text
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left alignment
                win32print.WritePrinter(printer_handle, f"Nomor : {ticket_number}\n".encode())
                win32print.WritePrinter(printer_handle, f"Waktu : {timestamp}\n".encode())
                win32print.WritePrinter(printer_handle, b"================================\n")
                
                # Barcode section - optimized for thermal printer
                win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")  # HRI below barcode
                win32print.WritePrinter(printer_handle, b"\x1D\x68\x50")  # Barcode height = 80 dots
                win32print.WritePrinter(printer_handle, b"\x1D\x77\x02")  # Barcode width = 2
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
                
                # Use CODE39 with clear format
                win32print.WritePrinter(printer_handle, b"\x1D\x6B\x04")  # Select CODE39
                
                # Simplify ticket number for better scanning
                simple_number = ticket_number.split('_')[1]  # Ambil hanya nomor urut
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
                
                print("✅ Tiket berhasil dicetak")
                
            except Exception as e:
                print(f"❌ Gagal mengirim data ke printer: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error printing ticket: {str(e)}")
            print(f"❌ Error saat mencetak tiket: {str(e)}")

    def setup_database(self):
        """Setup koneksi ke database atau API"""
        try:
            # Cek apakah psycopg2 tersedia
            if not PSYCOPG2_AVAILABLE:
                logger.warning("Modul psycopg2 tidak tersedia, menggunakan mode API atau dummy")
                print("⚠️ Modul database tidak tersedia, mencoba API...")
                self.db_mode = "api"
                
                # Coba koneksi ke API
                try:
                    api_url = f"http://{API_SERVER}:{API_PORT}{API_ENDPOINT}/test"
                    response = requests.get(api_url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ API terkoneksi ke {API_SERVER}")
                        logger.info(f"Koneksi API berhasil ke {API_SERVER}")
                        return True
                    else:
                        raise Exception(f"API status code: {response.status_code}")
                except Exception as api_error:
                    logger.warning(f"Koneksi API gagal: {str(api_error)}")
                    print(f"⚠️ Koneksi API gagal, menggunakan mode dummy")
                    self.db_mode = "dummy"
                    return True
            
            # Coba koneksi database ke server jika psycopg2 tersedia
            try:
                # Koneksi langsung ke PostgreSQL
                self.db_conn = psycopg2.connect(
                    host=DB_SERVER,
                    port=DB_PORT,
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD
                )
                print(f"✅ Database terkoneksi ke {DB_SERVER}")
                logger.info(f"Koneksi database berhasil ke {DB_SERVER}")
                self.db_mode = "direct"
                return True
            except Exception as db_error:
                # Jika koneksi database gagal, gunakan API
                logger.warning(f"Koneksi database PostgreSQL gagal: {str(db_error)}")
                print(f"⚠️ Koneksi database gagal, mencoba API...")
                
                # Test API
                api_url = f"http://{API_SERVER}:{API_PORT}{API_ENDPOINT}/test"
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ API terkoneksi ke {API_SERVER}")
                    logger.info(f"Koneksi API berhasil ke {API_SERVER}")
                    self.db_mode = "api"
                    return True
                else:
                    raise Exception(f"API status code: {response.status_code}")
        except Exception as e:
            # Fallback ke mode dummy jika semua koneksi gagal
            logger.error(f"Gagal koneksi ke database dan API: {str(e)}")
            print(f"⚠️ Gagal koneksi ke server {DB_SERVER}, menggunakan mode dummy")
            self.db_mode = "dummy"
            return True
            
    def save_to_database(self, ticket_number, image_path):
        """Simpan data tiket ke database atau API"""
        try:
            if self.db_mode == "direct" and PSYCOPG2_AVAILABLE:
                # Koneksi langsung ke PostgreSQL
                cur = self.db_conn.cursor()
                
                # Baca file gambar sebagai binary
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                # Query untuk insert data
                sql = """
                INSERT INTO tickets (ticket_number, capture_time, image_data) 
                VALUES (%s, %s, %s)
                """
                
                # Eksekusi query
                cur.execute(sql, (ticket_number, datetime.now(), psycopg2.Binary(image_data)))
                self.db_conn.commit()
                cur.close()
                
                logger.info(f"Data tiket {ticket_number} berhasil disimpan ke database")
                print("✅ Data tersimpan di database")
                return True
                
            elif self.db_mode == "api":
                # Kirim data melalui API
                api_url = f"http://{API_SERVER}:{API_PORT}{API_ENDPOINT}"
                
                # Kirim file gambar
                files = {'image': open(image_path, 'rb')}
                data = {'ticket_number': ticket_number, 'timestamp': datetime.now().isoformat()}
                
                try:
                    response = requests.post(api_url, files=files, data=data, timeout=10)
                    if response.status_code == 200:
                        logger.info(f"Data tiket {ticket_number} berhasil dikirim ke API")
                        print("✅ Data terkirim ke API server")
                        return True
                    else:
                        logger.error(f"API error: {response.status_code} - {response.text}")
                        print(f"❌ API error: {response.status_code}")
                        # Fallback ke mode dummy jika API gagal
                        self.db_mode = "dummy"
                except Exception as api_error:
                    logger.error(f"Gagal mengirim ke API: {str(api_error)}")
                    print(f"❌ Gagal mengirim ke API: Connection error")
                    # Fallback ke mode dummy
                    self.db_mode = "dummy"
            
            # Mode dummy (jika semua koneksi gagal atau awalnya diset dummy)
            if self.db_mode == "dummy":
                logger.info(f"[DUMMY MODE] Data tiket {ticket_number} disimulasikan tersimpan")
                print("✅ Data tersimpan (mode dummy)")
                return True
                
        except Exception as e:
            logger.error(f"Gagal menyimpan data: {str(e)}")
            print(f"❌ Gagal menyimpan data: {str(e)}")
            return False

    def process_button_press(self):
        """Proses ketika tombol ditekan - ambil gambar, cetak tiket, dan simpan ke database"""
        try:
            # Tambah delay kecil untuk stabilisasi
            time.sleep(0.2)  # Kurangi dari 0.5 detik menjadi 0.2 detik untuk stabilisasi kamera
            
            print("\n\nMemproses... Mohon tunggu...\n")
            print("1. Mengambil gambar...")
            logger.info("Mulai proses capture gambar")
            
            # Cek apakah ada capture yang masih diproses
            current_time = time.time()
            if hasattr(self, 'last_capture_time') and self.last_capture_time:
                time_since_last = current_time - self.last_capture_time
                if time_since_last < 1:  # Kurangi dari 2 menjadi 1 detik antara capture
                    print("⚠️ Terlalu cepat! Mohon tunggu...\n")
                    logger.warning(f"Capture terlalu cepat, interval: {time_since_last:.1f}s")
                    return
            
            # Jangan coba membaca frame jika kamera adalah None
            if self.camera is not None:
                # Ambil beberapa frame untuk stabilisasi
                for _ in range(3):  # Ambil 3 frame untuk stabilisasi
                    self.camera.read()
            
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
                time.sleep(0.2)  # Kurangi dari 0.5 detik menjadi 0.2 detik setelah proses
                print("\n\nStatus: Menunggu input berikutnya...\n")
                logger.info("Proses capture selesai dengan sukses")
            else:
                print("\n❌ Gagal mengambil gambar!\n")
                logger.error("Gagal melakukan capture gambar")
                
        except Exception as e:
            logger.error(f"Error dalam process_button_press: {str(e)}")
            print(f"\n❌ Error saat memproses: {str(e)}\n")

    def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'camera') and self.camera is not None:
                self.camera.release()
                
            # Hanya tutup koneksi serial jika bukan mode dummy
            if hasattr(self, 'button_mode') and self.button_mode != "dummy" and hasattr(self, 'button') and self.button is not None:
                self.button.close()
                
            logger.info("Cleanup berhasil")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def run(self):
        """Main loop program"""
        button_mode_str = "Dummy (Keyboard)" if hasattr(self, 'button_mode') and self.button_mode == "dummy" else "Pushbutton (Arduino)"
        
        print(f"""
================================
    SISTEM PARKIR RSI BNA    
================================
Mode: {button_mode_str} (Tanpa Kamera)
Status: Menunggu input dari {"keyboard (tekan '1')" if hasattr(self, 'button_mode') and self.button_mode == "dummy" else "pushbutton"}...

        """)
        
        try:
            while True:
                if self.check_button():  # Pushbutton ditekan
                    self.process_button_press()
                
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
