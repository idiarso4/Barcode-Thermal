import serial
import time
import win32print
import sys
import random

# Serial port settings - UPDATE THESE
SERIAL_PORT = 'COM7'  # Arduino port
BAUD_RATE = 9600

def generate_linear_barcode(ticket_number):
    """
    Generate a text-based linear barcode pattern from a ticket number.
    This is used to create a visual barcode representation.
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

def print_barcode_ticket():
    """
    Generate and print a ticket with a linear barcode.
    All barcode generation is handled by Python.
    """
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Using printer: {printer_name}")
        
        # Generate a ticket number (timestamp-based for uniqueness)
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-6:]  # Last 6 digits of timestamp
        
        # Generate barcode pattern from the ticket number
        barcode_pattern = generate_linear_barcode(ticket_number)
        
        # Open printer
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start print job
        win32print.StartDocPrinter(printer_handle, 1, ("BarcodeTicket", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Reset printer - ONLY essential command
        win32print.WritePrinter(printer_handle, b"\x1B\x40")
        time.sleep(0.5)  # Wait for reset
        
        # Print ticket number in large text
        ticket_text = f"\n\n{ticket_number}\n\n"
        win32print.WritePrinter(printer_handle, ticket_text.encode('ascii'))
        
        # Convert pattern to blocks for better visibility
        barcode_line = ""
        for char in barcode_pattern:
            if char == '|':
                barcode_line += "█"  # Full block character
            else:
                barcode_line += " "  # Space
        
        # Print the barcode
        win32print.WritePrinter(printer_handle, barcode_line.encode('cp437'))
        win32print.WritePrinter(printer_handle, b"\x0A\x0A")  # Line feeds
        
        # Add footer with spacing
        win32print.WritePrinter(printer_handle, b"\x0A\x0A\x0A\x0A")
        
        # End print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        print(f"Successfully printed ticket #{ticket_number}")
        return True
        
    except Exception as e:
        print(f"Error printing ticket: {e}")
        return False

def monitor_arduino():
    """
    Monitor Arduino for button presses.
    When a button press is detected, generate and print a barcode ticket.
    """
    print("Connecting to Arduino...")
    
    ser = None
    try:
        # Connect to Arduino
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to Arduino on {SERIAL_PORT}")
        time.sleep(2)  # Wait for connection to stabilize
        
        # Clear any buffered data
        ser.reset_input_buffer()
        
        print("Waiting for button press...")
        print("Press Ctrl+C to exit")
        print("-----------------------")
        
        while True:
            if ser.in_waiting > 0:
                # Read line from Arduino
                line = ser.readline().decode('utf-8', errors='replace').strip()
                
                # Process the line based on its content
                if line == "BUTTON_PRESSED":
                    print("\nButton pressed - generating and printing ticket...")
                    print_barcode_ticket()
                elif line == "READY":
                    print("Arduino is ready.")
                else:
                    print(f"Received: {line}")
            
            # Small delay to prevent high CPU usage
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        print("Running in test mode...")
        # Test print a ticket
        print_barcode_ticket()
        
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        
    finally:
        # Close serial connection if open
        if ser and ser.is_open:
            ser.close()
            print("Serial connection closed")

def main():
    """
    Main function that runs when script is executed.
    Checks if pyserial is installed and starts Arduino monitoring.
    """
    try:
        # Check if pyserial is installed
        import serial
    except ImportError:
        print("Required library 'pyserial' is not installed.")
        print("Please install it with: pip install pyserial")
        sys.exit(1)
        
    # Start monitoring Arduino
    monitor_arduino()

if __name__ == "__main__":
    main() 