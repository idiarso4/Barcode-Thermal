import os
from datetime import datetime
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import logging
import tempfile

logger = logging.getLogger(__name__)

class TicketPrinter:
    def __init__(self):
        self.ticket_width = 400
        self.ticket_height = 600
        self.margin = 20
        
        # Try to load Arial font, fallback to default if not available
        try:
            self.font_header = ImageFont.truetype("arial.ttf", 24)
            self.font_normal = ImageFont.truetype("arial.ttf", 20)
        except:
            self.font_header = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
        
        self.temp_dir = tempfile.gettempdir()
        logger.info("Ticket printer initialized")

    def generate_barcode(self, data):
        """Generate barcode image
        
        Args:
            data: String to encode in barcode
            
        Returns:
            Path to generated barcode image
        """
        try:
            # Generate Code128 barcode
            code128 = Code128(data, writer=ImageWriter())
            
            # Save barcode to temp file
            barcode_path = os.path.join(self.temp_dir, f"barcode_{data}")
            code128.save(barcode_path)
            
            return f"{barcode_path}.png"
        except Exception as e:
            logger.error(f"Failed to generate barcode: {e}")
            raise
    
    def create_ticket_image(self, ticket_data):
        """Create ticket image with text and barcode
        
        Args:
            ticket_data: Dictionary containing ticket information
            
        Returns:
            Path to generated ticket image
        """
        try:
            # Create blank ticket with white background
            ticket = Image.new('RGB', (self.ticket_width, self.ticket_height), 'white')
            draw = ImageDraw.Draw(ticket)

            # Add header text
            header_text = "PARKIR RSI BANJARNEGARA"
            header_bbox = draw.textbbox((0, 0), header_text, font=self.font_header)
            header_width = header_bbox[2] - header_bbox[0]
            draw.text(
                ((self.ticket_width - header_width) // 2, self.margin),
                header_text,
                font=self.font_header,
                fill='black'
            )

            # Generate barcode
            barcode_path = self.generate_barcode(ticket_data['plate_number'])
            barcode_img = Image.open(barcode_path)

            # Calculate vertical positions
            current_y = 80  # Start after header
            line_spacing = 30

            # Add ticket details
            details = [
                f"Nomor Plat : {ticket_data.get('plate_number', 'N/A')}",
                f"Jenis      : {ticket_data.get('vehicle_type', 'N/A')}",
                f"Masuk      : {ticket_data.get('entry_time', 'N/A')}"
            ]

            for detail in details:
                draw.text(
                    (self.margin, current_y),
                    detail,
                    font=self.font_normal,
                    fill='black'
                )
                current_y += line_spacing

            # Add barcode image - centered
            barcode_x = (self.ticket_width - 360) // 2
            barcode_y = current_y + 20
            ticket.paste(barcode_img.resize((360, 100)), (barcode_x, barcode_y))

            # Add footer text
            footer_y = barcode_y + 100 + 20
            footer_text = "Terima kasih atas kunjungan Anda"
            footer_bbox = draw.textbbox((0, 0), footer_text, font=self.font_normal)
            footer_width = footer_bbox[2] - footer_bbox[0]
            draw.text(
                ((self.ticket_width - footer_width) // 2, footer_y),
                footer_text,
                font=self.font_normal,
                fill='black'
            )

            # Save the ticket
            ticket_path = os.path.join(self.temp_dir, f"ticket_{ticket_data['plate_number']}.png")
            ticket.save(ticket_path)

            # Clean up temporary barcode file
            try:
                os.remove(barcode_path)
            except:
                pass

            logger.info(f"Ticket created successfully: {ticket_path}")
            return ticket_path

        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            raise

    def print_ticket(self, ticket_data):
        """Print parking ticket
        
        Args:
            ticket_data: Dictionary containing ticket information
        """
        try:
            # Generate ticket image
            ticket_path = self.create_ticket_image(ticket_data)
            
            # Print ticket (in simulation, just show the path)
            print(f"\nTiket tersimpan di: {ticket_path}")
            print("Dalam implementasi nyata, tiket akan dicetak ke printer thermal")
            
            # In real implementation, would send to printer here
            # self.send_to_printer(ticket_path)
            
        except Exception as e:
            logger.error(f"Failed to print ticket: {e}")
            raise
    
    def send_to_printer(self, image_path):
        """Send image to printer (placeholder for real implementation)"""
        # This would contain the actual printer implementation
        # For example, using python-escpos for thermal printer
        pass

# Test the ticket printer
if __name__ == "__main__":
    # Create sample ticket data
    sample_data = {
        "plate_number": "B 1234 XY",
        "vehicle_type": "Motor",
        "entry_time": "2024-03-19 12:34:56"
    }
    
    # Create and print test ticket
    printer = TicketPrinter()
    try:
        ticket_path = printer.create_ticket_image(sample_data)
        printer.print_ticket(sample_data)
    except Exception as e:
        print(f"Error creating test ticket: {e}") 