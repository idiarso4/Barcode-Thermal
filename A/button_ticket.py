import win32print
import time

def print_ticket():
    printer_name = win32print.GetDefaultPrinter()
    print(f"Printing ke: {printer_name}")
    
    # Generate ticket number
    timestamp = int(time.time())
    ticket_number = str(timestamp)[-6:]  # Keep it short: 6 digits only
    
    printer_handle = None
    try:
        # Wait for system to stabilize
        time.sleep(1.0)
        
        # Open printer - simple and direct
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start print job with minimal parameters
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Ticket", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # NO control sequences at all - just the number with newlines
        ticket_string = f"\n\n\n{ticket_number}\n\n\n\n\n\n"
        
        # Single write operation
        win32print.WritePrinter(printer_handle, ticket_string.encode('ascii'))
        
        # End the print job
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