import serial
import serial.tools.list_ports
import time

def close_serial_ports():
    print("Checking for open serial ports...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if 'COM7' in port.device:
            print(f"Found {port.description} on {port.device}")
            try:
                ser = serial.Serial(port.device)
                ser.close()
                print(f"Closed connection to {port.device}")
                time.sleep(1)  # Give the port time to fully close
            except Exception as e:
                print(f"Could not close {port.device}: {str(e)}")

if __name__ == "__main__":
    close_serial_ports()
    print("Done checking serial ports") 