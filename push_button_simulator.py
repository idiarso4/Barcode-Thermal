import requests
import json
import logging
import os
import time
import random
import keyboard
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter

# Setup logging
logging.basicConfig(
    filename='button_simulator.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('button_simulator')

class PushButtonSimulator:
    def __init__(self):
        self.base_url = "http://192.168.2.6:5051/api"
        self.capture_dir = "capture_images"
        
        # Create capture directory if it doesn't exist
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
    
    def test_connection(self):
        """Test connection to the server"""
        try:
            response = requests.get(f"{self.base_url}/test")
            if response.ok:
                data = response.json()
                return True, data
            else:
                logger.error(f"Server error: {response.status_code} - {response.text}")
                return False, {"message": f"Error: {response.status_code}"}
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False, {"message": f"Connection error: {str(e)}"}
    
    def generate_random_plate(self):
        """Generate a random plate number"""
        # Generate random plate number in the format 'ABCD123'
        letters = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=2))
        numbers = ''.join(random.choices('0123456789', k=4))
        return f"{letters}{numbers}"
            
    def capture_image(self):
        """Simulate capturing an image from camera"""
        # In a real system, this would capture from a camera
        # We're creating a dummy image with timestamp
        
        width, height = 640, 480
        image = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # Draw a simulated vehicle
        draw.rectangle((100, 200, 540, 400), fill=(60, 60, 60))  # Car body
        draw.rectangle((150, 150, 490, 200), fill=(70, 70, 70))  # Car top
        draw.ellipse((120, 350, 200, 430), fill=(30, 30, 30))  # Wheel
        draw.ellipse((440, 350, 520, 430), fill=(30, 30, 30))  # Wheel
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            
        draw.text((10, 10), timestamp, fill=(255, 0, 0), font=font)
        draw.text((10, 40), "RSI BNA CCTV", fill=(0, 0, 255), font=font)
        
        # Generate a unique filename with timestamp
        filename = f"{self.capture_dir}/vehicle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        image.save(filename)
        
        return filename
        
    def process_button_press(self):
        """Process a button press - capture image and send to server"""
        print("\n⏳ Memproses kendaraan...")
        
        try:
            # 1. Capture image
            print("📸 Mengambil gambar kendaraan...")
            image_path = self.capture_image()
            print(f"✅ Gambar disimpan: {image_path}")
            
            # 2. Generate plate number (in real system, might use OCR)
            plate = self.generate_random_plate()
            print(f"🔢 Nomor plat: {plate}")
            
            # 3. Send data to server
            print("🔄 Mengirim data ke server...")
            
            data = {
                "plat": plate,
                "vehicleType": "Motor",
                "vehicleTypeId": 2,
                "isParked": True
            }
            
            response = requests.post(
                f"{self.base_url}/masuk",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.ok:
                result = response.json()
                if result.get('success'):
                    print("\n✅ KENDARAAN BERHASIL MASUK")
                    print(f"🎫 Nomor Tiket : {result['data']['ticket']}")
                    print(f"🚗 Nomor Plat  : {plate}")
                    print(f"🕒 Waktu Masuk : {result['data']['waktu']}")
                    
                    # Create and save ticket image
                    self.create_ticket_image({
                        'tiket': result['data']['ticket'],
                        'plat': plate,
                        'waktu': result['data']['waktu']
                    })
                    
                    # Print ticket (simulated)
                    print("\n🖨️ Mencetak tiket...")
                    time.sleep(1)  # Simulate printing time
                    print("✅ Tiket berhasil dicetak")
                    
                    return True
                else:
                    print(f"\n❌ GAGAL: {result.get('message', 'Kesalahan tidak diketahui')}")
                    return False
            else:
                print(f"\n❌ GAGAL: Kesalahan server {response.status_code}")
                return False
                
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            logger.error(f"Error processing button press: {str(e)}")
            return False
    
    def create_ticket_image(self, data):
        """Create a ticket image"""
        width = 400
        height = 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to load a nice font, fallback to default if not found
            try:
                font_header = ImageFont.truetype("arial.ttf", 24)
                font_normal = ImageFont.truetype("arial.ttf", 20) 
            except:
                font_header = ImageFont.load_default()
                font_normal = ImageFont.load_default()

            # Header
            draw.text((width//2, 20), "RSI BANJARNEGARA", font=font_header, fill='black', anchor='mt')
            draw.text((width//2, 50), "================", font=font_header, fill='black', anchor='mt')

            # Ticket details
            draw.text((20, 100), f"TIKET: {data['tiket']}", font=font_normal, fill='black')
            draw.text((20, 140), f"PLAT : {data['plat']}", font=font_normal, fill='black')
            draw.text((20, 180), f"WAKTU: {data['waktu']}", font=font_normal, fill='black')

            # Generate barcode
            barcode_class = barcode.get_barcode_class('code39')
            barcode_instance = barcode_class(data['tiket'], writer=ImageWriter())
            barcode_image = barcode_instance.render()
            
            # Resize barcode to fit ticket width
            barcode_image = barcode_image.resize((width-40, 100))
            
            # Paste barcode
            image.paste(barcode_image, (20, 240))
            
            # Save the image to a file in the images directory
            if not os.path.exists('images'):
                os.makedirs('images')
                
            image_path = f"images/ticket_{data['tiket']}.png"
            image.save(image_path)
            logger.info(f"Ticket image saved to {image_path}")
            
            print(f"🖼️ Gambar tiket: {image_path}")
            
        except Exception as e:
            logger.error(f"Error creating ticket image: {str(e)}")
            print(f"❌ Error membuat gambar tiket: {str(e)}")

def main():
    simulator = PushButtonSimulator()
    
    print("""
============================================================
     SISTEM PARKIR RSI BANJARNEGARA - PUSH BUTTON MODE      
============================================================
Mode: Simulasi Push Button (Tekan SPASI untuk menjalankan)
    """)
    
    # Test connection
    is_connected, data = simulator.test_connection()
    if is_connected:
        print("✅ Terhubung ke server")
        if data and 'total_kendaraan' in data:
            print(f"📊 Jumlah kendaraan: {data['total_kendaraan']}")
        
        print("\n🔴 SISTEM SIAP - Tekan SPASI untuk memproses kendaraan masuk")
        print("⚠️  Tekan ESC untuk keluar dari program")
        
        # Register keyboard events
        keyboard.on_press_key('space', lambda _: simulator.process_button_press())
        keyboard.wait('esc')  # Wait until ESC is pressed
        
        print("\n🛑 Program dihentikan")
    else:
        print("❌ Tidak dapat terhubung ke server!")
        print(f"Error: {data.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main() 