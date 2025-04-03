import datetime
import win32print
import time

def print_ticket():
    printer_name = win32print.GetDefaultPrinter()
    print(f"Printing ke: {printer_name}")
    
    # Generate ticket number and timestamp
    timestamp = int(time.time())
    ticket_number = str(timestamp)[-8:]  # Last 8 digits of timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Print ticket
    printer_handle = None
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Ticket Print", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Reset printer and set encoding
        win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
        
        # Header - Center align with larger text
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width/height text
        win32print.WritePrinter(printer_handle, "PARKING TICKET\n".encode('ascii', errors='replace'))
        
        # Normal text size
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
        win32print.WritePrinter(printer_handle, b"\n")
        
        # Date/time - Left align
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left align
        win32print.WritePrinter(printer_handle, f"Date: {current_time}\n\n".encode('ascii', errors='replace'))
        
        # Ticket number - Center, large and bold
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width/height
        win32print.WritePrinter(printer_handle, b"\x1B\x45\x01")  # Bold on
        win32print.WritePrinter(printer_handle, f"TICKET: {ticket_number}\n\n".encode('ascii', errors='replace'))
        
        # Reset text formatting
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
        win32print.WritePrinter(printer_handle, b"\x1B\x45\x00")  # Bold off
        
        # Try to print simple barcode using ESC/POS commands
        try:
            # Center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")
            
            # Set barcode height
            win32print.WritePrinter(printer_handle, b"\x1D\x68\x50")
            
            # Set barcode width
            win32print.WritePrinter(printer_handle, b"\x1D\x77\x02")
            
            # Print text below barcode
            win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")
            
            # Select CODE39 barcode type
            win32print.WritePrinter(printer_handle, b"\x1D\x6B\x04")
            
            # Send barcode data (up to 255 characters)
            barcode_data = f"*{ticket_number}*"  # CODE39 requires * as start/stop character
            win32print.WritePrinter(printer_handle, bytes([len(barcode_data)]))
            win32print.WritePrinter(printer_handle, barcode_data.encode('ascii'))
            
            # Add space after barcode
            win32print.WritePrinter(printer_handle, b"\x0A\x0A")
        except Exception as e:
            # If barcode fails, print a text alternative
            print(f"Barcode error: {e}")
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
            win32print.WritePrinter(printer_handle, "|||||||||||||||||||||||||\n".encode('ascii'))
            win32print.WritePrinter(printer_handle, f"{ticket_number}\n".encode('ascii'))
            win32print.WritePrinter(printer_handle, "|||||||||||||||||||||||||\n\n".encode('ascii'))
        
        # Divider line
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
        win32print.WritePrinter(printer_handle, ("-" * 32 + "\n").encode('ascii'))
        
        # Footer
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
        win32print.WritePrinter(printer_handle, "Thank you for visiting\nPlease keep this ticket\n\n".encode('ascii', errors='replace'))
        
        # Feed and cut
        win32print.WritePrinter(printer_handle, b"\x1B\x64\x05")  # Feed 5 lines
        win32print.WritePrinter(printer_handle, b"\x1D\x56\x00")  # Full cut
        
        # End printing
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        print("Ticket berhasil di print!")
        
    except Exception as e:
        print(f"Error printing ticket: {e}")
    finally:
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")

if __name__ == "__main__":
    print_ticket() 