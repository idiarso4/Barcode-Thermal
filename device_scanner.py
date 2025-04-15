import serial.tools.list_ports
import subprocess
import logging
import os
from datetime import datetime
import win32print

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    log_file = f'logs/device_scan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def scan_serial_ports():
    """Scan for available serial ports"""
    logging.info("Scanning for serial ports...")
    
    ports = list(serial.tools.list_ports.comports())
    if ports:
        logging.info("Found serial ports:")
        for port in ports:
            logging.info(f"- {port.device}: {port.description}")
            if "Arduino" in port.description:
                logging.info(f"  ✅ Likely Arduino device: {port.device}")
    else:
        logging.warning("No serial ports found")
    
    return ports

def scan_windows_printers():
    """Scan for available Windows printers"""
    logging.info("Scanning for Windows printers...")
    
    try:
        # Get list of printers
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        if printers:
            logging.info("Found printers:")
            default_printer = win32print.GetDefaultPrinter()
            
            for flags, description, name, comment in printers:
                if name == default_printer:
                    logging.info(f"- {name} (Default)")
                    logging.info(f"  Description: {description}")
                    logging.info(f"  Comment: {comment}")
                else:
                    logging.info(f"- {name}")
                    logging.info(f"  Description: {description}")
                    logging.info(f"  Comment: {comment}")
        else:
            logging.warning("No printers found")
            
        return printers
    except Exception as e:
        logging.error(f"Error scanning printers: {e}")
        return []

def test_printer(printer_name=None):
    """Test specific printer or default printer"""
    try:
        if printer_name is None:
            printer_name = win32print.GetDefaultPrinter()
            logging.info(f"Testing default printer: {printer_name}")
        else:
            logging.info(f"Testing printer: {printer_name}")
        
        # Try to open printer
        printer_handle = win32print.OpenPrinter(printer_name)
        if printer_handle:
            logging.info(f"✅ Successfully connected to printer: {printer_name}")
            
            # Get printer info
            printer_info = win32print.GetPrinter(printer_handle, 2)
            logging.info("Printer details:")
            logging.info(f"- Status: {printer_info['Status']}")
            logging.info(f"- Port: {printer_info['pPortName']}")
            logging.info(f"- Driver: {printer_info['pDriverName']}")
            
            win32print.ClosePrinter(printer_handle)
            return True
    except Exception as e:
        logging.error(f"Error testing printer: {e}")
    
    return False

def main():
    log_file = setup_logging()
    logging.info("Starting device scanner...")
    
    # Scan for serial ports (Arduino)
    serial_ports = scan_serial_ports()
    
    # Scan for Windows printers
    printers = scan_windows_printers()
    
    # Test default printer
    test_printer()
    
    logging.info(f"Scan complete. Check {log_file} for details")

if __name__ == "__main__":
    main() 