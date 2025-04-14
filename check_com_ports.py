import serial.tools.list_ports

print("Daftar port serial yang tersedia:")
ports = list(serial.tools.list_ports.comports())

if not ports:
    print("Tidak ada port serial yang terdeteksi!")
else:
    for port in ports:
        print(f"{port.device} - {port.description}")
        
print("\nGunakan port yang tersedia di arduino_port.txt")
print("Contoh: echo COM3 > arduino_port.txt") 