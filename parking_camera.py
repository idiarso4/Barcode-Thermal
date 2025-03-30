import cv2
import RPi.GPIO as GPIO
import time
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    filename='parking.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parking_system')

class ParkingCamera:
    def __init__(self):
        # Inisialisasi folder dan file
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.capture_dir = os.path.join(self.base_dir, "capture_images")
        self.counter_file = os.path.join(self.base_dir, "counter.txt")
        
        # Buat folder jika belum ada
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
            logger.info(f"Folder capture dibuat: {self.capture_dir}")
        
        # Setup GPIO
        self.BUTTON_PIN = 18
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Inisialisasi kamera
        self.setup_camera()
        
        # Load counter
        self.load_counter()
        
        logger.info("Sistem parkir berhasil diinisialisasi")

    def setup_camera(self):
        """Inisialisasi kamera dengan mencoba beberapa device"""
        for i in range(4):  # Coba device 0-3
            try:
                self.camera = cv2.VideoCapture(i)
                if self.camera.isOpened():
                    logger.info(f"Kamera berhasil diinisialisasi pada device {i}")
                    # Set resolusi kamera (1920x1080)
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                    return
            except Exception as e:
                logger.error(f"Gagal membuka kamera device {i}: {str(e)}")
        
        raise Exception("Tidak ada kamera yang terdeteksi!")

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

    def capture_image(self):
        """Ambil gambar dari kamera dan simpan"""
        try:
            # Increment counter
            self.counter += 1
            
            # Generate nama file
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"TKT{timestamp}_{str(self.counter).zfill(4)}.jpg"
            filepath = os.path.join(self.capture_dir, filename)
            
            # Ambil beberapa frame untuk stabilisasi kamera
            for _ in range(5):
                ret, frame = self.camera.read()
                time.sleep(0.1)
            
            # Ambil dan simpan gambar
            ret, frame = self.camera.read()
            if ret:
                cv2.imwrite(filepath, frame)
                logger.info(f"Gambar berhasil disimpan: {filename}")
                print(f"\n✅ Gambar disimpan: {filename}")
                
                # Simpan counter baru
                self.save_counter()
                return True, filename
            else:
                logger.error("Gagal mengambil gambar dari kamera")
                return False, None
                
        except Exception as e:
            logger.error(f"Error saat capture gambar: {str(e)}")
            return False, None

    def check_storage(self):
        """Cek kapasitas storage"""
        try:
            total, used, free = shutil.disk_usage(self.base_dir)
            free_gb = free // (2**30)  # Convert to GB
            if free_gb < 1:
                logger.warning(f"Storage tersisa kurang dari 1GB: {free_gb}GB")
                print(f"\n⚠️ Peringatan: Storage tersisa {free_gb}GB")
            return free_gb
        except Exception as e:
            logger.error(f"Error checking storage: {str(e)}")
            return None

    def cleanup(self):
        """Bersihkan resources"""
        try:
            self.camera.release()
            GPIO.cleanup()
            logger.info("Cleanup berhasil")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def run(self):
        """Main loop program"""
        print("""
================================
    SISTEM PARKIR RSI BNA    
================================
Mode: Push Button + Camera (Lokal)
Status: Menunggu kendaraan...
        """)
        
        try:
            while True:
                # Baca status button
                if GPIO.input(self.BUTTON_PIN) == GPIO.LOW:  # Button ditekan
                    print("\nMemproses... Mohon tunggu...")
                    success, filename = self.capture_image()
                    
                    if success:
                        print("Status: Menunggu kendaraan berikutnya...")
                    else:
                        print("❌ Gagal mengambil gambar!")
                        
                    # Tunggu button dilepas
                    while GPIO.input(self.BUTTON_PIN) == GPIO.LOW:
                        time.sleep(0.1)
                    
                    # Delay untuk debounce
                    time.sleep(0.5)
                
                # Delay kecil untuk mengurangi CPU usage
                time.sleep(0.1)
                
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