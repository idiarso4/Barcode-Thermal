import serial
import time
import win32print
import os
import sys

# Serial port settings for Arduino
SERIAL_PORT = 'COM1'  # Update this to your Arduino port
BAUD_RATE = 9600

def print_plain_text_ticket():
    """
    Print a ticket with absolutely minimal commands.
    No ESC/POS codes, just pure text to prevent any random characters.
    """
    try:
        # Get the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Using printer: {printer_name}")
        
        # Generate a simple numeric ticket number (6 digits)
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-6:]
        
        # Open the printer directly
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start a basic print job
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("SimpleTicket", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Print ONLY the ticket number with newlines (no formatting)
        # This is the most reliable approach to avoid random characters
        ticket_text = "\n\n" + ticket_number + "\n\n\n\n"
        win32print.WritePrinter(printer_handle, ticket_text.encode('ascii'))
        
        # End the print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        print(f"Printed ticket: {ticket_number}")
        return True
        
    except Exception as e:
        print(f"Error printing ticket: {e}")
        return False

def arduino_button_monitor():
    """Monitor the Arduino for button presses"""
    print("Attempting to connect to Arduino...")
    
    ser = None
    try:
        # Try to connect to the Arduino
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Successfully connected to Arduino on {SERIAL_PORT}")
        
        # Add a delay to ensure stable connection
        time.sleep(2)
        
        # Clear any buffered data
        ser.reset_input_buffer()
        
        print("Waiting for button press... Press Ctrl+C to exit")
        print("-----------------------------------------------")
        
        # Track the last time a ticket was printed
        last_print_time = 0
        cooldown_period = 3  # seconds between allowed button presses
        
        while True:
            # Check if there's data available from Arduino
            if ser.in_waiting > 0:
                # Read the data
                line = ser.readline().decode('utf-8', errors='replace').strip()
                
                # Check if it's a button press signal
                if "BUTTON_PRESSED" in line:
                    current_time = time.time()
                    
                    # Check if cooldown period has elapsed
                    if current_time - last_print_time >= cooldown_period:
                        print("\nButton pressed - printing ticket...")
                        
                        # Print the ticket (with additional error handling)
                        try:
                            print_plain_text_ticket()
                            last_print_time = current_time
                        except Exception as e:
                            print(f"Failed to print ticket: {e}")
                    else:
                        remaining = cooldown_period - (current_time - last_print_time)
                        print(f"Too soon! Please wait {remaining:.1f} seconds")
            
            # Small delay to prevent high CPU usage
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        # If we can't connect to Arduino, run in test mode
        print("Running in test mode (no Arduino connected)")
        print_plain_text_ticket()
        
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        
    finally:
        # Make sure to close the serial connection
        if ser and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    # First check if pyserial is installed
    try:
        import serial
    except ImportError:
        print("The 'pyserial' library is required.")
        print("Please install it with: pip install pyserial")
        sys.exit(1)
    
    # Start the button monitor
    arduino_button_monitor() 