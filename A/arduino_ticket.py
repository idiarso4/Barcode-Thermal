import win32print
import time

def print_raw_ticket():
    """
    Super simple ticket printer function - absolute minimum code
    Only prints the ticket number with no control codes
    """
    try:
        # Get printer
        printer_name = win32print.GetDefaultPrinter()
        
        # Generate simple numeric ticket
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-6:]
        
        # Open printer directly
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start minimal print job
        win32print.StartDocPrinter(printer_handle, 1, ("Ticket", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Just print the number with spaces
        win32print.WritePrinter(printer_handle, f"\n\n{ticket_number}\n\n\n\n".encode('ascii'))
        
        # End job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        print(f"Ticket printed: {ticket_number}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print_raw_ticket() 