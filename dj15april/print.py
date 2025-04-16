import serial
import time
import win32print  # For Windows printing

# Open the serial connection to the Arduino
arduino = serial.Serial('COM3', 9600, timeout=1)

def generate_and_print_barcode(barcode_data):
    try:
        # Get the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

        # Open the printer
        printer_handle = win32print.OpenPrinter(printer_name)

        # Start a print job
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Barcode Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)

        # ESC/POS commands for barcode printing
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"Testing Text\n" +    # Plain text for testing
            b"\x1D\x6B\x49" +      # Barcode type: Code 128
            barcode_data.encode() + b"\x00" +  # Barcode data (null-terminated)
            b"\x0A" +              # Line feed (new line)
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # Send the ESC/POS commands to the printer
        win32print.WritePrinter(printer_handle, esc_pos_commands)

        # End the print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode printed successfully!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        # Close the printer handle
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")
def main():
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received number: {received_data}")

                    # Generate and print the barcode using the received number
                    generate_and_print_barcode(received_data)

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


----------------------------------------------------------||--------------------------------------------------------------------

import serial
import win32print  # For Windows printing
import time
import psycopg2  # For PostgreSQL database interaction

# Open the serial connection to the Arduino
arduino = serial.Serial('COM3', 9600, timeout=1)

# Database connection details
DB_HOST = "localhost"
DB_NAME = "your_database_name"  # Replace with your database name
DB_USER = "postgres"           # Replace with your username
DB_PASSWORD = "password"       # Replace with your password

def print_barcode(barcode_data):
    try:
        # Get the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

        # Open the printer
        printer_handle = win32print.OpenPrinter(printer_name)

        # Start a print job
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Barcode Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)

        # ESC/POS commands for barcode printing
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"\x1B\x61\x01" +      # Center alignment
            f"Barcode: {barcode_data}\n".encode() +  # Label for clarity
            b"\x1D\x6B\x49" +      # Barcode type: Code 128
            barcode_data.encode() + b"\x00" +  # Barcode data (null-terminated)
            b"\x0A" +              # Line feed (new line)
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # Send the ESC/POS commands to the printer
        win32print.WritePrinter(printer_handle, esc_pos_commands)

        # End the print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode printed successfully!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        # Close the printer handle
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")

def insert_into_database(barcode_data):
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()

        # Insert the barcode data into the "vehicle" table
        query = "INSERT INTO vehicle (vehicle_entry) VALUES (%s);"
        cursor.execute(query, (barcode_data,))

        # Commit the transaction
        connection.commit()
        print(f"Inserted '{barcode_data}' into the database.")

    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        # Close the database connection
        if connection:
            cursor.close()
            connection.close()

def main():
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received data from Arduino: {received_data}")

                    # Step 1: Print the barcode
                    print_barcode(received_data)

                    # Step 2: Insert the data into the PostgreSQL database
                    insert_into_database(received_data)

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


-------------------------------------------------------||||------------------------------------------------------------------------

import serial
import win32print 
import time
import psycopg2  

# Open the serial connection to the Arduino
arduino = serial.Serial('COM4', 9600, timeout=1)

# Database connection details
DB_HOST = "localhost"
DB_NAME = "rsibna"  
DB_USER = "postgres"          
DB_PASSWORD = "password"       

def print_barcode(barcode_data):
    try:
        
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing ke: {printer_name}")

        
        printer_handle = win32print.OpenPrinter(printer_name)

        
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Barcode Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)

        
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"\x1B\x61\x01" +      # Center alignment
            f"Barcode: {barcode_data}\n".encode() +  # Label for clarity
            b"\x1D\x6B\x49" +      # Barcode type: Code 128
            barcode_data.encode() + b"\x00" +  # Barcode data (null-terminated)
            b"\x0A" +              # Line feed (new line)
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # kirim ESC/POS commands  printer
        win32print.WritePrinter(printer_handle, esc_pos_commands)

        # sudah ngeprint
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode sudah di print!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        # Close the printer handle
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")

def insert_into_database(barcode_data):
    try:
        # konek ke PostgreSQL database
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()

        # Memasukan e barcode data ke tabel "kendaraan" 
        query = "INSERT INTO kendaraan (vehicle_entry) VALUES (%s);"
        cursor.execute(query, (barcode_data,))

        # Commit the transaction
        connection.commit()
        print(f"Inserted '{barcode_data}' into the database.")

    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        # Close the database connection
        if connection:
            cursor.close()
            connection.close()

def main():
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received data from Arduino: {received_data}")

                    # Step 1: Print the barcode
                    print_barcode(received_data)

                    # Step 2: Insert the data into the PostgreSQL database
                    insert_into_database(received_data)

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
