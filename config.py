# Konfigurasi API
API_CONFIG = {
    'base_url': 'http://192.168.2.6:5050',
    'timeout': 30,
    'max_retries': 3
}

# Konfigurasi Database
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'parkir2',
    'user': 'postgres',
    'password': 'postgres'
}

# Konfigurasi Printer
PRINTER_CONFIG = {
    'name': 'TM-T82X-S-A',
    'port': '/dev/usb/lp0',
    'baudrate': 9600,
    'timeout': 5000
}

# Konfigurasi Kamera
CAMERA_CONFIG = {
    'device_index': 0,
    'resolution': (640, 480),
    'fps': 30
}

# Konfigurasi Logging
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/client.log'
} 