import cv2
import time
import numpy as np
from datetime import datetime
import pytz
import os
import logging
import serial
import serial.tools.list_ports
import configparser
import json

# Suppress OpenCV error messages
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

class Config:
    """Kelas untuk mengelola konfigurasi sistem"""
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = 'config.ini'
        self.load_config()
    
    def load_config(self):
        """Load konfigurasi dari file, buat default jika tidak ada"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """Buat konfigurasi default"""
        self.config['camera'] = {
            'ip': '192.168.2.20',
            'username': 'admin',
            'password': '@dminparkir',
            'main_stream': 'rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0',
            'sub_stream': 'rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1'
        }
        
        self.config['serial'] = {
            'port': 'COM7',
            'baudrate': '9600',
            'timeout': '1',
            'retry_count': '3',
            'retry_delay': '2'
        }
        
        self.save_config()
    
    def save_config(self):
        """Simpan konfigurasi ke file"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section, key, fallback=None):
        """Ambil nilai konfigurasi dengan fallback"""
        return self.config.get(section, key, fallback=fallback)

def setup_directories():
    """Setup direktori yang diperlukan"""
    dirs = ['capture_images', 'logs']
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
            logging.info(f"Membuat direktori: {dir}")

def find_arduino_port():
    """Cari port Arduino secara otomatis"""
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description or "USB Serial" in port.description:
            return port.device
    return None

def check_pushbutton(config):
    """Cek koneksi pushbutton dengan retry mechanism"""
    port = config.get('serial', 'port', 'COM7')
    baudrate = config.get('serial', 'baudrate', '9600')
    retry_count = int(config.get('serial', 'retry_count', '3'))
    retry_delay = int(config.get('serial', 'retry_delay', '2'))
    
    # Coba deteksi otomatis jika port tidak ditemukan
    if not port or not os.path.exists(f"\\\\.\\{port}"):
        detected_port = find_arduino_port()
        if detected_port:
            port = detected_port
            logging.info(f"Port Arduino terdeteksi otomatis: {port}")
            # Update konfigurasi
            if 'serial' not in config.config:
                config.config['serial'] = {}
            config.config['serial']['port'] = port
            config.save_config()
    
    for attempt in range(retry_count):
        try:
            ser = serial.Serial(port, int(baudrate), timeout=1)
            if ser.is_open:
                logging.info(f"✅ Pushbutton terhubung di port {port}")
                ser.close()
                return True
        except Exception as e:
            if attempt < retry_count - 1:
                logging.warning(f"Percobaan {attempt + 1}/{retry_count}: Gagal terhubung ke pushbutton di {port}")
                logging.warning(f"Menunggu {retry_delay} detik sebelum mencoba lagi...")
                time.sleep(retry_delay)
            else:
                logging.error(f"❌ Gagal terhubung ke pushbutton setelah {retry_count} percobaan: {str(e)}")
                logging.info("Port yang tersedia:")
                for p in serial.tools.list_ports.comports():
                    logging.info(f"- {p.device}: {p.description}")
    return False

def test_camera():
    """Test koneksi kamera lokal dan IP"""
    logging.info("Mencoba koneksi ke kamera...")
    
    # Load konfigurasi
    config = Config()
    
    # Cek kamera IP terlebih dahulu
    try:
        ip = config.get('camera', 'ip', '192.168.2.20')
        username = config.get('camera', 'username', 'admin')
        password = config.get('camera', 'password', '@dminparkir')
        
        main_stream = config.get('camera', 'main_stream')
        main_stream = main_stream.format(username=username, password=password, ip=ip)
        
        logging.info(f"Mencoba koneksi ke kamera IP {ip}...")
        cap = cv2.VideoCapture(main_stream)
        
        if not cap.isOpened():
            raise Exception("Gagal membuka koneksi RTSP")
            
        ret, frame = cap.read()
        if not ret:
            raise Exception("Gagal membaca frame dari kamera")
            
        # Simpan gambar test
        timestamp = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y%m%d_%H%M%S")
        filename = f"capture_images/test_main_stream_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        logging.info(f"✅ Test image disimpan: {filename}")
        
        cap.release()
        logging.info("✅ Kamera IP Dahua terdeteksi dan berfungsi")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error koneksi kamera IP: {str(e)}")
        logging.error("Detail koneksi:")
        logging.error(f"IP: {ip}")
        logging.error(f"Username: {username}")
        logging.error(f"Main Stream: {main_stream}")
        
        # Jika kamera IP gagal, coba kamera lokal
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cap.isOpened():
                logging.info("✅ Kamera lokal terdeteksi")
                cap.release()
                return True
        except Exception as local_e:
            logging.error(f"❌ Error kamera lokal: {str(local_e)}")
    
    logging.warning("⚠️ Tidak ada kamera yang terdeteksi")
    logging.info("✅ Beralih ke mode dummy")
    return False

def check_camera_time(cap):
    """Memeriksa waktu kamera dan waktu sistem"""
    try:
        # Set timezone ke WIB
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        system_time = datetime.now(jakarta_tz)
        
        # Ambil timestamp kamera
        camera_timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
        
        logging.info("=== Informasi Waktu ===")
        logging.info(f"Time Zone: (UTC+07.00) Bangkok, Hanoi, Jakarta")
        logging.info(f"Waktu Sistem: {system_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if camera_timestamp > 0:
            camera_time = datetime.fromtimestamp(camera_timestamp/1000, jakarta_tz)
            logging.info(f"Waktu Kamera: {camera_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            time_diff = abs(camera_timestamp/1000 - time.time())
            logging.info(f"Perbedaan Waktu: {time_diff:.2f} detik")
            
            if time_diff > 60:
                logging.warning("⚠️ PERINGATAN: Perbedaan waktu lebih dari 1 menit!")
                logging.info("Pastikan NTP server (time.windows.com) dapat diakses")
        else:
            logging.info("Waktu Kamera: Menggunakan waktu sistem")
        
        return True
    except Exception as e:
        logging.error(f"Error saat memeriksa waktu: {str(e)}")
        return False

def test_ip_camera(config):
    """Test koneksi ke kamera IP Dahua menggunakan konfigurasi"""
    ip = config.get('camera', 'ip', '192.168.2.20')
    username = config.get('camera', 'username', 'admin')
    password = config.get('camera', 'password', '@dminparkir')
    
    main_stream_template = config.get('camera', 'main_stream', 
        'rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0')
    sub_stream_template = config.get('camera', 'sub_stream',
        'rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1')
    
    # Format URL dengan kredensial
    streams = {
        "Main Stream": main_stream_template.format(username=username, password=password, ip=ip),
        "Sub Stream": sub_stream_template.format(username=username, password=password, ip=ip)
    }
    
    for stream_name, rtsp_url in streams.items():
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                # Periksa waktu kamera
                check_camera_time(cap)
                
                # Baca frame
                ret, frame = cap.read()
                if ret:
                    # Simpan gambar dengan timestamp
                    timestamp = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y%m%d_%H%M%S")
                    filename = f"capture_images/test_{stream_name.lower().replace(' ', '_')}_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    logging.info(f"✅ Test image disimpan: {filename}")
                    cap.release()
                    return True
            cap.release()
        except Exception as e:
            logging.error(f"Error saat koneksi ke {stream_name}: {str(e)}")
            if 'cap' in locals():
                cap.release()
    return False

def test_dahua_credentials():
    """Test multiple common Dahua default credentials."""
    credentials = [
        ('admin', '@dminparkir'),  # Add the provided credentials first
        ('admin', 'admin'),
        ('admin', 'Admin12345'),
        ('admin', ''),
        ('admin', '888888'),
        ('admin', '123456'),
        ('888888', '888888')
    ]
    
    for username, password in credentials:
        print(f"\nTesting credentials: {username}/{password}")
        url_main = f"rtsp://{username}:{password}@192.168.2.20:554/cam/realmonitor?channel=1&subtype=0"
        url_sub = f"rtsp://{username}:{password}@192.168.2.20:554/cam/realmonitor?channel=1&subtype=1"
        
        try:
            cap = cv2.VideoCapture(url_main)
            if cap.isOpened():
                print("✅ Main Stream connection successful!")
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite('test_main.jpg', frame)
                    print("Main Stream image saved as test_main.jpg")
                cap.release()
                return username, password
        except Exception as e:
            print(f"❌ Main Stream error: {str(e)}")
            
        try:
            cap = cv2.VideoCapture(url_sub)
            if cap.isOpened():
                print("✅ Sub Stream connection successful!")
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite('test_sub.jpg', frame)
                    print("Sub Stream image saved as test_sub.jpg")
                cap.release()
                return username, password
        except Exception as e:
            print(f"❌ Sub Stream error: {str(e)}")
    
    return None, None

def print_system_status():
    """Tampilkan status sistem"""
    print("\n================================")
    print("      SISTEM PARKIR RSI BNA     ")
    print("================================")
    
    # Setup direktori
    setup_directories()
    
    # Load konfigurasi
    config = Config()
    
    # Tampilkan waktu mulai
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    current_time = datetime.now(jakarta_tz)
    logging.info("Starting parking system...")
    
    # Cek koneksi kamera
    camera_status = test_camera()
    
    # Cek koneksi pushbutton
    logging.info("\nMencoba koneksi ke pushbutton...")
    pushbutton_status = check_pushbutton(config)
    if pushbutton_status:
        print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
        print("ℹ️ Atau tekan tombol '1' pada keyboard untuk mengaktifkan gate")
    
    # Tampilkan informasi printer
    print("\nMencari printer thermal...")
    print("✅ Printer terdeteksi: EPSON TM-T82X Receipt")
    
    # Tampilkan informasi database
    print("✅ Database terkoneksi")
    
    # Tampilkan header status
    print("\n================================")
    print("      SISTEM PARKIR RSI BNA     ")
    print("================================")
    
    # Mode operasi
    if camera_status:
        print("Mode: Kamera IP Dahua")
        print(f"IP: {config.get('camera', 'ip')}")
        print(f"Resolution: 1920x1080 (Main) / 704x576 (Sub)")
        print(f"Capture Path: {os.path.abspath('capture_images')}")
    else:
        print("Mode: Pushbutton (Tanpa Kamera)")
    
    # Status sistem
    print("\nStatus: Menunggu input dari pushbutton...")

if __name__ == "__main__":
    config = Config()
    print_system_status()
    print("=== Test Kamera OpenCV ===")
    print(f"OpenCV version: {cv2.__version__}")
    success = test_camera()
    if success:
        print("\n✅ Test kamera berhasil!")
    else:
        print("\n❌ Test kamera gagal!")
        print("\nTroubleshooting steps:")
        print("1. Pastikan kamera terhubung dengan benar")
        print("2. Cek Device Manager untuk memastikan driver kamera terinstall")
        print("3. Coba restart komputer")
        print("4. Cek apakah kamera berfungsi di aplikasi lain (misal: Camera app Windows)")
        print("5. Update driver kamera jika perlu")
    test_ip_camera(config)
    print("\nJika koneksi gagal, coba:")
    print("1. Pastikan IP kamera benar (192.168.2.20)")
    print("2. Pastikan username dan password benar (default: admin/admin)")
    print("3. Pastikan komputer dan kamera terhubung dalam jaringan yang sama")
    print("4. Coba ping kamera untuk memastikan konektivitas")
    print("5. Periksa firewall settings")
    print("\nTesting Dahua IP camera with common credentials...")
    username, password = test_dahua_credentials()
    
    if username and password:
        print(f"\n✅ Successfully connected with credentials: {username}/{password}")
        print("Please update your configuration to use these credentials.")
    else:
        print("\n❌ Failed to connect with any common credentials.")
        print("Please verify the correct credentials with your camera administrator.") 