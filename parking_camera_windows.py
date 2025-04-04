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
        
        # Tambahkan state untuk debounce
        self.last_button_press = 0
        self.debounce_delay = 10.0  # 10 detik delay antara press
        
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

    def images_are_different(self, img1, img2):
        """
        Membandingkan dua gambar untuk menentukan apakah objek berbeda
        Returns: True jika gambar cukup berbeda (kendaraan berbeda)
        """
        try:
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
        """Ambil gambar dari kamera"""
        try:
            # Baca frame dari kamera
            ret, frame = self.camera.read()
            if not ret:
                print("❌ Gagal mengambil gambar")
                return False, None

            # Generate nama file
            counter = self.get_counter()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"TKT{timestamp}_{counter:04d}.jpg"
            
            # Cek apakah gambar cukup berbeda dengan sebelumnya
            if self.check_similar_images and self.last_image is not None:
                if not self.images_are_different(frame, self.last_image):
                    print("ℹ️ Gambar terlalu mirip dengan capture sebelumnya")
                    print("ℹ️ Kemungkinan kendaraan yang sama, skip capture")
                    return False, None

            # Simpan gambar
            filepath = os.path.join(self.config['storage']['capture_dir'], filename)
            cv2.imwrite(filepath, frame)
            
            # Update last image dan timestamp
            self.last_image = frame.copy()
            self.last_capture_time = datetime.now()
            
            print(f"✅ Gambar disimpan: {filename}")
            return True, filename

        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
            print(f"❌ Error saat mengambil gambar: {str(e)}")
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
                                        return
                                except:
                                    continue
                    else:
                        print(f"\n⚠️ Gagal koneksi ke port {button_config['port']}: {str(e)}")
                    raise Exception(f"Gagal koneksi ke pushbutton: {str(e)}")
            else:
                raise Exception(f"Tipe button {button_config['type']} tidak didukung")
                
        except Exception as e:
            logger.error(f"Gagal setup pushbutton: {str(e)}")
            raise Exception(f"Gagal setup pushbutton: {str(e)}")

    def check_button(self):
        """Cek status pushbutton dengan debounce dan toleransi"""
        try:
            if self.button.in_waiting:
                # Baca semua data yang tersedia di buffer
                data = self.button.read_all().decode().strip()
                current_time = time.time()
                
                # Debug log
                if data:
                    logger.debug(f"Data tombol diterima: {repr(data)}")
                
                # Cek apakah sudah melewati waktu debounce
                if current_time - self.last_button_press >= self.debounce_delay:
                    # Cek berbagai kemungkinan input yang valid
                    if any(x in data for x in ['1', 'true', 'True', 'HIGH']):
                        self.last_button_press = current_time
                        logger.info("Tombol terdeteksi dengan benar")
                        return True
                    else:
                        # Jika ada data tapi tidak valid, mungkin tombol belum ditekan cukup kuat
                        if data:
                            print("⚠️ Tombol terdeteksi tapi tidak cukup kuat, tekan lebih lama")
                            logger.warning(f"Tombol terdeteksi tapi data tidak valid: {repr(data)}")
                else:
                    # Jika masih dalam masa debounce, tampilkan sisa waktu
                    remaining = self.debounce_delay - (current_time - self.last_button_press)
                    if data:  # Hanya tampilkan jika ada aktivitas tombol
                        print(f"⏳ Mohon tunggu {remaining:.1f} detik lagi...")
                        
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
                
                # Header - double height only
                win32print.WritePrinter(printer_handle, b"\x1B\x21\x10")  # Double height only
                win32print.WritePrinter(printer_handle, b"RSI BANJARNEGARA\n")
                win32print.WritePrinter(printer_handle, b"TIKET PARKIR\n")
                win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
                win32print.WritePrinter(printer_handle, b"================================\n")
                
                # Ticket details - left align, normal text
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left alignment
                win32print.WritePrinter(printer_handle, f"Nomor : {ticket_number}\n".encode())
                win32print.WritePrinter(printer_handle, f"Waktu : {timestamp}\n".encode())
                win32print.WritePrinter(printer_handle, b"================================\n")
                
                # Extra space before barcode
                win32print.WritePrinter(printer_handle, b"\n")
                
                # Barcode section - optimized for thermal printer
                win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")  # HRI below barcode
                win32print.WritePrinter(printer_handle, b"\x1D\x68\x64")  # Barcode height = 100 dots (12.5mm)
                win32print.WritePrinter(printer_handle, b"\x1D\x77\x03")  # Barcode width = 3 (thicker)
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
                
            except Exception as e:
                print(f"❌ Gagal mengirim data ke printer: {str(e)}")
                raise
            finally:
                try:
                    win32print.ClosePrinter(printer_handle)
                    print("✅ Koneksi printer ditutup")
                except:
                    pass
            
            print("✅ Tiket berhasil dicetak")
            
        except Exception as e:
            logger.error(f"Error printing ticket: {str(e)}")
            print(f"❌ Error saat mencetak tiket: {str(e)}")

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
        print("1. Mengambil gambar...")
        
        # Ambil gambar
        success, filename = self.capture_image()
        
        if success:
            print("2. Menyimpan ke database...")
            # Simpan ke database
            ticket_number = filename.replace('.jpg', '')
            image_path = os.path.join(self.config['storage']['capture_dir'], filename)
            self.save_to_database(ticket_number, image_path)
            
            # Cetak tiket jika printer tersedia
            print(f"3. Status printer: {'Tersedia' if self.printer_available else 'Tidak tersedia'}")
            if self.printer_available:
                print("4. Mencoba cetak tiket...")
                self.print_ticket(filename)
            else:
                print("❌ Printer tidak tersedia, tiket tidak bisa dicetak")
            
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