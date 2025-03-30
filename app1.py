import serial
import time
import win32print  # For Windows printing

# Open the serial connection to the Arduino
arduino = serial.Serial('COM4', 9600, timeout=1)

def generate_and_print_barcode(barcode_data):
    try:
        # Get the default printer
        printer_name = win32print.GetDefaultPrinter()
        print(f"Printing to: {printer_name}")

        # Open the printer
        printer_handle = win32print.OpenPrinter(printer_name)

        # Start a print job
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Barcode Print Job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)

        # ESC/POS commands for barcode printing
        esc_pos_commands = (
            b"\x1B\x40" +          # Initialize printer
            b"Testing Text\n" +    # Plain text for testing
            b"\x1D\x6B\x49" +      # Barcode type: Code 128
            barcode_data.encode() + b"\x00" +  # Barcode data (null-terminated)
            b"\x0A" +              # Line feed (new line)
            b"\x1D\x56\x41\x00"    # Auto-cut command
        )

        # Send the ESC/POS commands to the printer
        win32print.WritePrinter(printer_handle, esc_pos_commands)

        # End the print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)

        print("Barcode printed successfully!")
    except Exception as e:
        print(f"Error printing barcode: {e}")
    finally:
        # Close the printer handle
        if printer_handle:
            try:
                win32print.ClosePrinter(printer_handle)
            except Exception as e:
                print(f"Error closing printer handle: {e}")
def main():
    while True:
        try:
            # Reconnect to the Arduino if the connection is lost
            if not arduino.is_open:
                arduino.open()

            # Check for incoming data from the Arduino
            if arduino.in_waiting > 0:
                received_data = arduino.readline().decode('utf-8').strip()

                if received_data:
                    print(f"Received number: {received_data}")

                    # Generate and print the barcode using the received number
                    generate_and_print_barcode(received_data)

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    try:
        main()
    finally:
        if arduino.is_open:
            arduino.close()