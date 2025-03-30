import serial
import win32print
import time
import psycopg2
import sys

# Open the serial connection to the Arduino
arduino = serial.Serial('COM7', 9600, timeout=1)

# Database connection details
DB_HOST = "192.168.2.6"
DB_PORT = "5432"
DB_NAME = "parkir2"
DB_USER = "postgres"
DB_PASSWORD = "postgres"  # Corrected password

def print_barcode(barcode_data):
    try:
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

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

        win32print.WritePrinter(printer_handle, esc_pos_commands)

        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode printed successfully!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        if 'printer_handle' in locals():
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
        print(f"Database connection error: {e}")
        print(f"Check if PostgreSQL server is running at {DB_HOST}:{DB_PORT} and accepting remote connections.")
    except Exception as e:
        print(f"Error inserting into database: {e}")
    finally:
        # Close the database connection
        if cursor:
            cursor.close()
        if connection:
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