import serial.tools.list_ports
import serial
import time
import os
import sys

def check_arduino():
    print("Checking available ports...")
    ports = [p.device for p in serial.tools.list_ports.comports()]
    print(f"Available ports: {ports}")
    
    # Jika COM7 terdeteksi, langsung gunakan
    if 'COM7' in ports:
        print("\nCOM7 ditemukan, langsung menggunakan port ini...")
        try:
            ser = serial.Serial('COM7', 9600, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
            
            # Simpan port untuk digunakan nanti
            with open("arduino_port.txt", "w") as f:
                f.write("COM7")
                
            ser.close()
            print("✅ Arduino disiapkan di port COM7")
            return True
        except Exception as e:
            print(f"❌ Error saat menggunakan COM7: {str(e)}")
    
    if not ports:
        print("No ports found. Please check Arduino connection.")
        
        # Check for force dummy mode
        if "--force-dummy" in sys.argv:
            print("\n⚠️ MENGGUNAKAN MODE DUMMY (TANPA ARDUINO) ⚠️")
            print("Mode ini hanya untuk testing. Beberapa fitur mungkin tidak berfungsi.")
            # Create dummy file to indicate dummy mode
            with open("dummy_arduino.flag", "w") as f:
                f.write("dummy_mode=True\n")
                f.write(f"timestamp={time.time()}\n")
            return True
        return False
        
    print("\nTrying to connect to each port...")
    arduino_found = False
    arduino_port = None
    
    for port in ports:
        print(f"\nTrying {port}...")
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
            
            # Try to read multiple times
            for _ in range(3):
                if ser.in_waiting:
                    data = ser.readline().decode().strip()
                    print(f"Data received from {port}: {data}")
                    if "READY" in data:
                        print(f"Arduino found on {port}!")
                        # Save port for later use
                        arduino_port = port
                        arduino_found = True
                        break
                time.sleep(1)
                
            ser.close()
            if arduino_found:
                break
            
        except Exception as e:
            print(f"Error on {port}: {str(e)}")
    
    if arduino_found and arduino_port:
        # Save port for later use
        with open("arduino_port.txt", "w") as f:
            f.write(arduino_port)
        return True
    else:
        print("\nNo Arduino found on any port. Please check:")
        print("1. Arduino is connected")
        print("2. Correct port is selected")
        print("3. Arduino is powered on")
        print("4. No other program is using the port")
        
        # Check for force dummy mode
        if "--force-dummy" in sys.argv:
            print("\n⚠️ MENGGUNAKAN MODE DUMMY (TANPA ARDUINO) ⚠️")
            print("Mode ini hanya untuk testing. Beberapa fitur mungkin tidak berfungsi.")
            # Create dummy file to indicate dummy mode
            with open("dummy_arduino.flag", "w") as f:
                f.write("dummy_mode=True\n")
                f.write(f"timestamp={time.time()}\n")
            return True
    
    return arduino_found

if __name__ == "__main__":
    # Pass all command-line arguments to check_arduino
    result = check_arduino()
    # Return success (0) if either Arduino found or dummy mode
    sys.exit(0 if result else 1) 