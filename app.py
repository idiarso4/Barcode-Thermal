import serial
import barcode
from barcode.writer import ImageWriter
import os
import win32print  # For Windows printing
import time
import requests
import json
from datetime import datetime

# Server API Configuration
API_BASE_URL = "http://192.168.2.6:5051/api"
OFFLINE_DATA_FILE = "offline_data.json"

# Open the serial connection to the Arduino
arduino = serial.Serial('COM4', 9600, timeout=1)

def save_offline_data(data):
    try:
        existing_data = []
        if os.path.exists(OFFLINE_DATA_FILE):
            with open(OFFLINE_DATA_FILE, 'r') as f:
                existing_data = json.load(f)
        
        existing_data.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data
        })
        
        with open(OFFLINE_DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
    except Exception as e:
        print(f"Error saving offline data: {e}")

def send_to_server(plat_nomor, jenis="Motor"):
    try:
        # Test server connection first
        response = requests.get(f"{API_BASE_URL}/test")
        if not response.ok:
            raise Exception("Server not available")

        # Send vehicle entry data
        data = {
            "plat": plat_nomor,
            "jenis": jenis
        }
        
        response = requests.post(
            f"{API_BASE_URL}/masuk",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.ok:
            result = response.json()
            if result.get('success'):
                return result['data']['ticket']
            else:
                raise Exception(result.get('message', 'Unknown error'))
        else:
            raise Exception(f"Server error: {response.status_code}")
            
    except Exception as e:
        print(f"Error sending to server: {e}")
        # Save data for offline processing
        save_offline_data({"plat": plat_nomor, "jenis": jenis})
        # Generate offline ticket as fallback
        return f"OFF{int(time.time())%10000:04d}"

def generate_and_print_barcode(barcode_data):
    temp_file = "temp_barcode"
    barcode_file = f"{temp_file}.png"
    printer_handle = None

    try:
        # Generate a barcode image (Code 128 format)
        barcode_format = barcode.get_barcode_class('code128')
        barcode_image = barcode_format(barcode_data, writer=ImageWriter())

        # Save the barcode image to a temporary file
        barcode_image.save(temp_file)

        # Print the barcode using the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

        printer_handle = win32print.OpenPrinter(printer_name)
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Barcode Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)

        with open(barcode_file, "rb") as f:
            raw_data = f.read()
            win32print.WritePrinter(printer_handle, raw_data)

        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode printed successfully!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        # Clean up resources
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")

        # Clean up the temporary file
        if os.path.exists(barcode_file):
            try:
                os.remove(barcode_file)
            except Exception as e:
                print(f"Error deleting temporary file: {e}")

def process_vehicle_entry(plat_nomor):
    try:
        # Get ticket number from server
        ticket = send_to_server(plat_nomor)
        print(f"Generated ticket: {ticket}")
        
        # Generate and print barcode
        generate_and_print_barcode(ticket)
        
        return True
    except Exception as e:
        print(f"Error processing vehicle entry: {e}")
        return False

def main():
    print("Starting parking system client...")
    print(f"Connecting to server at {API_BASE_URL}")
    
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received plate number: {received_data}")
                    process_vehicle_entry(received_data)

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    try:
        main()
    finally:
        if arduino.is_open:
            arduino.close()