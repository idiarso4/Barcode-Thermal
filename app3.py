import serial
import win32print 
import time
import psycopg2
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='parking_app.log'
)
logger = logging.getLogger(__name__)

# Open the serial connection to the Arduino
arduino = serial.Serial('COM7', 9600, timeout=1)

# Database connection details
DB_HOST = "192.168.2.6"
DB_PORT = "5432"
DB_NAME = "parkir2"  
DB_USER = "postgres"          
DB_PASSWORD = "postgres"       

def print_barcode(barcode_data):
    try:
        printer_name = win32print.GetDefaultPrinter()
        logger.info(f"Printing to: {printer_name}")
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

        logger.info("Barcode printed successfully!")
        print("Barcode printed successfully!")
    except Exception as e:
        logger.error(f"Error printing barcode: {e}")
        print(f"Error printing barcode: {e}")
    finally:
        if 'printer_handle' in locals():
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                logger.error(f"Error closing printer handle: {e}")
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

        # Generate ticket number
        ticket_number = f"PK-{time.strftime('%Y%m%d%H%M%S')}"

        # Insert vehicle data
        query = """
            INSERT INTO vehicles 
            (plate_number, vehicle_type, ticket_number) 
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        cursor.execute(query, (barcode_data, 'Motor', ticket_number))
        vehicle_id = cursor.fetchone()[0]

        # Commit the transaction
        connection.commit()
        logger.info(f"Inserted vehicle with ID {vehicle_id} into database")
        print(f"Inserted vehicle with ID {vehicle_id} into database")

        return ticket_number

    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        print(f"Database connection error: {e}")
        print(f"Check if PostgreSQL server is running at {DB_HOST}:{DB_PORT}")
        return None
    except Exception as e:
        logger.error(f"Error inserting into database: {e}")
        print(f"Error inserting into database: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main():
    logger.info("Starting parking system...")
    print("Starting parking system...")
    print("Waiting for vehicle data...")

    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()
                logger.info("Reconnected to Arduino")
                print("Reconnected to Arduino")

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    logger.info(f"Received data from Arduino: {received_data}")
                    print(f"Received data from Arduino: {received_data}")

                    # Step 1: Insert the data into the PostgreSQL database
                    ticket_number = insert_into_database(received_data)
                    
                    if ticket_number:
                        # Step 2: Print the ticket with barcode
                        print_barcode(ticket_number)
                    else:
                        logger.warning("Skipping ticket printing due to database error")
                        print("Skipping ticket printing due to database error")

        except KeyboardInterrupt:
            logger.info("Exiting...")
            print("Exiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main()