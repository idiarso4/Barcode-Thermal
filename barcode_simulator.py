import datetime
import time

def simulate_barcode_print(ticket_number, barcode_type="CODE39"):
    """Simulasi pencetakan tiket dengan barcode berbeda"""
    print("\nSimulasi Cetak Tiket dengan", barcode_type)
    print("=" * 32)
    
    # Header tiket
    print("     RSI BANJARNEGARA     ")
    print("      TIKET PARKIR        ")
    print("-" * 32)
    
    # Informasi tiket
    timestamp = datetime.datetime.now()
    print(f"Tanggal : {timestamp.strftime('%d-%m-%Y')}")
    print(f"Jam     : {timestamp.strftime('%H:%M:%S')}")
    print(f"No.     : {ticket_number}")
    print("-" * 32)
    
    # Simulasi barcode
    if barcode_type == "CODE39":
        # Format CODE39: *data*
        barcode = f"*{ticket_number}*"
        print("\nBarcode CODE39:")
        print(barcode)
        print("Hex commands:")
        print("1D 6B 04")  # Select CODE39
        print("Data:", " ".join(hex(ord(c))[2:] for c in barcode))
        print("\nKelebihan CODE39:")
        print("✓ Paling kompatibel dengan printer thermal")
        print("✓ Mudah dibaca scanner")
        print("✓ Support huruf dan angka")
        print("✓ Format sederhana dengan * sebagai start/stop")
        print("✓ Ideal untuk tiket parkir")
        
    elif barcode_type == "CODE128":
        # Format CODE128: {data}
        barcode = f"{{{ticket_number}}}"
        print("\nBarcode CODE128:")
        print(barcode)
        print("Hex commands:")
        print("1D 6B 08")  # Select CODE128
        print("Data:", " ".join(hex(ord(c))[2:] for c in barcode))
        print("\nKelebihan CODE128:")
        print("✓ Lebih padat")
        print("✓ Support semua ASCII")
        print("✗ Tidak semua printer mendukung")
        print("✗ Lebih kompleks")
        
    elif barcode_type == "EAN13":
        # Format EAN-13: 12 digits + check digit
        barcode = ticket_number[-12:] if len(ticket_number) >= 12 else ticket_number.zfill(12)
        print("\nBarcode EAN-13:")
        print(barcode)
        print("Hex commands:")
        print("1D 6B 02")  # Select EAN-13
        print("Data:", " ".join(hex(ord(c))[2:] for c in barcode))
        print("\nKelebihan EAN-13:")
        print("✓ Standar retail")
        print("✗ Hanya untuk 13 digit angka")
        print("✗ Tidak cocok untuk tiket parkir")
        
    print("\nESC/POS Commands yang akan dikirim ke printer:")
    print("1B 40      # Initialize printer")
    print("1B 61 01   # Center alignment")
    print("1D 48 02   # Set barcode height")
    print("1D 77 02   # Set barcode width")
    print("1D 6B XX   # Select barcode type")
    print(f"Data: {barcode}")
    print("0A         # Line feed")
    print("1D 56 41   # Cut paper")
    
    print("\n" + "=" * 32)

def main():
    # Generate nomor tiket seperti format asli
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    counter = 1234
    ticket_number = f"TKT{timestamp}_{str(counter).zfill(4)}"
    
    # Simulasi dengan berbagai format
    simulate_barcode_print(ticket_number, "CODE39")
    time.sleep(1)
    simulate_barcode_print(ticket_number, "CODE128")
    time.sleep(1)
    simulate_barcode_print(ticket_number[-12:], "EAN13")
    
    print("\nRekomendasi untuk Printer Thermal:")
    print("1. CODE39 (✓ RECOMMENDED)")
    print("   - Paling reliable untuk printer thermal")
    print("   - Support: A-Z, 0-9, -, ., $, /, +, %, SPACE")
    print("   - Format sederhana: *DATA*")
    print("   - Command: 1D 6B 04")
    print("   - Ideal untuk tiket parkir")
    print("\n2. CODE128")
    print("   - Support lebih banyak karakter")
    print("   - Lebih padat tapi kompleks")
    print("   - Command: 1D 6B 08")
    print("   - Tidak semua printer mendukung")
    print("\n3. EAN-13")
    print("   - Hanya untuk 13 digit angka")
    print("   - Command: 1D 6B 02")
    print("   - Lebih cocok untuk retail")
    print("\nTips Pencetakan Barcode Thermal:")
    print("1. Gunakan kertas thermal berkualitas baik")
    print("2. Atur tinggi barcode (1D 48 XX)")
    print("3. Atur lebar barcode (1D 77 XX)")
    print("4. Pastikan alignment center (1B 61 01)")
    print("5. Beri jarak atas bawah yang cukup")

if __name__ == "__main__":
    main() 