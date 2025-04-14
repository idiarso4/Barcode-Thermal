import os
import shutil
import time
from datetime import datetime, timedelta
import psutil
import logging

# Setup logging
logging.basicConfig(
    filename='maintenance.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SystemMaintenance:
    def __init__(self):
        self.log_dir = 'logs'
        self.capture_dir = 'capture_images'
        self.max_log_age_days = 7  # Hapus log lebih dari 7 hari
        self.max_capture_age_days = 3  # Hapus capture lebih dari 3 hari
        self.max_log_size_mb = 100  # Maksimum ukuran log file (MB)
        self.max_capture_size_mb = 1000  # Maksimum ukuran folder capture (MB)

    def check_system_resources(self):
        """Monitor system resources"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        logging.info(f"CPU Usage: {cpu_percent}%")
        logging.info(f"Memory Usage: {memory.percent}%")
        logging.info(f"Disk Usage: {disk.percent}%")
        
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            logging.warning("High system resource usage detected!")

    def cleanup_old_files(self):
        """Clean up old log and capture files"""
        current_time = datetime.now()
        
        # Clean up old log files
        if os.path.exists(self.log_dir):
            for log_file in os.listdir(self.log_dir):
                log_path = os.path.join(self.log_dir, log_file)
                if os.path.isfile(log_path):
                    file_age = datetime.fromtimestamp(os.path.getmtime(log_path))
                    if (current_time - file_age).days > self.max_log_age_days:
                        try:
                            os.remove(log_path)
                            logging.info(f"Removed old log file: {log_file}")
                        except Exception as e:
                            logging.error(f"Error removing log file {log_file}: {str(e)}")

        # Clean up old capture files
        if os.path.exists(self.capture_dir):
            for capture_file in os.listdir(self.capture_dir):
                capture_path = os.path.join(self.capture_dir, capture_file)
                if os.path.isfile(capture_path):
                    file_age = datetime.fromtimestamp(os.path.getmtime(capture_path))
                    if (current_time - file_age).days > self.max_capture_age_days:
                        try:
                            os.remove(capture_path)
                            logging.info(f"Removed old capture file: {capture_file}")
                        except Exception as e:
                            logging.error(f"Error removing capture file {capture_file}: {str(e)}")

    def check_file_sizes(self):
        """Check and manage file sizes"""
        # Check log directory size
        if os.path.exists(self.log_dir):
            total_size = sum(os.path.getsize(os.path.join(self.log_dir, f)) 
                           for f in os.listdir(self.log_dir) 
                           if os.path.isfile(os.path.join(self.log_dir, f)))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > self.max_log_size_mb:
                logging.warning(f"Log directory size ({total_size_mb:.2f}MB) exceeds limit")
                self.cleanup_old_files()

        # Check capture directory size
        if os.path.exists(self.capture_dir):
            total_size = sum(os.path.getsize(os.path.join(self.capture_dir, f)) 
                           for f in os.listdir(self.capture_dir) 
                           if os.path.isfile(os.path.join(self.capture_dir, f)))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > self.max_capture_size_mb:
                logging.warning(f"Capture directory size ({total_size_mb:.2f}MB) exceeds limit")
                self.cleanup_old_files()

    def run_maintenance(self):
        """Run all maintenance tasks"""
        logging.info("Starting maintenance tasks...")
        self.check_system_resources()
        self.cleanup_old_files()
        self.check_file_sizes()
        logging.info("Maintenance tasks completed")

if __name__ == "__main__":
    maintenance = SystemMaintenance()
    maintenance.run_maintenance() 