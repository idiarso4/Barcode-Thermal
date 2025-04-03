import win32print
import time

def generate_linear_barcode(ticket_number):
    """
    Generate a text-based linear barcode pattern from a ticket number.
    """
    barcode_pattern = ""
    
    # Convert each digit to a unique pattern of bars and spaces
    for digit in ticket_number:
        if digit == '0':
            barcode_pattern += "|| | "
        elif digit == '1':
            barcode_pattern += "||  |"
        elif digit == '2':
            barcode_pattern += "|| ||"
        elif digit == '3':
            barcode_pattern += "|||||"
        elif digit == '4':
            barcode_pattern += "| |||"
        elif digit == '5':
            barcode_pattern += "||||"
        elif digit == '6':
            barcode_pattern += "| ||"
        elif digit == '7':
            barcode_pattern += "|| |"
        elif digit == '8':
            barcode_pattern += "| | "
        elif digit == '9':
            barcode_pattern += "|||"
        else:
            barcode_pattern += "| |"
    
    # Add start and end patterns
    full_pattern = "|||" + barcode_pattern + "|||"
    return full_pattern

def print_test_barcode():
    """
    Print a test barcode ticket.
    Uses barcode generation code from Python.
    """
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Using printer: {printer_name}")
        
        # Ticket number for testing
        ticket_number = "123456"
        
        # Generate barcode pattern from ticket number
        barcode_pattern = generate_linear_barcode(ticket_number)
        
        # Open printer
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start print job
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("TestBarcode", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Reset printer - essential command
        win32print.WritePrinter(printer_handle, b"\x1B\x40")
        time.sleep(0.5)  # Wait for reset
        
        # Print ticket number in simple text
        ticket_text = f"\n\n{ticket_number}\n\n"
        win32print.WritePrinter(printer_handle, ticket_text.encode('ascii'))
        
        # Print the word BARCODE to identify section
        win32print.WritePrinter(printer_handle, "BARCODE: \n".encode('ascii'))
        
        # Convert pattern to blocks for better visibility
        barcode_line = ""
        for char in barcode_pattern:
            if char == '|':
                barcode_line += "█"  # Full block character
            else:
                barcode_line += " "  # Space
        
        # Print the barcode pattern
        win32print.WritePrinter(printer_handle, barcode_line.encode('cp437'))
        win32print.WritePrinter(printer_handle, b"\x0A\x0A")  # Line feeds
        
        # Add spacing and end
        win32print.WritePrinter(printer_handle, b"\x0A\x0A\x0A\x0A")
        
        # End print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        print(f"Test barcode printed successfully!")
        return True
        
    except Exception as e:
        print(f"Error printing test barcode: {e}")
        return False

if __name__ == "__main__":
    print_test_barcode() 