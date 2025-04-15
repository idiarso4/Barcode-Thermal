import requests
import json
import logging
import os
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter

# Setup logging
logging.basicConfig(
    filename='api_integration.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api_integration')

class ParkingIntegration:
    def __init__(self):
        self.base_url = "http://192.168.2.6:5051/api"
        self.offline_file = "offline_data.json"
        self.counter_file = "counter.txt"
        
    def test_connection(self):
        """Test connection to the server API"""
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
    
    def process_vehicle(self, plate_number, vehicle_type="Motor"):
        """Process vehicle entry"""
        try:
            # Send data to server
            data = {
                "plat": plate_number,
                "vehicleType": vehicle_type,
                "vehicleTypeId": 2 if vehicle_type.lower() == "motor" else 1,
                "isParked": True
            }
            
            logger.debug(f"Sending data to server: {json.dumps(data)}")
            
            response = requests.post(
                f"{self.base_url}/masuk",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.ok:
                result = response.json()
                logger.info(f"Server response: {json.dumps(result)}")
                if result.get('success'):
                    ticket_data = {
                        'tiket': result['data']['ticket'],
                        'plat': plate_number,
                        'waktu': result['data']['waktu']
                    }
                    return True, ticket_data
                else:
                    logger.error(f"Server error: {result.get('message')}")
                    return False, result.get('message', 'Unknown error')
            else:
                logger.error(f"Server error: {response.status_code} - {response.text}")
                return False, f"Server error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error processing vehicle: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def create_ticket_image(self, data):
        """Create an image of the ticket for preview"""
        # Create image with white background
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
            
            # Display info about where the image was saved
            print(f"\nTicket image saved to {image_path}")
            
            return image

        except Exception as e:
            logger.error(f"Error creating ticket image: {str(e)}")
            print(f"Error creating ticket image: {str(e)}")
            return None

def main():
    client = ParkingIntegration()
    print("""
==================================================
     SISTEM PARKIR RSI BANJARNEGARA - API MODE       
==================================================
Mode: Manual Input (Simulasi)
    """)
    
    # Tes koneksi API
    is_connected, data = client.test_connection()
    if is_connected:
        print("✅ Terhubung ke server")
        if data and 'total_kendaraan' in data:
            print(f"📊 Jumlah kendaraan: {data['total_kendaraan']}")
    else:
        print("❌ Tidak dapat terhubung ke server.")
        print(f"Error: {data.get('message', 'Unknown error')}")
        return

    print("\nSiap memproses kendaraan...")
    
    try:
        while True:
            print("\n1. Proses kendaraan baru")
            print("2. Test koneksi")
            print("3. Keluar")
            choice = input("\nPilih menu (1-3): ")
            
            if choice == "1":
                plate = input("\nMasukkan nomor plat (atau tekan Enter untuk nomor acak): ")
                if not plate:
                    plate = f"SIM{datetime.now().strftime('%H%M%S')}"
                    print(f"Menggunakan nomor plat otomatis: {plate}")
                
                vehicle_type = input("Jenis kendaraan (Motor/Mobil, default=Motor): ").strip() or "Motor"
                
                print(f"\nMemproses kendaraan dengan plat {plate}...")
                success, result = client.process_vehicle(plate, vehicle_type)
                
                if success:
                    print("\n✅ Tiket Berhasil Dibuat:")
                    print(f"Nomor Tiket : {result['tiket']}")
                    print(f"Nomor Plat  : {result['plat']}")
                    print(f"Waktu Masuk : {result['waktu']}")
                    
                    # Create and save ticket image
                    ticket_image = client.create_ticket_image(result)
                else:
                    print(f"\n❌ Gagal: {result}")
            
            elif choice == "2":
                print("\nMengecek koneksi ke server...")
                is_connected, data = client.test_connection()
                if is_connected:
                    print("✅ Terhubung ke server")
                    if data and 'total_kendaraan' in data:
                        print(f"📊 Jumlah kendaraan: {data['total_kendaraan']}")
                else:
                    print("❌ Tidak dapat terhubung ke server.")
                    print(f"Error: {data.get('message', 'Unknown error')}")
            
            elif choice == "3":
                print("\nMenutup aplikasi...")
                break
            
            else:
                print("\n❌ Pilihan tidak valid. Silakan pilih 1-3.")
                
    except KeyboardInterrupt:
        print("\nProgram dihentikan...")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 