import win32print
import time
import os
import sys

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
        win32print.StartDocPrinter(printer_handle, 1, ("Barcode", None, "RAW"))
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

def main():
    """
    Main function to print tickets on demand without Arduino.
    """
    # Clear screen based on OS
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=============================================")
    print("         STANDALONE BARCODE PRINTER          ")
    print("=============================================")
    print()
    print("This program will print barcode tickets")
    print("without requiring an Arduino connection.")
    print()
    
    while True:
        print("\nOptions:")
        print("1. Print a barcode ticket")
        print("2. Exit")
        
        choice = input("\nEnter your choice (1 or 2): ")
        
        if choice == '1':
            print("\nPrinting barcode ticket...")
            print_barcode_ticket()
            print("\nPress Enter to continue...")
            input()
        elif choice == '2':
            print("\nExiting program...")
            break
        else:
            print("\nInvalid choice. Please try again.")
    
    print("\nThank you for using the Barcode Printer!")

if __name__ == "__main__":
    main() 