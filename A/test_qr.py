import datetime
import win32print
import time
import os
import tempfile
import barcode
from barcode import writer
import qrcode
from PIL import Image

def generate_barcode(code, output_file):
    # Generate Code 128 barcode
    code128 = barcode.get('code128', code, writer=writer.ImageWriter())
    # Save barcode to file
    code128.save(output_file)
    return f"{output_file}.png"

def generate_qrcode(data, output_file):
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create an image from the QR code
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_file)
    return output_file

def print_image(printer_name, image_path):
    # Print an image using the specified printer
    printer_handle = win32print.OpenPrinter(printer_name)
    try:
        # Open raw mode
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Image Print", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Convert the image to bytes
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Write the image data to the printer
        win32print.WritePrinter(printer_handle, image_data)
        
        # End the page and document
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
    finally:
        win32print.ClosePrinter(printer_handle)

def print_ticket():
    printer_name = win32print.GetDefaultPrinter()
    print(f"Printing ke: {printer_name}")
    
    # Create temporary directory for barcode and QR code images
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate ticket number
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-8:]
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create barcode image
        barcode_file = os.path.join(temp_dir, "barcode")
        barcode_image = generate_barcode(ticket_number, barcode_file)
        
        # Create QR code image with more data
        qrcode_file = os.path.join(temp_dir, "qrcode.png")
        qr_data = f"PARK-TICKET:{ticket_number},{current_time}"
        qrcode_image = generate_qrcode(qr_data, qrcode_file)
        
        # Print ticket header
        printer_handle = None
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Ticket Print", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Reset printer and set encoding
            win32print.WritePrinter(printer_handle, b"\x1B\x40")
            win32print.WritePrinter(printer_handle, b"\x1B\x74\x00")
            
            # Header - Center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")
            header_text = f"Parking Ticket Phase Model Fair\n\n"
            header_text += f"Tgl: {current_time}\n\n"
            win32print.WritePrinter(printer_handle, header_text.encode('ascii', errors='replace'))
            
            # Print barcode (using ESC/POS commands to print the image)
            # Resize and convert barcode image
            barcode_img = Image.open(barcode_image)
            # Scale to appropriate width for thermal printer (typically 384 or 576 pixels)
            width = 384
            ratio = width / barcode_img.width
            height = int(barcode_img.height * ratio)
            barcode_img = barcode_img.resize((width, height))
            
            # Save as bitmap
            barcode_bmp = os.path.join(temp_dir, "barcode.bmp")
            barcode_img.save(barcode_bmp)
            
            # Print the barcode image
            with open(barcode_bmp, 'rb') as f:
                barcode_data = f.read()
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
                win32print.WritePrinter(printer_handle, barcode_data)
            
            # Space after barcode
            win32print.WritePrinter(printer_handle, b"\x0A\x0A")
            
            # Additional information - Left align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")
            additional_text = "Scan code with your device for more info.\n\n"
            win32print.WritePrinter(printer_handle, additional_text.encode('ascii', errors='replace'))
            
            # Print QR code
            qr_img = Image.open(qrcode_image)
            # Resize for thermal printer
            qr_img = qr_img.resize((200, 200))
            qr_bmp = os.path.join(temp_dir, "qrcode.bmp")
            qr_img.save(qr_bmp)
            
            with open(qr_bmp, 'rb') as f:
                qr_data = f.read()
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
                win32print.WritePrinter(printer_handle, qr_data)
            
            # Footer
            win32print.WritePrinter(printer_handle, b"\x0A\x0A")
            footer_text = "Thank you for visiting\n\n"
            win32print.WritePrinter(printer_handle, footer_text.encode('ascii', errors='replace'))
            
            # Cut paper
            win32print.WritePrinter(printer_handle, b"\x1D\x56\x00")
            
            # End printing
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            print("Ticket berhasil di print!")
            
        except Exception as e:
            print(f"Error printing ticket: {e}")
        finally:
            if printer_handle:
                try:
                    win32print.ClosePrinter(printer_handle)
                except Exception as e:
                    print(f"Error closing printer handle: {e}")
    
    finally:
        # Clean up temporary files
        try:
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

if __name__ == "__main__":
    print_ticket() 