import win32print

def test_printer_access():
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Default printer: {printer_name}")
        
        # List all printers
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        print("\nAvailable printers:")
        for flags, description, name, comment in printers:
            print(f"- {name}")
            print(f"  Description: {description}")
            
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing win32print module...")
    test_printer_access() 