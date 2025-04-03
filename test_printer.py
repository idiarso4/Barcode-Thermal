import win32print
import time
import os
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('printer_test')

def find_epson_printer():
    """Find an EPSON printer"""
    printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)]
    logger.info(f"Available printers: {printers}")
    
    # Look for EPSON thermal printer
    for printer_name in printers:
        if "EPSON" in printer_name.upper() or "TM-T" in printer_name.upper():
            logger.info(f"Found EPSON printer: {printer_name}")
            return printer_name
    
    # Use default printer as fallback
    default_printer = win32print.GetDefaultPrinter()
    logger.info(f"Using default printer: {default_printer}")
    return default_printer

def print_test_ticket(printer_name):
    """Print a test ticket using ESC/POS commands"""
    # Generate test data
    ticket_number = "TEST12345"
    plate = "AB1234"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Create ESC/POS commands
    commands = bytearray()
    
    # Reset printer
    commands.extend(b"\x1B\x40")
    
    # Center alignment
    commands.extend(b"\x1B\x61\x01")
    
    # Title - double height and width
    commands.extend(b"\x1B\x21\x30")  # Double width, double height
    commands.extend(b"=== TEST TIKET ===\n")
    
    # Reset text format
    commands.extend(b"\x1B\x21\x00")
    commands.extend(b"\n")
    
    # Print some standard text
    commands.extend(b"TIKET: ")
    commands.extend(ticket_number.encode())
    commands.extend(b"\n")
    
    commands.extend(b"PLAT : ")
    commands.extend(plate.encode())
    commands.extend(b"\n")
    
    commands.extend(b"WAKTU: ")
    commands.extend(timestamp.encode())
    commands.extend(b"\n\n")
    
    # Print a basic barcode
    commands.extend(b"\x1D\x48\x02")  # HRI position - below barcode
    commands.extend(b"\x1D\x68\x50")  # Barcode height = 80 dots
    commands.extend(b"\x1D\x77\x02")  # Barcode width multiplier (2)
    commands.extend(b"\x1D\x6B\x04")  # Select CODE39
    
    # Add length byte and data
    length = len(ticket_number)
    commands.append(length)  # Length byte
    commands.extend(ticket_number.encode())  # Data
    
    # Add newlines after barcode
    commands.extend(b"\n\n")
    
    # Footer text
    commands.extend(b"Terima Kasih\n")
    commands.extend(b"Test Printer Selesai\n\n")
    
    # Cut paper
    commands.extend(b"\x1D\x56\x00")  # Full cut
    
    # Send to printer
    try:
        logger.info(f"Sending {len(commands)} bytes to printer: {printer_name}")
        
        # Log hex values for debugging (first 100 bytes)
        hex_values = ' '.join('{:02x}'.format(b) for b in commands[:100])
        logger.info(f"Command bytes (first 100): {hex_values}")
        
        # Open printer and send commands
        handle = win32print.OpenPrinter(printer_name)
        try:
            job = win32print.StartDocPrinter(handle, 1, ("Test Ticket", None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, commands)
                win32print.EndPagePrinter(handle)
                print("✅ Test ticket sent to printer successfully")
                return True
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)
            
    except Exception as e:
        logger.error(f"Error printing test ticket: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Printer Test Utility ===")
    
    # Find a suitable printer
    printer = find_epson_printer()
    if not printer:
        print("❌ No printer found")
        exit(1)
        
    print(f"Using printer: {printer}")
    
    # Print a test ticket
    print("Sending test ticket...")
    print_test_ticket(printer)
    
    print("Test complete. Check printer for output.") 