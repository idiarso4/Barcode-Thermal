import serial
import time
import sys
import win32print
import logging
import os
from datetime import datetime

# Setup logging
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Setup file handler
    log_file = f'logs/arduino_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging started. Log file: {log_file}")

def print_ticket():
    try:
        printer_name = win32print.GetDefaultPrinter()
        logging.info(f"Using printer: {printer_name}")
        
        # Generate simple ticket number
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-6:]
        
        # Open printer
        printer_handle = win32print.OpenPrinter(printer_name)
        logging.debug("Printer opened successfully")
        
        # Start print job
        win32print.StartDocPrinter(printer_handle, 1, ("Ticket", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        logging.debug("Print job started")
        
        # Print ticket with simple format
        ticket_text = f"\n\n{ticket_number}\n\n\n"
        win32print.WritePrinter(printer_handle, ticket_text.encode('ascii'))
        logging.debug(f"Sent ticket data: {ticket_number}")
        
        # End print job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        logging.info(f"✅ Ticket printed: {ticket_number}")
        return True
    except Exception as e:
        logging.error(f"Error printing ticket: {e}", exc_info=True)
        return False

def test_arduino():
    logging.info("Starting Arduino Communication Test")
    logging.info("===================================")
    
    try:
        # Try to open the serial port
        logging.info("Opening COM7 at 9600 baud...")
        ser = serial.Serial(
            'COM7',
            baudrate=9600,
            timeout=2,
            write_timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # Wait for Arduino to initialize
        logging.info("Waiting for Arduino to initialize (2 seconds)...")
        time.sleep(2)
        
        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        logging.debug("Serial buffers cleared")
        
        # Wait for READY message
        logging.info("Waiting for READY message...")
        logging.debug("Monitoring serial data...")
        
        while True:
            if ser.in_waiting > 0:
                # Read raw bytes first
                raw_data = ser.read(ser.in_waiting)
                logging.debug(f"Raw bytes received: {raw_data}")
                
                try:
                    # Try to decode as UTF-8
                    response = raw_data.decode('utf-8', errors='replace').strip()
                    logging.debug(f"Decoded data: '{response}'")
                    
                    if response == "READY":
                        logging.info("✅ Arduino is ready!")
                        break
                    elif response == "1":
                        logging.info("Button press detected!")
                        if print_ticket():
                            logging.info("✅ Ticket printed successfully")
                        else:
                            logging.error("❌ Failed to print ticket")
                except Exception as e:
                    logging.error(f"Error decoding data: {e}")
            
            time.sleep(0.1)
        
        logging.info("Monitoring for button presses... (Press Ctrl+C to exit)")
        logging.debug("Waiting for '1' signal...")
        
        while True:
            if ser.in_waiting > 0:
                # Read raw bytes first
                raw_data = ser.read(ser.in_waiting)
                logging.debug(f"Raw bytes received: {raw_data}")
                
                try:
                    # Try to decode as UTF-8
                    data = raw_data.decode('utf-8', errors='replace').strip()
                    logging.debug(f"Decoded data: '{data}'")
                    
                    if data == "1":
                        logging.info("Button press detected!")
                        if print_ticket():
                            logging.info("✅ Ticket printed successfully")
                        else:
                            logging.error("❌ Failed to print ticket")
                except Exception as e:
                    logging.error(f"Error decoding data: {e}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logging.info("Test stopped by user")
    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            logging.info("Serial connection closed")

if __name__ == "__main__":
    setup_logging()
    test_arduino() 