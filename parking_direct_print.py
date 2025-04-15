import win32print
import time
import logging
import random
import string
import requests
import json
import os
import sys

# Simple direct printing script - stripped down to essentials

def print_direct(ticket_number, plate_number, timestamp):
    """Print directly to the printer using raw commands"""
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        if not printer_name:
            print("❌ Error: No default printer found")
            return False
            
        print(f"Menggunakan printer: {printer_name}")
        
        # Check printer status
        try:
            printer_info = win32print.GetPrinter(printer_name, 2)
            printer_status = printer_info["Status"]
            
            if printer_status == 0:
                print("✅ Printer status: Ready")
            else:
                print(f"⚠️ Warning: Printer status code: {printer_status}")
                
                # Common status codes
                status_messages = {
                    win32print.PRINTER_STATUS_PAUSED: "Printer is paused",
                    win32print.PRINTER_STATUS_ERROR: "Printer error",
                    win32print.PRINTER_STATUS_PENDING_DELETION: "Printer being deleted",
                    win32print.PRINTER_STATUS_PAPER_JAM: "Paper jam",
                    win32print.PRINTER_STATUS_PAPER_OUT: "Out of paper",
                    win32print.PRINTER_STATUS_MANUAL_FEED: "Manual feed required",
                    win32print.PRINTER_STATUS_PAPER_PROBLEM: "Paper problem",
                    win32print.PRINTER_STATUS_OFFLINE: "Printer is offline",
                    win32print.PRINTER_STATUS_IO_ACTIVE: "Receiving data",
                    win32print.PRINTER_STATUS_BUSY: "Printer is busy",
                    win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: "Output bin is full",
                    win32print.PRINTER_STATUS_NOT_AVAILABLE: "Printer not available",
                    win32print.PRINTER_STATUS_WAITING: "Waiting",
                    win32print.PRINTER_STATUS_PROCESSING: "Processing",
                    win32print.PRINTER_STATUS_INITIALIZING: "Initializing",
                    win32print.PRINTER_STATUS_WARMING_UP: "Warming up",
                    win32print.PRINTER_STATUS_TONER_LOW: "Toner low",
                    win32print.PRINTER_STATUS_NO_TONER: "No toner",
                    win32print.PRINTER_STATUS_PAGE_PUNT: "Page punt",
                    win32print.PRINTER_STATUS_USER_INTERVENTION: "User intervention required",
                    win32print.PRINTER_STATUS_OUT_OF_MEMORY: "Out of memory",
                    win32print.PRINTER_STATUS_DOOR_OPEN: "Door open",
                    win32print.PRINTER_STATUS_SERVER_UNKNOWN: "Server unknown",
                    win32print.PRINTER_STATUS_POWER_SAVE: "Power save mode"
                }
                
                for status_code, message in status_messages.items():
                    if printer_status & status_code:
                        print(f"⚠️ {message}")
        except Exception as status_error:
            print(f"⚠️ Cannot get printer status: {status_error}")

        # For longer ticket numbers (like TKT202503290219527426), use a shorter version for barcode
        barcode_ticket = ticket_number
        if len(ticket_number) > 15 and ticket_number.startswith("TKT"):
            # Extract just the numeric portion or the last 10 characters
            barcode_ticket = ticket_number[-10:]
            print(f"Menggunakan barcode pendek: {barcode_ticket} dari {ticket_number}")

        # Direct handle to the printer
        try:
            handle = win32print.OpenPrinter(printer_name)
            print("✅ Successfully opened printer connection")
        except Exception as open_error:
            print(f"❌ Failed to open printer: {open_error}")
            return False
        
        try:
            # Start a document
            job = win32print.StartDocPrinter(handle, 1, ("Parking Ticket", None, "RAW"))
            print(f"✅ Started document with job ID: {job}")
            
            try:
                # Start a page
                win32print.StartPagePrinter(handle)
                print("✅ Started page")
                
                # Create ESC/POS commands
                # Initialize printer
                data = b"\x1B\x40"  # ESC @ - Initialize printer
                win32print.WritePrinter(handle, data)
                
                # Center align
                data = b"\x1B\x61\x01"  # ESC a 1 - Center alignment
                win32print.WritePrinter(handle, data)
                
                # Title with large font
                data = b"\x1B\x21\x30"  # ESC ! 0x30 - Double width/height
                win32print.WritePrinter(handle, data)
                data = "PARKIR RSI BNA\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                # Normal font
                data = b"\x1B\x21\x00"  # ESC ! 0x00 - Normal font
                win32print.WritePrinter(handle, data)
                
                # Line separator
                data = "====================\n\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                # Ticket info - show the full ticket number
                data = f"TIKET: {ticket_number}\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                data = f"PLAT : {plate_number}\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                data = f"WAKTU: {timestamp}\n\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                # Barcode (CODE39 format)
                data = b"\x1D\x48\x02"  # GS H 2 - HRI below barcode
                win32print.WritePrinter(handle, data)
                
                data = b"\x1D\x68\x50"  # GS h 80 - Barcode height 80 dots
                win32print.WritePrinter(handle, data)
                
                data = b"\x1D\x77\x02"  # GS w 2 - Barcode width (multiplier 2)
                win32print.WritePrinter(handle, data)
                
                data = b"\x1D\x6B\x04"  # GS k 4 - CODE39 barcode
                win32print.WritePrinter(handle, data)
                
                # Use the shortened barcode version
                data = bytes([len(barcode_ticket)])  # Length byte
                win32print.WritePrinter(handle, data)
                
                data = barcode_ticket.encode('ascii')  # Barcode data
                win32print.WritePrinter(handle, data)
                
                # Line feeds after barcode
                data = b"\n\n"
                win32print.WritePrinter(handle, data)
                
                # Footer
                data = "Terima kasih\nJangan hilangkan tiket ini\n\n".encode('ascii')
                win32print.WritePrinter(handle, data)
                
                # Cut paper
                data = b"\x1D\x56\x42"  # GS V B - Cut paper
                win32print.WritePrinter(handle, data)
                
                # End the page and document
                win32print.EndPagePrinter(handle)
                print("✅ Page complete")
                
                win32print.EndDocPrinter(handle)
                print("✅ Document complete")
                
                win32print.ClosePrinter(handle)
                print("✅ Printer connection closed")
                
                print("✅ Tiket berhasil dicetak")
                return True
                
            except Exception as page_error:
                print(f"❌ Error in page printing: {page_error}")
                win32print.EndDocPrinter(handle)
                return False
                
        except Exception as doc_error:
            print(f"❌ Error starting document: {doc_error}")
            win32print.ClosePrinter(handle)
            return False
            
    except Exception as e:
        print(f"❌ Gagal mencetak: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.args}")
        return False

def generate_test_data():
    """Generate test data for printing test"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    plate = f"{letters}{numbers}"
    
    # Generate both a simple test ticket and a server-format ticket
    if random.choice([True, False]):
        # Simple test ticket
        ticket = f"TST{int(time.time())%10000:04d}"
    else:
        # Server format ticket (long format with TKT prefix)
        now = int(time.time())
        ticket = f"TKT{time.strftime('%Y%m%d%H%M%S')}{now%10000:04d}"
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return ticket, plate, timestamp

def print_test():
    """Run a simple print test"""
    # Generate test data
    ticket, plate, timestamp = generate_test_data()
    
    print(f"\nMencoba cetak tiket dengan data:")
    print(f"Nomor Tiket : {ticket}")
    print(f"Nomor Plat  : {plate}")
    print(f"Waktu       : {timestamp}")
    
    # Print directly
    success = print_direct(ticket, plate, timestamp)
    
    if not success:
        print("\nMencoba metode cetak alternatif...")
        try:
            # Alternative printing method - all at once
            printer_name = win32print.GetDefaultPrinter()
            handle = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(handle, 1, ("Parking Ticket", None, "RAW"))
                try:
                    win32print.StartPagePrinter(handle)
                    
                    # All commands combined
                    commands = bytearray()
                    
                    # Initialize printer and set formatting
                    commands.extend(b"\x1B\x40")  # Initialize printer
                    commands.extend(b"\x1B\x61\x01")  # Center alignment
                    
                    # Title
                    commands.extend(b"\x1B\x21\x30")  # Double width/height
                    commands.extend("PARKIR RSI BNA\n".encode('ascii'))
                    
                    # Reset to normal font
                    commands.extend(b"\x1B\x21\x00")
                    commands.extend("====================\n\n".encode('ascii'))
                    
                    # Ticket info
                    commands.extend(f"TIKET: {ticket}\n".encode('ascii'))
                    commands.extend(f"PLAT : {plate}\n".encode('ascii'))
                    commands.extend(f"WAKTU: {timestamp}\n\n".encode('ascii'))
                    
                    # Barcode
                    commands.extend(b"\x1D\x48\x02")  # HRI below
                    commands.extend(b"\x1D\x68\x50")  # Height 80
                    commands.extend(b"\x1D\x77\x02")  # Width 2
                    commands.extend(b"\x1D\x6B\x04")  # CODE39
                    commands.append(len(ticket))  # Length byte
                    commands.extend(ticket.encode('ascii'))  # Data
                    
                    # Footer
                    commands.extend(b"\n\nTerima kasih\nJangan hilangkan tiket ini\n\n")
                    
                    # Cut paper
                    commands.extend(b"\x1D\x56\x42")
                    
                    # Send all commands at once
                    win32print.WritePrinter(handle, commands)
                    
                    win32print.EndPagePrinter(handle)
                    print("✅ Metode alternatif berhasil")
                    return True
                finally:
                    win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
                
        except Exception as e:
            print(f"❌ Metode alternatif gagal: {str(e)}")
            
            # Last resort - try text file method
            try:
                printer_name = win32print.GetDefaultPrinter()
                
                # Create a text file with printer instructions
                with open("temp_ticket.txt", "w") as f:
                    f.write(f"PARKIR RSI BNA\n\n")
                    f.write(f"TIKET: {ticket}\n")
                    f.write(f"PLAT : {plate}\n")
                    f.write(f"WAKTU: {timestamp}\n\n")
                    f.write(f"Terima kasih\n")
                
                # Print the text file
                with open("temp_ticket.txt", "rb") as f:
                    data = f.read()
                
                handle = win32print.OpenPrinter(printer_name)
                try:
                    job = win32print.StartDocPrinter(handle, 1, ("Text Ticket", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(handle)
                        win32print.WritePrinter(handle, data)
                        win32print.EndPagePrinter(handle)
                        print("✅ Metode text file berhasil")
                        return True
                    finally:
                        win32print.EndDocPrinter(handle)
                finally:
                    win32print.ClosePrinter(handle)
                    
                    # Delete temp file
                    if os.path.exists("temp_ticket.txt"):
                        os.remove("temp_ticket.txt")
                        
            except Exception as e2:
                print(f"❌ Semua metode gagal: {str(e2)}")
                return False

def test_tkt_format():
    """Test printing with the server's TKT format"""
    # Create a sample ticket with TKT format
    now = int(time.time())
    ticket = f"TKT{time.strftime('%Y%m%d%H%M%S')}{now%10000:04d}"
    plate = "QB1234"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nMencoba cetak tiket format server dengan data:")
    print(f"Nomor Tiket : {ticket}")
    print(f"Nomor Plat  : {plate}")
    print(f"Waktu       : {timestamp}")
    
    # Print directly
    success = print_direct(ticket, plate, timestamp)
    return success

def test_printer_connection():
    """Test basic printer connection without actually printing"""
    try:
        # List all available printers
        print("===== PRINTER CONNECTION TEST =====")
        printer_list = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)
        
        if not printer_list:
            print("❌ No printers found on this system")
            return False
        
        print(f"Found {len(printer_list)} printer(s)")
        
        for i, printer in enumerate(printer_list):
            print(f"{i+1}. {printer[2]}")
        
        # Get default printer
        default_printer = win32print.GetDefaultPrinter()
        
        if not default_printer:
            print("❌ No default printer set")
            return False
        
        print(f"Default printer: {default_printer}")
        
        # Try to open connection to default printer
        try:
            handle = win32print.OpenPrinter(default_printer)
            print("✅ Successfully opened connection to default printer")
            
            # Get printer info
            try:
                printer_info = win32print.GetPrinter(handle, 2)
                print(f"Printer information:")
                print(f"  - Name: {printer_info.get('pPrinterName', 'N/A')}")
                print(f"  - Port: {printer_info.get('pPortName', 'N/A')}")
                print(f"  - Driver: {printer_info.get('pDriverName', 'N/A')}")
                
                # Check printer status
                status = printer_info.get("Status", -1)
                if status == 0:
                    print("  - Status: Ready")
                else:
                    print(f"  - Status code: {status}")
                    
            except Exception as info_error:
                print(f"❌ Error getting printer info: {info_error}")
                
            win32print.ClosePrinter(handle)
            return True
            
        except Exception as open_error:
            print(f"❌ Error opening printer: {open_error}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing printer connection: {e}")
        return False

def main():
    """Main function to control printing"""
    print("===== PRINTER TEST UTILITY =====")
    print(f"Versi Python: {sys.version}")
    print(f"Versi win32print: {win32print}")
    
    # Get available printers
    printers = [printer_info[2] for printer_info in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)]
    default_printer = win32print.GetDefaultPrinter()
    
    print("\nPrinter tersedia:")
    for i, printer in enumerate(printers):
        if printer == default_printer:
            print(f"  {i+1}. {printer} (DEFAULT)")
        else:
            print(f"  {i+1}. {printer}")
    
    # Print test ticket
    while True:
        print("\nPilihan uji cetak:")
        print("1. Test tiket biasa")
        print("2. Test tiket format server (TKT)")
        print("3. Test koneksi printer saja")
        print("q. Keluar")
        
        choice = input("Pilihan Anda: ")
        
        if choice.lower() == 'q':
            break
        elif choice == '1':
            print_test()
        elif choice == '2':
            test_tkt_format()
        elif choice == '3':
            test_printer_connection()
        elif choice == '':
            # Default to regular test if just Enter is pressed
            print_test()
        else:
            print("Pilihan tidak valid")

if __name__ == "__main__":
    main() 