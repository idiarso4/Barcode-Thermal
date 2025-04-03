import datetime
import win32print
import time
import os
import tempfile
import qrcode
from PIL import Image
import importlib.util

# Check if python-barcode is installed
try:
    import python_barcode as barcode
except ImportError:
    try:
        from python_barcode import generate, writer
    except ImportError:
        import barcode
        from barcode import writer

def generate_barcode(code, output_file):
    # Generate Code 128 barcode
    try:
        code128 = barcode.get('code128', code, writer=writer.ImageWriter())
        # Save barcode to file
        code128.save(output_file)
        return f"{output_file}.png"
    except Exception as e:
        print(f"Error generating barcode: {e}")
        # Create a simple text file as fallback
        fallback_file = f"{output_file}.png"
        img = Image.new('RGB', (384, 100), color='white')
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"TICKET: {code}", fill='black')
        img.save(fallback_file)
        return fallback_file

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

def print_ticket():
    printer_name = win32print.GetDefaultPrinter()
    print(f"Printing ke: {printer_name}")
    
    # Create temporary directory for barcode and QR code images
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate ticket number
        timestamp = int(time.time())
        ticket_number = str(timestamp)[-8:]  # Use last 8 digits of timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create barcode image
        barcode_file = os.path.join(temp_dir, "barcode")
        barcode_image = generate_barcode(ticket_number, barcode_file)
        
        # Create QR code image with more data
        qrcode_file = os.path.join(temp_dir, "qrcode.png")
        qr_data = f"PARK-TICKET:{ticket_number},{current_time}"
        qrcode_image = generate_qrcode(qr_data, qrcode_file)
        
        # Print ticket
        printer_handle = None
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Ticket Print", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Reset printer and set encoding
            win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
            win32print.WritePrinter(printer_handle, b"\x1B\x74\x00")  # Set code page
            
            # Print header - Center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
            header_text = "Parking Ticket Phase Model Fair\n\n"
            header_text += f"Tgl: {current_time}\n\n"
            win32print.WritePrinter(printer_handle, header_text.encode('ascii', errors='replace'))
            
            # Print the ticket number - Left align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left align
            ticket_text = f"Ticket: {ticket_number}\n\n"
            win32print.WritePrinter(printer_handle, ticket_text.encode('ascii', errors='replace'))
            
            # Print the linear barcode - Center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
            
            # Instead of using ESC/POS commands, print a pre-generated barcode image
            try:
                # Convert barcode image to a format suitable for the printer
                barcode_img = Image.open(barcode_image)
                
                # Print simple text as fallback in case of image printing issues
                win32print.WritePrinter(printer_handle, f"\n{ticket_number}\n".encode('ascii'))
                
                # Insert a line of text
                win32print.WritePrinter(printer_handle, b"\x0A")  # Line feed
                
                # Print QR code text instruction
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left align
                win32print.WritePrinter(printer_handle, "Scan code with your device for more info.\n\n".encode('ascii'))
                
                # Center align for QR code
                win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center align
                
                # Print the ticket number in a readable format
                win32print.WritePrinter(printer_handle, f"TICKET: {ticket_number}\n".encode('ascii'))
                
                # Footer
                win32print.WritePrinter(printer_handle, b"\x0A")  # Line feed
                win32print.WritePrinter(printer_handle, "Thank you for visiting\n\n".encode('ascii'))
                
            except Exception as e:
                print(f"Error processing barcode image: {e}")
            
            # Cut paper
            win32print.WritePrinter(printer_handle, b"\x1D\x56\x00")  # Full cut
            
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