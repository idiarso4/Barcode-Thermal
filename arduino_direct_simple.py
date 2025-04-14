import serial
import time
import os
from datetime import datetime
import logging
import win32print

# Coba import psycopg2, jika tidak ada gunakan dummy
try:
    import psycopg2
    from psycopg2 import Error
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    print("⚠️ Database PostgreSQL tidak tersedia (psycopg2 tidak terinstal)")
    print("   Fitur database dinonaktifkan")
    print("   Jalankan: pip install psycopg2-binary untuk mengaktifkan fitur database")

# Setup logging
logging.basicConfig(
    filename='arduino_simple.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('arduino_simple')

class ArduinoHandler:
    def __init__(self):
        # Inisialisasi variable
        self.counter = 1  # Untuk nomor urut tiket
        self.last_button_press = 0
        self.debounce_delay = 0.1  # Kurangi menjadi 0.1 detik untuk lebih responsif
        self.printer_available = False
        self.printer_name = None
        self.db_conn = None
        
        # Setup button dan printer
        print("\n=== SISTEM TIKET ARDUINO SIMPLE ===\n")
        self.setup_button()
        self.setup_printer()
        self.setup_database()
        
    def setup_button(self):
        """Setup koneksi ke Arduino melalui serial"""
        try:
            # Cek apakah ada file arduino_port.txt dan baca port yang tersimpan
            if os.path.exists("arduino_port.txt"):
                with open("arduino_port.txt", "r") as f:
                    saved_port = f.read().strip()
                port = saved_port
            else:
                port = "COM7"  # Default port
            
            print(f"\nMencoba koneksi ke Arduino di port {port}...")
            
            try:
                self.button = serial.Serial(
                    port=port,
                    baudrate=9600,
                    timeout=0.1
                )
                
                # Tunggu Arduino siap
                time.sleep(2)
                
                # Bersihkan buffer
                self.button.reset_input_buffer()
                self.button.reset_output_buffer()
                
                # Kirim beberapa perintah test ke Arduino
                print("Mengirim perintah test ke Arduino...")
                self.button.write(b'test\n')
                time.sleep(0.1)
                if self.button.in_waiting:
                    response = self.button.read_all().decode(errors='ignore').strip()
                    print(f"  Respons: {repr(response)}")
                
                # Kirim perintah debug mode
                self.button.write(b'debug\n')
                time.sleep(0.1)
                if self.button.in_waiting:
                    response = self.button.read_all().decode(errors='ignore').strip()
                    print(f"  Respons debug: {repr(response)}")
                
                print(f"✅ Arduino terhubung di port {port}")
                print("ℹ️ Tekan tombol dengan mantap selama 0.5-1 detik")
                print("ℹ️ Atau tekan tombol '1' pada keyboard untuk testing")
                return
                
            except Exception as e:
                print(f"❌ Gagal koneksi ke port {port}: {str(e)}")
                raise Exception(f"Gagal koneksi ke Arduino: {str(e)}")
                
        except Exception as e:
            logger.error(f"Gagal setup Arduino: {str(e)}")
            raise Exception(f"Gagal setup Arduino: {str(e)}")

    def check_button(self):
        """Cek status button dengan debounce dan toleransi"""
        try:
            # Tambahan keyboard input untuk testing
            try:
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore')
                    current_time = time.time()
                    
                    if key == '1':  # Tombol '1' pada keyboard
                        if current_time - self.last_button_press >= self.debounce_delay:
                            self.last_button_press = current_time
                            print("\n✅ Tombol keyboard '1' terdeteksi - memproses...")
                            logger.info("Tombol keyboard '1' terdeteksi")
                            return True
            except:
                pass  # Abaikan jika msvcrt tidak tersedia
            
            # Polling aktif ke Arduino setiap 1 detik
            if not hasattr(self, '_last_poll_time'):
                self._last_poll_time = 0
                
            if time.time() - self._last_poll_time > 1:
                try:
                    # Kirim perintah untuk meningkatkan kemungkinan respon
                    self.button.write(b'check\n')
                    time.sleep(0.1)
                    self._last_poll_time = time.time()
                except:
                    pass

            # Baca data dari Arduino
            if self.button.in_waiting:
                # Baca semua data yang tersedia di buffer
                data = self.button.read_all().decode(errors='ignore').strip()
                current_time = time.time()
                
                # Debug log dan tampilkan data mentah
                if data:
                    print(f"\nData dari Arduino: {repr(data)}")
                    logger.debug(f"Data tombol diterima: {repr(data)}")
                
                # Cek apakah sudah melewati waktu debounce
                if current_time - self.last_button_press >= self.debounce_delay:
                    # Cek lebih banyak kemungkinan input valid
                    if (any(str(x) in data for x in range(1, 10)) or 
                        any(x in data for x in ['1', 'true', 'True', 'HIGH', 'Ready', 'READY', 'on', 'ON']) or
                        data.strip()):  # Terima data apapun, tidak kosong
                        
                        self.last_button_press = current_time
                        print("\n✅ Tombol Arduino terdeteksi - memproses...")
                        logger.info(f"Tombol terdeteksi dengan data: {repr(data)}")
                        return True
                else:
                    # Jika masih dalam masa debounce, tampilkan sisa waktu
                    remaining = self.debounce_delay - (current_time - self.last_button_press)
                    if data:  # Hanya tampilkan jika ada aktivitas tombol
                        print(f"\n⏳ Mohon tunggu {remaining:.1f} detik lagi...\n")
                        logger.debug(f"Tombol dalam debounce, sisa waktu: {remaining:.1f}s")
                        
            return False
        except Exception as e:
            logger.error(f"Error membaca button: {str(e)}")
            print(f"⚠️ Error membaca button: {str(e)}")
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
            
        except Exception as e:
            logger.error(f"Setup printer error: {str(e)}")
            print(f"\n❌ Setup printer error: {str(e)}")
            self.printer_available = False

    def print_ticket(self, ticket_number):
        """Cetak tiket dengan barcode CODE39"""
        try:
            if not self.printer_available:
                print("❌ Printer tidak tersedia")
                return
                
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\nMencetak tiket:")
            print(f"Nomor: {ticket_number}")
            print(f"Waktu: {timestamp}")
            
            # Gunakan metode alternatif via file yang terbukti berhasil
            try:
                print("Menggunakan metode cetak file...")
                
                # Buat file temporer dengan perintah ESC/POS
                temp_file = "temp_ticket.prn"
                with open(temp_file, "wb") as f:
                    # Initialize printer
                    f.write(b"\x1B\x40")  # Initialize printer
                    f.write(b"\x1B\x61\x01")  # Center alignment
                    
                    # Header - double height & width
                    f.write(b"\x1B\x21\x30")  # Double width & height
                    f.write(b"RSI BANJARNEGARA\n")
                    f.write(b"TIKET PARKIR\n")
                    f.write(b"\x1B\x21\x00")  # Normal text
                    f.write(b"================================\n")
                    
                    # Ticket details - left align, normal text
                    f.write(b"\x1B\x61\x00")  # Left alignment
                    f.write(f"Nomor : {ticket_number}\n".encode())
                    f.write(f"Waktu : {timestamp}\n".encode())
                    f.write(b"================================\n")
                    
                    # Barcode section - optimized for thermal printer
                    f.write(b"\x1D\x48\x02")  # HRI below barcode
                    f.write(b"\x1D\x68\x50")  # Barcode height = 80 dots
                    f.write(b"\x1D\x77\x02")  # Barcode width = 2
                    f.write(b"\x1B\x61\x01")  # Center alignment
                    
                    # Use CODE39 with clear format
                    f.write(b"\x1D\x6B\x04")  # Select CODE39
                    
                    # Simplify ticket number for better scanning
                    simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number  # Ambil hanya nomor urut
                    barcode_data = f"*{simple_number}*".encode()  # Format CODE39
                    f.write(barcode_data)
                    
                    # Extra space after barcode
                    f.write(b"\n\n")
                    
                    # Footer - center align
                    f.write(b"\x1B\x61\x01")  # Center alignment
                    f.write(b"Terima kasih\n")
                    f.write(b"Jangan hilangkan tiket ini\n")
                    
                    # Feed and cut
                    f.write(b"\x1B\x64\x05")  # Feed 5 lines
                    f.write(b"\x1D\x56\x41\x00")  # Cut paper
                
                # Kirim file ke printer menggunakan command line
                print(f"Mengirim file ke printer: {self.printer_name}")
                os.system(f'copy /b "{temp_file}" "{self.printer_name}"')
                
                print("✅ File berhasil dikirim ke printer")
                
                # Hapus file temporer setelah selesai
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
                print("✅ Tiket berhasil dicetak")
                return
                
            except Exception as e:
                print(f"❌ Gagal mencetak dengan metode file: {str(e)}")
                print("Mencoba metode RAW sebagai fallback...")
            
            # Jika metode file gagal, gunakan metode RAW sebagai fallback
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
                simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number  # Ambil hanya nomor urut
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
        """Setup koneksi ke database PostgreSQL"""
        if not HAS_POSTGRES:
            logger.warning("Koneksi database dilewati - psycopg2 tidak terinstal")
            return
            
        try:
            print("\nMenghubungkan ke database PostgreSQL...")
            
            # Konfigurasi database
            db_config = {
                'dbname': 'postgres',  # Sesuaikan dengan nama database
                'user': 'postgres',     # Sesuaikan dengan username
                'password': 'postgres', # Sesuaikan dengan password
                'host': '192.168.2.6',  # Server PostgreSQL
                'port': '5432'          # Port default PostgreSQL
            }
            
            # Koneksi ke database
            self.db_conn = psycopg2.connect(
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                port=db_config['port']
            )
            
            logger.info("Koneksi ke database berhasil")
            print("✅ Database terkoneksi")
            
        except Exception as e:
            logger.error(f"Gagal koneksi ke database: {str(e)}")
            print(f"❌ Gagal koneksi ke database: {str(e)}")
            print("   Mode database dinonaktifkan")
            self.db_conn = None
    
    def save_to_database(self, ticket_number):
        """Simpan data tiket ke database"""
        if not self.db_conn:
            logger.warning("Database tidak tersedia, tiket tidak disimpan")
            return
            
        try:
            cur = self.db_conn.cursor()
            
            # Data untuk tiket
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_path = f"dummy_path_{ticket_number}.jpg"  # Path dummy untuk testing
            
            # Query untuk insert data
            sql = """
            INSERT INTO public."CaptureTickets" 
            ("TicketNumber", "ImagePath", "Timestamp") 
            VALUES (%s, %s, %s)
            """
            
            # Eksekusi query
            cur.execute(sql, (ticket_number, image_path, timestamp))
            self.db_conn.commit()
            
            logger.info(f"Data tiket {ticket_number} berhasil disimpan ke database")
            print("✅ Data tersimpan di database")
            
        except Exception as e:
            logger.error(f"Gagal menyimpan ke database: {str(e)}")
            print(f"❌ Gagal menyimpan ke database: {str(e)}")
            if self.db_conn:
                self.db_conn.rollback()
        finally:
            if 'cur' in locals():
                cur.close()
    
    def process_button_press(self):
        """Proses ketika tombol ditekan - cetak tiket"""
        try:
            # Tambah delay kecil untuk stabilisasi
            time.sleep(0.2)
            
            print("\n\nMemproses... Mohon tunggu...\n")
            logger.info("Mulai proses pencetakan tiket")
            
            # Buat nomor tiket
            ticket_time = datetime.now().strftime("%Y%m%d%H%M%S")
            ticket_number = f"TKT{ticket_time}_{self.counter:04d}"
            self.counter += 1
            
            # Coba simpan ke database
            if HAS_POSTGRES and self.db_conn:
                print("Menyimpan ke database PostgreSQL...")
                self.save_to_database(ticket_number)
            
            # Cetak tiket jika printer tersedia
            if self.printer_available:
                self.print_ticket(ticket_number)
            else:
                print("\n❌ Printer tidak tersedia, tiket tidak bisa dicetak")
            
            print("\n\nStatus: Menunggu input berikutnya...\n")
            logger.info("Proses cetak selesai")
                
        except Exception as e:
            logger.error(f"Error dalam process_button_press: {str(e)}")
            print(f"\n❌ Error saat memproses: {str(e)}\n")
            
    def cleanup(self):
        """Bersihkan resources"""
        try:
            if hasattr(self, 'button'):
                self.button.close()
            if hasattr(self, 'db_conn') and self.db_conn:
                self.db_conn.close()
                logger.info("Koneksi database ditutup")
            logger.info("Cleanup berhasil")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def run(self):
        """Main loop program"""
        print("""
================================
      TIKET PARKIR SISTEM    
================================
Status: Menunggu input dari Arduino...

        """)
        
        try:
            while True:
                if self.check_button():  # Button ditekan
                    self.process_button_press()
                
                # Delay kecil untuk mengurangi CPU usage
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    try:
        handler = ArduinoHandler()
        handler.run()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 