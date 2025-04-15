import requests
import json
import logging
import time
from datetime import datetime
import serial
import os
from typing import Tuple, Optional, Dict, Any
import platform
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/parking_exit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Determine if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# Import appropriate GPIO module
if IS_WINDOWS:
    import gpio_simulator as GPIO
    logger.info("Using GPIO simulator for Windows")
else:
    import RPi.GPIO as GPIO
    logger.info("Using RPi.GPIO for Raspberry Pi")

class ParkingExit:
    def __init__(self):
        """Initialize parking exit system"""
        try:
            # GPIO Setup
            GPIO.setmode(GPIO.BCM)
            
            # Pin definitions
            self.BUTTON_PIN = 17      # Push button pin
            self.BARRIER_PIN = 18     # Barrier gate control pin
            self.LED_PIN = 27        # Status LED pin
            self.LOOP_DETECTOR = 22   # Loop detector pin
            
            # Setup pins
            GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.BARRIER_PIN, GPIO.OUT)
            GPIO.setup(self.LED_PIN, GPIO.OUT)
            GPIO.setup(self.LOOP_DETECTOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Initialize barrier gate (closed)
            GPIO.output(self.BARRIER_PIN, GPIO.LOW)
            
            # State flags
            self.barrier_open = False
            self.vehicle_detected = False
            
            # API Configuration
            self.base_url = "http://192.168.2.6:5051"
            self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Barcode scanner setup
            if IS_WINDOWS:
                self.scanner = None
                logger.info("Barcode scanner simulation mode (use keyboard input)")
            else:
                try:
                    self.scanner = serial.Serial(
                        port='/dev/ttyUSB0',
                        baudrate=9600,
                        timeout=1
                    )
                    logger.info("Barcode scanner initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize barcode scanner: {e}")
                    self.scanner = None
            
            # Start loop detector monitoring in a separate thread
            self.loop_detector_thread = threading.Thread(target=self._monitor_loop_detector)
            self.loop_detector_thread.daemon = True
            self.loop_detector_thread.start()
            
            logger.info("Parking exit system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize parking exit system: {e}")
            raise
    
    def _monitor_loop_detector(self):
        """Monitor loop detector state in a separate thread"""
        while True:
            try:
                # Read loop detector state (LOW when vehicle detected)
                current_state = GPIO.input(self.LOOP_DETECTOR)
                
                if current_state == GPIO.LOW and not self.vehicle_detected:
                    # Vehicle just entered the loop
                    self.vehicle_detected = True
                    logger.info("Vehicle detected on loop")
                    print("🚗 Vehicle detected")
                    
                elif current_state == GPIO.HIGH and self.vehicle_detected:
                    # Vehicle just left the loop
                    self.vehicle_detected = False
                    logger.info("Vehicle left the loop")
                    print("🚗 Vehicle passed")
                    
                    # If barrier is open, close it
                    if self.barrier_open:
                        self.close_barrier()
                
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
            except Exception as e:
                logger.error(f"Error in loop detector monitoring: {e}")
                time.sleep(1)  # Wait before retrying
    
    def read_barcode(self):
        """Read barcode from scanner or simulate with keyboard input"""
        try:
            if IS_WINDOWS:
                # Simulate barcode input in Windows
                barcode = input("Enter barcode (press Enter to simulate scan): ").strip()
                if barcode:
                    logger.info(f"Barcode input (simulated): {barcode}")
                    return barcode
                return None
            else:
                if self.scanner and self.scanner.in_waiting:
                    barcode = self.scanner.readline().decode('utf-8').strip()
                    if barcode:
                        logger.info(f"Barcode read: {barcode}")
                        return barcode
                return None
        except Exception as e:
            logger.error(f"Error reading barcode: {e}")
            return None
    
    def process_exit(self, ticket_id):
        """Process vehicle exit with API"""
        try:
            response = requests.post(
                f"{self.base_url}/api/process-exit/",
                json={"ticket_id": ticket_id},
                headers=self.headers
            )
            
            if response.ok:
                data = response.json()
                if data.get('success'):
                    logger.info(f"Exit processed successfully: {data}")
                    return True, data['data']
                else:
                    logger.error(f"Exit processing failed: {data.get('error')}")
                    return False, data.get('error')
            else:
                logger.error(f"API request failed: {response.status_code}")
                return False, f"API error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error processing exit: {e}")
            return False, str(e)
    
    def open_barrier(self):
        """Open the barrier gate"""
        try:
            GPIO.output(self.BARRIER_PIN, GPIO.HIGH)
            GPIO.output(self.LED_PIN, GPIO.HIGH)  # Turn on LED
            self.barrier_open = True
            logger.info("Barrier gate opened")
            print("🔓 Barrier gate opened")
            return True
        except Exception as e:
            logger.error(f"Error opening barrier gate: {e}")
            return False
    
    def close_barrier(self):
        """Close the barrier gate"""
        try:
            GPIO.output(self.BARRIER_PIN, GPIO.LOW)
            GPIO.output(self.LED_PIN, GPIO.LOW)  # Turn off LED
            self.barrier_open = False
            logger.info("Barrier gate closed")
            print("🔒 Barrier gate closed")
            return True
        except Exception as e:
            logger.error(f"Error closing barrier gate: {e}")
            return False
    
    def button_callback(self, channel):
        """Callback function for button press"""
        logger.info("Button pressed - manual exit triggered")
        self.open_barrier()
    
    def run(self):
        """Main loop for parking exit system"""
        try:
            # Setup button interrupt
            GPIO.add_event_detect(self.BUTTON_PIN, GPIO.FALLING, 
                                callback=self.button_callback, bouncetime=2000)
            
            logger.info("Parking exit system started")
            print("\n🚗 Parking Exit System Running")
            if IS_WINDOWS:
                print("Running in Windows simulation mode")
                print("Press '1' to simulate button press")
                print("Press '4' to simulate loop detector (vehicle entering)")
                print("Press '5' to simulate loop detector (vehicle leaving)")
            print("Press Ctrl+C to exit")
            
            while True:
                # Check for barcode
                barcode = self.read_barcode()
                if barcode:
                    print(f"\n📋 Processing ticket: {barcode}")
                    success, result = self.process_exit(barcode)
                    
                    if success:
                        print("✅ Exit authorized")
                        print(f"💰 Fee: Rp {result.get('fee', 0)}")
                        self.open_barrier()
                    else:
                        print(f"❌ Exit failed: {result}")
                
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down parking exit system...")
        except Exception as e:
            logger.error(f"System error: {e}")
            print(f"\n❌ Error: {e}")
        finally:
            if not IS_WINDOWS and self.scanner:
                self.scanner.close()
            GPIO.cleanup()
            print("🔄 System cleanup completed")

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    try:
        parking = ParkingExit()
        parking.run()
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}") 