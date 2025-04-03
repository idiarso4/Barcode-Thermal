import serial
import time
import sys

# List available ports for debugging
print("Attempting to connect to Arduino...")

# Try a wider range of COM ports
for port_num in range(1, 11):  # Try COM1 through COM10
    port_name = f'COM{port_num}'
    try:
        arduino = serial.Serial(port_name, 9600, timeout=1)
        print(f"Successfully connected to {port_name}")
        break
    except serial.serialutil.SerialException as e:
        print(f"Failed to connect to {port_name}: {e}")
else:  # This runs if the for loop completes without a break
    print("Could not connect to any COM port from COM1 to COM10")
    print("Please check if your Arduino is properly connected")
    sys.exit(1)

print("Connection established, continuing with program...")

# Add functionality from app1.py below this line
# ...

# Main program loop
def main():
    print("Combined application started")
    while True:
        try:
            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()
                if received_data:
                    print(f"Received data from Arduino: {received_data}")
                    # Process the data (add your app1.py processing here)
                    
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