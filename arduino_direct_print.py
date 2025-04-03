import serial
import time
import random
import string
import sys
import os

# Serial port configuration
# Try COM7 first, which is reported as the Arduino port
SERIAL_PORTS = ["COM7", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM8", "COM9"]
BAUD_RATE = 9600

def try_connect_serial():
    """Try to connect to printer via serial port"""
    for port in SERIAL_PORTS:
        try:
            print(f"Mencoba koneksi ke port {port}...")
            ser = serial.Serial(port, BAUD_RATE, timeout=2)
            print(f"✅ Terhubung ke port {port}")
            return ser
        except Exception as e:
            print(f"❌ Gagal koneksi ke port {port}: {str(e)}")
    
    print("❌ Tidak dapat menemukan port serial yang aktif")
    return None

def print_ticket_serial(ser, ticket_number, plate_number, timestamp):
    """Print ticket directly via serial port"""
    try:
        if not ser:
            print("❌ Tidak ada koneksi serial")
            return False
            
        print(f"Mencetak tiket via serial port: {ser.port}")
        
        # For longer ticket numbers, use a shortened version for barcode
        barcode_ticket = ticket_number
        if len(ticket_number) > 15 and ticket_number.startswith("TKT"):
            barcode_ticket = ticket_number[-10:]
            print(f"Menggunakan barcode pendek: {barcode_ticket} dari {ticket_number}")
        
        # ESC/POS commands for thermal printer
        commands = bytearray()
        
        # Initialize printer
        commands.extend(b"\x1B\x40")  # ESC @ - Initialize printer
        
        # Center align
        commands.extend(b"\x1B\x61\x01")  # ESC a 1 - Center alignment
        
        # Title with large font
        commands.extend(b"\x1B\x21\x30")  # ESC ! 0x30 - Double width/height
        commands.extend("PARKIR RSI BNA\n".encode('ascii'))
        
        # Normal font
        commands.extend(b"\x1B\x21\x00")  # ESC ! 0x00 - Normal font
        
        # Line separator
        commands.extend("====================\n\n".encode('ascii'))
        
        # Ticket info
        commands.extend(f"TIKET: {ticket_number}\n".encode('ascii'))
        commands.extend(f"PLAT : {plate_number}\n".encode('ascii'))
        commands.extend(f"WAKTU: {timestamp}\n\n".encode('ascii'))
        
        # Barcode (CODE39 format)
        commands.extend(b"\x1D\x48\x02")  # GS H 2 - HRI below barcode
        commands.extend(b"\x1D\x68\x50")  # GS h 80 - Barcode height 80 dots
        commands.extend(b"\x1D\x77\x02")  # GS w 2 - Barcode width (multiplier 2)
        commands.extend(b"\x1D\x6B\x04")  # GS k 4 - CODE39 barcode
        
        # Barcode data
        commands.append(len(barcode_ticket))  # Length byte
        commands.extend(barcode_ticket.encode('ascii'))  # Barcode data
        
        # Footer
        commands.extend(b"\n\n")
        commands.extend("Terima kasih\nJangan hilangkan tiket ini\n\n".encode('ascii'))
        
        # Cut paper
        commands.extend(b"\x1D\x56\x42")  # GS V B - Cut paper
        
        # Send commands to printer via serial port
        ser.write(commands)
        ser.flush()
        
        # Wait for printing to complete
        time.sleep(1)
        
        print("✅ Berhasil mengirim perintah cetak")
        return True
        
    except Exception as e:
        print(f"❌ Gagal mencetak via serial: {str(e)}")
        return False

def generate_test_data():
    """Generate test data for printing test"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    plate = f"{letters}{numbers}"
    
    # Generate random ticket number
    ticket = f"TST{random.randint(1000, 9999)}"
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return ticket, plate, timestamp

def print_test(ser):
    """Run a simple print test"""
    # Generate test data
    ticket, plate, timestamp = generate_test_data()
    
    print(f"\nMencoba cetak tiket dengan data:")
    print(f"Nomor Tiket : {ticket}")
    print(f"Nomor Plat  : {plate}")
    print(f"Waktu       : {timestamp}")
    
    # Print via serial
    success = print_ticket_serial(ser, ticket, plate, timestamp)
    return success

def test_server_ticket(ser):
    """Test printing with the server's TKT format"""
    # Create a sample ticket with TKT format
    ticket = "TKT202503290219527426"  # Example from server
    plate = "QB1234"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nMencoba cetak tiket format server dengan data:")
    print(f"Nomor Tiket : {ticket}")
    print(f"Nomor Plat  : {plate}")
    print(f"Waktu       : {timestamp}")
    
    # Print via serial
    success = print_ticket_serial(ser, ticket, plate, timestamp)
    return success

def test_serial_connection(ser):
    """Test serial connection by sending a simple command"""
    if not ser:
        print("❌ Tidak ada koneksi serial")
        return False
        
    try:
        print(f"Testing serial connection on {ser.port}...")
        
        # Send printer status request
        ser.write(b"\x10\x04\x01")  # DLE EOT n - Transmit printer status
        ser.flush()
        
        # Try to read response (may not work with all printers)
        time.sleep(0.5)
        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            print(f"Printer response: {response.hex()}")
        else:
            print("No response from printer (this is normal for some printers)")
        
        # Send printer initialization command
        ser.write(b"\x1B\x40")  # ESC @ - Initialize printer
        ser.flush()
        
        print("✅ Serial connection test complete")
        return True
        
    except Exception as e:
        print(f"❌ Serial connection test failed: {str(e)}")
        return False

def send_raw_command(ser):
    """Send a raw command to the printer for testing"""
    if not ser:
        print("❌ Tidak ada koneksi serial")
        return False
        
    print("\nMenu perintah raw:")
    print("1. Initialize printer")
    print("2. Cut paper")
    print("3. Print test pattern")
    print("4. Custom command (hex)")
    
    choice = input("Pilihan: ")
    
    try:
        if choice == "1":
            ser.write(b"\x1B\x40")  # ESC @ - Initialize printer
            print("Sent: ESC @")
        elif choice == "2":
            ser.write(b"\x1D\x56\x42")  # GS V B - Cut paper
            print("Sent: GS V B")
        elif choice == "3":
            # Print a simple test pattern
            ser.write(b"\x1B\x40")  # Initialize
            ser.write(b"\x1B\x21\x00")  # Normal font
            ser.write("TEST PRINT\n".encode('ascii'))
            ser.write("1234567890\n".encode('ascii'))
            ser.write("ABCDEFGHIJKLMNOPQRSTUVWXYZ\n".encode('ascii'))
            ser.write(b"\x1D\x56\x42")  # Cut paper
            print("Sent: Test pattern")
        elif choice == "4":
            hex_cmd = input("Enter hex command (e.g. 1B40): ")
            cmd_bytes = bytes.fromhex(hex_cmd)
            ser.write(cmd_bytes)
            print(f"Sent: {hex_cmd}")
        else:
            print("Invalid choice")
            return False
            
        ser.flush()
        print("✅ Command sent successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send command: {str(e)}")
        return False

def main():
    """Main function"""
    print("===== ARDUINO DIRECT PRINT UTILITY =====")
    print(f"Versi Python: {sys.version}")
    
    # Try to connect to printer via serial
    ser = try_connect_serial()
    
    if not ser:
        print("\n❌ Gagal menemukan printer via serial")
        print("Pastikan printer terhubung dan nyala")
        return
    
    # Menu loop
    while True:
        print("\nArduino Direct Print - Menu:")
        print("1. Test tiket biasa")
        print("2. Test tiket format server (TKT)")
        print("3. Test koneksi serial")
        print("4. Kirim perintah raw")
        print("q. Keluar")
        
        choice = input("Pilihan Anda: ")
        
        if choice.lower() == 'q':
            break
        elif choice == '1':
            print_test(ser)
        elif choice == '2':
            test_server_ticket(ser)
        elif choice == '3':
            test_serial_connection(ser)
        elif choice == '4':
            send_raw_command(ser)
        elif choice == '':
            # Default to regular test if just Enter is pressed
            print_test(ser)
        else:
            print("Pilihan tidak valid")
    
    # Close serial connection
    if ser:
        ser.close()
        print("Serial port ditutup")

if __name__ == "__main__":
    main() 