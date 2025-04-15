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

# Setup logging
logging.basicConfig(
    filename='parking.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_system')

class ParkingCamera:
    def __init__(self):
        # Konfigurasi kamera
        self.camera_ip = "192.168.2.20"
        self.camera_user = "admin"
        self.camera_pass = "@dminparkir"
        self.rtsp_url = f"rtsp://{self.camera_user}:{self.camera_pass}@{self.camera_ip}/cam/realmonitor?channel=1&subtype=0"
        
        # Konfigurasi capture
        self.capture_dir = "capture"
        self.image_quality = 60  # JPEG quality (1-100)
        self.target_size = (800, 600)  # Ukuran gambar yang lebih kecil
        
        # Buat folder jika belum ada
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
            logger.info(f"Folder capture dibuat: {self.capture_dir}")
        
        # Setup kamera
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
        self.debounce_delay = 0.5  # Turunkan dari 1.0 ke 0.5 detik untuk lebih responsif
        
        # Add additional timing parameters
        self.camera_initialization_delay = 2.0  # Turunkan dari 5.0 ke 2.0 detik
        self.button_check_interval = 0.05  # Turunkan dari 0.1 ke 0.05 untuk lebih responsif
        
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
        """Setup kamera - bisa mode dummy atau real camera"""
        try:
            print("\nMelewati inisialisasi kamera (mode dummy)...")
            self.camera = None
            print("✅ Mode dummy kamera aktif - tidak melakukan capture gambar sungguhan")
            return
        except Exception as e:
            logger.error(f"Error setting up camera: {str(e)}")
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
        """Capture gambar - mode dummy akan menghasilkan file kosong"""
        try:
            # Generate nama file berdasarkan timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            counter = str(random.randint(1000, 9999))
            filename = f"TKT{timestamp}_{counter}.jpg"
            filepath = os.path.join(self.capture_dir, filename)
            
            # Dalam mode dummy, buat file kosong
            with open(filepath, 'w') as f:
                pass
                
            # Buat file JSON dengan metadata
            json_data = {
                "timestamp": timestamp,
                "counter": counter,
                "mode": "dummy"
            }
            
            with open(filepath + ".json", 'w') as f:
                json.dump(json_data, f, indent=4)
                
            print("✅ Menggunakan gambar dummy (tanpa kamera)")
            print(f"✅ File dummy disimpan: {filename}")
            
            self.last_capture_time = time.time()
            return True, filename
            
        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
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
            # Import msvcrt di sini untuk handle keyboard
            global msvcrt
            import msvcrt
            
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
                    self.button.write(b'TEST\n')
                    time.sleep(0.1)
                    response = self.button.readline().decode().strip()
                    
                    if response:
                        logger.info(f"Koneksi serial ke pushbutton berhasil di port {button_config['port']}")
                        print(f"✅ Pushbutton terhubung di port {button_config['port']}")
                        print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
                        print("ℹ️ Atau tekan tombol '1' pada keyboard untuk mengaktifkan gate")
                        self.button_mode = "serial"
                        
                        # Kirim inisialisasi ke Arduino
                        self.button.write(b'INIT\n')
                        logger.info("Sinyal inisialisasi dikirim ke Arduino")
                        return
                    else:
                        print("⚠️ Tidak ada respons dari perangkat")
                        print("ℹ️ Push button tidak terdeteksi, tapi Anda tetap bisa menggunakan tombol '1'")
                        self.button_mode = "simulation"
                        if hasattr(self, 'button'):
                            self.button.close()
                        return
                        
                except serial.SerialException as e:
                    print(f"\n⚠️ Error koneksi push button: {str(e)}")
                    print("ℹ️ Anda tetap bisa menggunakan tombol '1' pada keyboard")
                    self.button_mode = "simulation"
                    return
            else:
                print("⚠️ Mode pushbutton tidak dikenali")
                print("ℹ️ Anda tetap bisa menggunakan tombol '1' pada keyboard")
                self.button_mode = "simulation"
                return
                
        except Exception as e:
            logger.error(f"Setup pushbutton warning: {str(e)}")
            print("⚠️ Terjadi error pada setup push button")
            print("ℹ️ Anda tetap bisa menggunakan tombol '1' pada keyboard")
            self.button_mode = "simulation"

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
                        # Kirim sinyal ke Arduino untuk mengangkat gate
                        if self.button_mode == "serial" and hasattr(self, 'button'):
                            try:
                                self.button.write(b'OPEN\n')  # Kirim perintah ke Arduino
                                print("🔄 Mengirim sinyal buka gate...")
                                logger.info("Sinyal buka gate dikirim dari keyboard")
                            except Exception as e:
                                logger.error(f"Gagal mengirim sinyal ke Arduino: {str(e)}")
            
            # Cek pushbutton fisik
            if self.button_mode == "serial" and self.button.in_waiting:
                data = self.button.read_all().decode().strip()
                
                # Debug log
                if data:
                    logger.debug(f"Data tombol diterima: {repr(data)}")
                
                # Cek apakah sudah melewati waktu debounce
                if current_time - self.last_button_press >= self.debounce_delay:
                    # Reset buffer setelah membaca
                    self.button.reset_input_buffer()
                    
                    # Cek berbagai kemungkinan input yang valid
                    if any(x in data for x in ['1', 'true', 'True', 'HIGH']):
                        print("\n🔘 Push button fisik terdeteksi")
                        self.last_button_press = current_time
                        button_pressed = True
                        logger.info("Push button terdeteksi dengan benar")
                        # Kirim konfirmasi ke Arduino
                        try:
                            self.button.write(b'ACK\n')  # Acknowledge signal received
                            logger.info("Sinyal ACK dikirim ke Arduino")
                        except Exception as e:
                            logger.error(f"Gagal mengirim ACK: {str(e)}")
                    else:
                        # Jika ada data tapi tidak valid, coba proses juga
                        if data:
                            print("\n🔘 Push button terdeteksi (data tidak standar)")
                            logger.info(f"Push button terdeteksi dengan data tidak standar: {repr(data)}")
                            self.last_button_press = current_time
                            button_pressed = True
                else:
                    # Jika masih dalam masa debounce, bersihkan buffer
                    self.button.reset_input_buffer()
                    
                    # Tampilkan sisa waktu jika ada aktivitas tombol
                    if data:
                        remaining = self.debounce_delay - (current_time - self.last_button_press)
                        print(f"\n⏳ Mohon tunggu {remaining:.1f} detik lagi...")
                        logger.debug(f"Tombol dalam debounce, sisa waktu: {remaining:.1f}s")
            
            return button_pressed
            
        except Exception as e:
            logger.error(f"Error membaca input: {str(e)}")
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
        printer_handle = None
        try:
            if not self.printer_available:
                print("❌ Printer tidak tersedia")
                return
                
            # Buka printer
            print("\nMembuka koneksi printer...")
            printer_handle = win32print.OpenPrinter(self.printer_name)
            print("✅ Berhasil membuka koneksi printer")
            
            # Mulai dokumen baru
            print("Memulai dokumen baru...")
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Parse data tiket
            timestamp = datetime.now()
            ticket_number = filename.replace('.jpg','')
            simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number
            
            # Siapkan data untuk dicetak - gunakan format yang lebih sederhana
            print_data = bytearray()
            
            # Reset dan inisialisasi printer
            print_data += b"\x1B\x40"  # Initialize printer
            
            # Set mode printer
            print_data += b"\x1B\x21\x00"  # Normal text mode
            print_data += b"\x1B\x61\x01"  # Center alignment
            
            # Header
            print_data += b"\x1B\x21\x30"  # Double width & height
            print_data += b"RSI BANJARNEGARA\n"
            print_data += b"TIKET PARKIR\n"
            print_data += b"\x1B\x21\x00"  # Normal text
            print_data += b"================================\n"
            
            # Informasi tiket (left align)
            print_data += b"\x1B\x61\x00"  # Left alignment
            print_data += f"Nomor : {ticket_number}\n".encode()
            print_data += f"Waktu : {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n".encode()
            print_data += b"================================\n"
            
            # Barcode (center)
            print_data += b"\x1B\x61\x01"  # Center alignment
            print_data += b"\x1D\x68\x50"  # Barcode height
            print_data += b"\x1D\x77\x02"  # Barcode width
            print_data += b"\x1D\x48\x02"  # HRI below barcode
            print_data += b"\x1D\x6B\x04"  # CODE39
            print_data += bytes([len(simple_number)])
            print_data += simple_number.encode()
            
            # Footer
            print_data += b"\n\n"
            print_data += b"Terima kasih\n"
            print_data += b"Jangan hilangkan tiket ini\n\n"
            
            # Kirim data ke printer
            print("Mengirim data ke printer...")
            
            # Kirim dalam satu operasi
            result = win32print.WritePrinter(printer_handle, print_data)
            print(f"Data terkirim: {result} bytes")
            
            # Tunggu sebentar
            time.sleep(0.5)
            
            # Feed dan cut
            print("Memotong tiket...")
            cut_command = bytearray()
            cut_command += b"\x1B\x64\x03"  # Feed 3 lines
            cut_command += b"\x1D\x56\x41"  # Full cut
            win32print.WritePrinter(printer_handle, cut_command)
            
            # Tunggu proses selesai
            time.sleep(1)
            
            # Tutup printer dengan benar
            print("Menutup koneksi printer...")
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            printer_handle = None
            
            print("✅ Tiket berhasil dicetak")
            
        except Exception as e:
            logger.error(f"Error printing ticket: {str(e)}")
            print(f"❌ Error saat mencetak tiket: {str(e)}")
            
            # Cleanup jika terjadi error
            if printer_handle:
                try:
                    win32print.EndPagePrinter(printer_handle)
                    win32print.EndDocPrinter(printer_handle)
                    win32print.ClosePrinter(printer_handle)
                except:
                    pass

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
            logger.info("Koneksi ke database berhasil")
            print("✅ Database terkoneksi")
        except Exception as e:
            logger.warning(f"Gagal koneksi ke database: {str(e)}")
            print(f"ℹ️ Mode tanpa database aktif - {str(e)}")
            self.db_conn = None

    def save_to_database(self, ticket_number, image_path):
        """Simpan data tiket ke database"""
        if self.db_conn is None:
            logger.info("Database tidak tersedia, menyimpan data secara lokal saja")
            print("ℹ️ Database tidak digunakan - data disimpan lokal")
            return

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
            print(f"⚠️ Gagal menyimpan ke database: {str(e)}")
            if self.db_conn:
                try:
                    self.db_conn.rollback()
                except:
                    pass
        finally:
            if 'cur' in locals() and cur:
                cur.close()

    def process_button_press(self):
        """Proses ketika tombol ditekan - ambil gambar, cetak tiket, dan simpan ke database"""
        try:
            # Tambah delay kecil untuk stabilisasi
            time.sleep(0.1)  # Kurangi dari 0.2 detik menjadi 0.1 detik untuk stabilisasi kamera
            
            print("\n\nMemproses... Mohon tunggu...\n")
            print("1. Mengambil gambar...")
            logger.info("Mulai proses capture gambar")
            
            # Cek apakah ada capture yang masih diproses
            current_time = time.time()
            if hasattr(self, 'last_capture_time') and self.last_capture_time:
                time_since_last = current_time - self.last_capture_time
                if time_since_last < 0.5:  # Kurangi dari 1 menjadi 0.5 detik antara capture
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
                time.sleep(0.1)  # Kurangi dari 0.2 detik menjadi 0.1 detik setelah proses
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
            if hasattr(self, 'button'):
                self.button.close()
            if hasattr(self, 'db_conn') and self.db_conn is not None:
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
Mode: Pushbutton (Tanpa Kamera)
Status: Menunggu input dari pushbutton...

        """)
        
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

if __name__ == "__main__":
    try:
        parking = ParkingCamera()
        parking.run()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 