import os
from PIL import Image
import logging
from datetime import datetime
import json
import shutil

# Setup logging
logging.basicConfig(
    filename='image_compression.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('image_compression')

class ImageManager:
    def __init__(self):
        self.capture_dir = "capture_images"
        self.backup_dir = "capture_images_backup"
        self.archive_dir = "capture_images_archive"
        self.counter_file = "image_counter.json"
        self.counter = self.load_counter()
        
        # Create necessary directories
        for directory in [self.capture_dir, self.backup_dir, self.archive_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Folder dibuat: {directory}")

    def load_counter(self):
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    return json.load(f)
            return {"total_processed": 0}
        except Exception as e:
            logger.error(f"Error loading counter: {str(e)}")
            return {"total_processed": 0}

    def save_counter(self):
        try:
            with open(self.counter_file, 'w') as f:
                json.dump(self.counter, f)
        except Exception as e:
            logger.error(f"Error saving counter: {str(e)}")

    def compress_image(self, input_path, output_path, quality=80, max_size_kb=300):
        """Compress image to target size while maintaining quality"""
        try:
            with Image.open(input_path) as img:
                original_size = os.path.getsize(input_path) / 1024
                logger.info(f"Ukuran asli {input_path}: {original_size:.2f}KB")

                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                new_size = os.path.getsize(output_path) / 1024
                logger.info(f"Ukuran baru {output_path}: {new_size:.2f}KB")
                
                if new_size > max_size_kb and quality > 30:
                    logger.info(f"Gambar masih terlalu besar, mencoba kompresi lebih agresif...")
                    return self.compress_image(input_path, output_path, quality-10, max_size_kb)
                
                return True
        except Exception as e:
            logger.error(f"Error saat mengkompres {input_path}: {str(e)}")
            return False

    def move_to_archive(self):
        """Move processed images to archive when count reaches 3000"""
        if self.counter["total_processed"] % 3000 == 0:
            archive_subfolder = f"batch_{self.counter['total_processed'] // 3000}"
            archive_path = os.path.join(self.archive_dir, archive_subfolder)
            
            if not os.path.exists(archive_path):
                os.makedirs(archive_path)
            
            # Move all processed images to archive
            for filename in os.listdir(self.capture_dir):
                if filename.lower().endswith('.jpg'):
                    src = os.path.join(self.capture_dir, filename)
                    dst = os.path.join(archive_path, filename)
                    try:
                        shutil.move(src, dst)
                        logger.info(f"Moved {filename} to archive: {archive_subfolder}")
                    except Exception as e:
                        logger.error(f"Error moving {filename} to archive: {str(e)}")

    def process_images(self):
        """Process and manage images"""
        image_files = [f for f in os.listdir(self.capture_dir) if f.lower().endswith('.jpg')]
        total_files = len(image_files)
        logger.info(f"Menemukan {total_files} gambar untuk dikompres")

        for i, filename in enumerate(image_files, 1):
            input_path = os.path.join(self.capture_dir, filename)
            output_path = os.path.join(self.capture_dir, filename)
            backup_path = os.path.join(self.backup_dir, filename)

            print(f"\nMemproses gambar {i}/{total_files}: {filename}")
            logger.info(f"Memproses gambar {i}/{total_files}: {filename}")

            # Backup original if not exists
            if not os.path.exists(backup_path):
                shutil.copy2(input_path, backup_path)
                logger.info(f"Backup dibuat: {backup_path}")

            # Compress image
            if self.compress_image(input_path, output_path):
                print(f"✅ Berhasil mengkompres: {filename}")
                self.counter["total_processed"] += 1
                self.save_counter()
            else:
                print(f"❌ Gagal mengkompres: {filename}")

            # Check if we need to archive
            self.move_to_archive()

def main():
    image_manager = ImageManager()
    image_manager.process_images()
    
    print("\nProses kompresi dan pengarsipan selesai!")
    print(f"Backup gambar asli tersimpan di folder: {image_manager.backup_dir}")
    print(f"Gambar terarsip tersimpan di folder: {image_manager.archive_dir}")
    print("Log kompresi tersimpan di: image_compression.log")

if __name__ == "__main__":
    main() 