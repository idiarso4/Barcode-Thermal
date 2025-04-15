import time
import logging
from datetime import datetime
import win32print
import random
import serial
import requests
import json
from printer_monitor import PrinterMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='parking_client.log'
)
logger = logging.getLogger(__name__)

# Server API Configuration
API_BASE_URL = "http://192.168.2.6:5051/api"

class ParkingButton:
    def __init__(self, terminal):
        """Initialize parking button handler
        
        Args:
            terminal: GetInTerminal instance that contains the API client
        """
        self.terminal = terminal
        self.api = terminal.api if terminal else None
        self.printer_name = win32print.GetDefaultPrinter()
        self.offline_counter = self._load_counter()
        self.running = False
        self.arduino = None
        self.button = None  # Inisialisasi button
        self.printer_monitor = PrinterMonitor()  # Initialize printer monitor
        self._try_connect_arduino()
        logger.info(f"Initialized with printer: {self.printer_name}")
        
    def _try_connect_arduino(self):
        """Try to connect to Arduino, return True if successful"""
        try:
            # Close any existing connection
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            
            print(f"\nConnecting to Arduino on COM7 at 9600 baud...")
            
            # Add more robust connection settings
            self.arduino = serial.Serial(
                'COM7',
                baudrate=9600,
                timeout=2,
                write_timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Give the Arduino time to initialize
            print("Waiting for Arduino to initialize (2 seconds)...")
            time.sleep(2)
            
            # Clear any existing data in the buffer
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Wait for READY message
            print("Waiting for READY message...")
            response = self.arduino.readline().decode().strip()
            
            if response == "READY":
                print("✅ Arduino is ready!")
                logger.info("Arduino connected successfully and sent READY message")
                self.button = self.arduino  # Set button to arduino connection
                return True
            else:
                print(f"⚠️ Unexpected response: {response}")
                logger.warning(f"Arduino connected but sent unexpected response: {response}")
                self.arduino.close()
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            logger.error(f"Failed to connect to Arduino: {str(e)}")
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            return False

    def check_button(self):
        """Check if button was pressed"""
        try:
            if self.arduino and self.arduino.is_open:
                if self.arduino.in_waiting > 0:
                    data = self.arduino.readline().decode().strip()
                    if data == "1":
                        logger.info("Button pressed detected")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking button: {str(e)}")
            return False

    def _generate_plate_number(self):
        """Generate a unique plate number based on timestamp"""
        return f"RSI{datetime.now().strftime('%H%M%S')}"
        
    def _determine_vehicle_type(self):
        """Randomly determine vehicle type (70% motorcycle, 30% car)"""
        return "Motor" if random.random() < 0.7 else "Mobil"
        
    def _load_counter(self):
        """Load offline counter from file"""
        try:
            with open('counter.txt', 'r') as f:
                return int(f.read().strip())
        except:
            return 1
            
    def _save_counter(self):
        """Save offline counter to file"""
        with open('counter.txt', 'w') as f:
            f.write(str(self.offline_counter))
            
    def _try_server_connection(self):
        """Test connection to parking server"""
        try:
            response = requests.get(f"{API_BASE_URL}/test", timeout=2)
            return response.ok
        except:
            return False
            
    def _get_ticket_from_server(self, plate_number, vehicle_type):
        """Get ticket number from server"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/masuk",
                json={"plat": plate_number, "jenis": vehicle_type},
                headers={"Content-Type": "application/json"},
                timeout=2
            )
            if response.ok:
                result = response.json()
                if result.get('success'):
                    return result['data']
        except Exception as e:
            logger.error(f"Error getting ticket from server: {e}")
        return None
            
    def _check_printer_ready(self):
        """Check if printer is ready before printing"""
        try:
            # Run printer checks
            self.printer_monitor.run_checks()
            
            # Check printer status
            if not self.printer_monitor.check_printer_status():
                logger.error("Printer is not ready")
                return False
                
            # Check system resources
            if not self.printer_monitor.check_system_resources():
                logger.error("System resources are too high")
                return False
                
            # Check active print jobs
            active_jobs = self.printer_monitor.monitor_print_jobs()
            if active_jobs > 0:
                logger.warning(f"Found {active_jobs} active print jobs")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking printer status: {e}")
            return False

    def _print_ticket(self, ticket_data, is_offline=False):
        """Print parking ticket using thermal printer"""
        try:
            # Check printer status before printing
            if not self._check_printer_ready():
                logger.error("Printer is not ready for printing")
                return False

            printer_handle = win32print.OpenPrinter(self.printer_name)
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Prepare commands list
            commands = []
            
            # Header
            commands.extend([
                b"\x1B\x40",          # Initialize printer
                b"\x1B\x61\x01",      # Center alignment
                b"\x1B\x21\x30",      # Double width + height + bold
                b"=== PARKIR RSI BNA ===\n",
                b"\x1B\x21\x00"       # Normal text
            ])
            
            # Add offline indicator if needed
            if is_offline:
                commands.extend([
                    b"\x1B\x21\x08",  # Bold
                    b"[OFFLINE MODE]\n",
                    b"\x1B\x21\x00"   # Normal text
                ])
            
            commands.append(b"\n")
            
            # Ticket details
            commands.extend([
                f"Plat: {ticket_data['plat']}\n".encode(),
                f"Jenis: {ticket_data.get('jenis', '-')}\n".encode(),
                f"Waktu: {ticket_data['waktu_masuk']}\n\n".encode()
            ])
            
            # Print barcode using CODE39
            ticket_number = ticket_data['tiket']
            commands.extend([
                b"\x1D\x48\x02",      # HRI position - below barcode
                b"\x1D\x68\x50",      # Barcode height = 80 dots
                b"\x1D\x77\x02",      # Barcode width multiplier (2)
                b"\x1D\x6B\x04",      # Select CODE39
                bytes([len(ticket_number)]) + ticket_number.encode(),  # Length + data
                b"\n\n"
            ])
            
            # Footer
            commands.extend([
                b"\x1B\x61\x01",      # Center align
                b"Terima kasih\n",
                b"Jangan hilangkan tiket ini\n",
                b"\n",
                b"\x1D\x56\x41\x00"   # Cut paper
            ])
            
            # Combine all commands
            ticket_text = b"".join(commands)
            
            # Send to printer
            win32print.WritePrinter(printer_handle, ticket_text)
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            
            logger.info("Ticket printed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error printing ticket: {e}")
            return False
            
    def _handle_button_press(self):
        """Handle button press event"""
        try:
            # Generate plate number and determine vehicle type
            plate_number = self._generate_plate_number()
            vehicle_type = self._determine_vehicle_type()
            
            logger.info(f"Processing vehicle: {plate_number} ({vehicle_type})")
            
            # Try online mode first
            if self._try_server_connection():
                server_data = self._get_ticket_from_server(plate_number, vehicle_type)
                
                if server_data:
                    # Convert server response to match our format
                    ticket_data = {
                        'plat': server_data['plat'],
                        'jenis': server_data['jenis'],
                        'tiket': server_data.get('ticket', server_data.get('tiket')),  # Handle both keys
                        'waktu_masuk': server_data['waktu']
                    }
                    logger.info(f"Got ticket from server: {ticket_data}")
                    # Print ticket
                    if self._print_ticket(ticket_data):
                        print(f"✅ Kendaraan {plate_number} berhasil masuk")
                        print(f"✅ Tiket dicetak: {ticket_data['tiket']}")
                        return
            
            # Fallback to offline mode
            logger.info("Using offline mode")
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            offline_data = {
                'plat': plate_number,
                'jenis': vehicle_type,
                'tiket': f"OFF{self.offline_counter:06d}",
                'waktu_masuk': current_time
            }
            
            if self._print_ticket(offline_data, is_offline=True):
                print(f"✅ [OFFLINE] Kendaraan {plate_number} berhasil masuk")
                print(f"✅ Tiket dicetak: {offline_data['tiket']}")
                self.offline_counter += 1
                self._save_counter()
            else:
                print(f"❌ Gagal mencetak tiket offline")
                
        except Exception as e:
            logger.error(f"Error handling button press: {e}")
            print(f"❌ Error: {e}")
    
    def start(self):
        """Start listening for button press"""
        print("\nSistem Parkir RSI BNA")
        print("======================")
        print("Mode: Keyboard Input (Arduino tidak terdeteksi)")
        print("Tekan 'p' untuk simulasi kendaraan masuk")
        print("Tekan Ctrl+C untuk keluar\n")
        
        self.running = True
        while self.running:
            try:
                if self.arduino and self.arduino.is_open:
                    # Check Arduino input
                    if self.arduino.in_waiting > 0:
                        data = self.arduino.readline().decode('utf-8').strip()
                        if data:
                            self._handle_button_press()
                else:
                    # Use keyboard input as fallback
                    if input().lower() == 'p':
                        self._handle_button_press()
            except KeyboardInterrupt:
                print("\nMenghentikan sistem...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                print(f"Error: {e}")
                time.sleep(1)  # Prevent rapid error loops
                
    def stop(self):
        """Stop the button handler"""
        self.running = False
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
        logger.info("Button handler stopped")

if __name__ == "__main__":
    try:
        button = ParkingButton(None)  # For standalone testing
        button.start()
    finally:
        if button.arduino and button.arduino.is_open:
            button.arduino.close() 