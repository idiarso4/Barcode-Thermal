import serial
import serial.tools.list_ports
import time
import psycopg2
import sys

def find_arduino_port():
    """Mencari port Arduino yang tersedia"""
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "arduino" in port.description.lower() or "ch340" in port.description.lower():
            return port.device
    return None

# Database connection details
DB_HOST = "192.168.2.6"
DB_PORT = "5432"
DB_NAME = "parkir2"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

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
        print(f"✅ Inserted '{barcode_data}' into the database.")

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection error: {e}")
        print(f"Check if PostgreSQL server is running at {DB_HOST}:{DB_PORT} and accepting remote connections.")
    except Exception as e:
        print(f"❌ Error inserting into database: {e}")
    finally:
        # Close the database connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main():
    print("\n=== Parking System (Database Only Mode) ===")
    print(f"Database connection details:")
    print(f"Host: {DB_HOST}")
    print(f"Port: {DB_PORT}")
    print(f"Database: {DB_NAME}")
    print(f"User: {DB_USER}")
    
    # Try to find and connect to Arduino
    arduino_port = find_arduino_port()
    arduino = None
    
    if arduino_port:
        try:
            arduino = serial.Serial(arduino_port, 9600, timeout=1)
            print(f"\n✅ Arduino terdeteksi pada port {arduino_port}")
        except Exception as e:
            print(f"\n❌ Gagal koneksi ke Arduino: {e}")
            arduino = None
    else:
        print("\n❌ Arduino tidak ditemukan")
        print("ℹ️ Anda dapat memasukkan data secara manual")
    
    print("\nMenunggu input data...")
    
    while True:
        try:
            if arduino and arduino.is_open:
                # Mode Arduino
                if arduino.in_waiting > 0:
                    received_data = arduino.readline().decode('utf-8').strip()
                    if received_data:
                        print(f"\nMenerima data dari Arduino: {received_data}")
                        insert_into_database(received_data)
            else:
                # Mode manual input
                data = input("\nMasukkan data (atau 'exit' untuk keluar): ")
                if data.lower() == 'exit':
                    break
                if data:
                    insert_into_database(data)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    try:
        main()
    finally:
        # Clean up resources
        pass