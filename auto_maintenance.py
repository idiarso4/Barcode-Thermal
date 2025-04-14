import os
import time
import json
from maintenance import SystemMaintenance

class AutoMaintenance:
    def __init__(self):
        self.counter_file = 'counter.txt'
        self.maintenance = SystemMaintenance()
        self.vehicle_count = 0
        self.load_counter()

    def load_counter(self):
        """Load vehicle count from file"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    self.vehicle_count = int(f.read().strip())
        except Exception as e:
            print(f"Error loading counter: {str(e)}")
            self.vehicle_count = 0

    def save_counter(self):
        """Save vehicle count to file"""
        try:
            with open(self.counter_file, 'w') as f:
                f.write(str(self.vehicle_count))
        except Exception as e:
            print(f"Error saving counter: {str(e)}")

    def increment_counter(self):
        """Increment vehicle count and check for maintenance"""
        self.vehicle_count += 1
        self.save_counter()
        
        # Run maintenance every 1000 vehicles
        if self.vehicle_count % 1000 == 0:
            print(f"Vehicle count reached {self.vehicle_count}, running maintenance...")
            self.maintenance.run_maintenance()
            print("Maintenance completed")

    def run(self):
        """Main loop to monitor vehicle count"""
        print("Auto maintenance system started")
        print(f"Current vehicle count: {self.vehicle_count}")
        
        try:
            while True:
                # Simulate vehicle detection (replace with actual vehicle detection logic)
                time.sleep(1)  # Check every second
                self.increment_counter()
        except KeyboardInterrupt:
            print("\nAuto maintenance system stopped")

if __name__ == "__main__":
    auto_maintenance = AutoMaintenance()
    auto_maintenance.run() 