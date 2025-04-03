import serial
import win32print 
import time
import psycopg2
import sys
import serial.tools.list_ports
import qrcode
from PIL import Image
import io

# Open the serial connection to the Arduino
print("Attempting to connect to Arduino...")

def find_arduino_port():
    # Get list of all available ports
    ports = list(serial.tools.list_ports.comports())
    
    # Try to find Arduino by looking for common identifiers
    for port in ports:
        # Check if this is likely an Arduino
        if any(identifier in port.description.lower() for identifier in ['arduino', 'ch340', 'usb serial']):
            try:
                # Try to open the port
                arduino = serial.Serial(port.device, 9600, timeout=1)
                print(f"Found Arduino on {port.device}")
                return arduino
            except serial.SerialException as e:
                print(f"Found Arduino on {port.device} but couldn't open it: {e}")
                print("Please close any other programs that might be using the Arduino")
                continue
    
    # If no Arduino found, try all COM ports
    for port_num in range(1, 11):
        port_name = f'COM{port_num}'
        try:
            arduino = serial.Serial(port_name, 9600, timeout=1)
            print(f"Successfully connected to {port_name}")
            return arduino
        except serial.SerialException as e:
            print(f"Failed to connect to {port_name}: {e}")
            continue
    
    return None

# Try to connect to Arduino
arduino = find_arduino_port()
if arduino is None:
    print("\nCould not connect to Arduino. Please check:")
    print("1. Is the Arduino connected to USB?")
    print("2. Is the correct USB cable being used?")
    print("3. Is the Arduino showing up in Device Manager?")
    print("4. Are any other programs using the Arduino?")
    print("\nTry these steps:")
    print("1. Unplug and replug the Arduino")
    print("2. Close Arduino IDE and other programs")
    print("3. Check Device Manager for the correct COM port")
    print("4. Try running the program as administrator")
    sys.exit(1)

# Database connection details
DB_HOST = "192.168.2.6"
DB_PORT = "5432"
DB_NAME = "parkir2"  
DB_USER = "postgres"          
DB_PASSWORD = "postgres"       

def generate_qr_code(data):
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    qr_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return img_byte_arr

def print_qr_code(qr_data, barcode_data):
    printer_handle = None
    try:
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing ke: {printer_name}")
        
        printer_handle = win32print.OpenPrinter(printer_name)
        
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("QR Code Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # ESC/POS commands for QR code printing
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"\x1B\x61\x01" +      # Center alignment
            b"\x1B\x2A\x21" +      # Set image mode
            b"\x1B\x2A\x00" +      # Set image size
            b"\x1B\x2A\x00" +      # Set image size
            b"\x1B\x2A\x00" +      # Set image size
            b"\x1B\x2A\x00" +      # Set image size
            qr_data +              # QR code image data
            b"\x0A\x0A" +          # Line feeds
            f"Ticket: {barcode_data}\n".encode() +  # Ticket number
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # Send ESC/POS commands to printer
        win32print.WritePrinter(printer_handle, esc_pos_commands)

        # End printing
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("QR Code sudah di print!")
    except Exception as e:
        print(f"Error printing QR code: {e}")
    finally:
        # Close the printer handle
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")

def insert_into_database(barcode_data):
    connection = None
    cursor = None
    try:
        # Connect to PostgreSQL database
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()

        # Insert barcode data into "Vehicles" table
        query = "INSERT INTO Vehicles (Id) VALUES (%s);"
        cursor.execute(query, (barcode_data,))

        # Commit the transaction
        connection.commit()
        print(f"Inserted '{barcode_data}' into the database.")

    except psycopg2.OperationalError as e:
        print(f"Error inserting into database: {e}")
        print(f"Check if PostgreSQL server is running at {DB_HOST}:{DB_PORT} and accepting remote connections")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        # Close the database connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main():
    print("Program QR code started. Waiting for data from Arduino...")
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()
                print("Reconnected to Arduino")

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received data from Arduino: {received_data}")

                    # Generate QR code
                    qr_data = generate_qr_code(received_data)

                    # Step 1: Print the QR code
                    print_qr_code(qr_data, received_data)

                    # Step 2: Insert the data into the PostgreSQL database
                    insert_into_database(received_data)

            time.sleep(0.1)  # Small delay to reduce CPU usage

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            print("Trying to reconnect in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    try:
        main()
    finally:
        if arduino.is_open:
            arduino.close()
            print("Arduino port closed")