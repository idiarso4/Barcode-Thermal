from escpos import printer
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import os
import tempfile
from datetime import datetime
from config import PRINTER_CONFIG

class TicketPrinter:
    def __init__(self):
        self.printer = printer.File(PRINTER_CONFIG['port'])
    
    def generate_barcode_image(self, ticket_number):
        # Generate Code128 barcode
        code128 = barcode.get_barcode_class('code128')
        
        # Create temporary file for barcode image
        temp_dir = tempfile.gettempdir()
        barcode_file = os.path.join(temp_dir, f"barcode_{ticket_number}")
        
        # Generate barcode image
        barcode_instance = code128(ticket_number, writer=ImageWriter())
        barcode_path = barcode_instance.save(barcode_file)
        
        # Open and resize barcode image
        img = Image.open(barcode_path)
        # Resize to fit printer width (adjust size as needed)
        img = img.resize((380, 100))
        
        return barcode_path, img
    
    def print_ticket(self, ticket_data):
        """
        Print parking ticket with barcode
        ticket_data should contain:
        - ticket_number
        - plate_number
        - entry_time
        - vehicle_type
        """
        try:
            # Generate barcode
            barcode_path, _ = self.generate_barcode_image(ticket_data['ticket_number'])
            
            # Start printing
            self.printer.set(align='center')
            
            # Print header
            self.printer.text("================================\n")
            self.printer.set(height=2, width=2)
            self.printer.text("PARKING TICKET\n")
            self.printer.set(height=1, width=1)
            self.printer.text("================================\n\n")
            
            # Print ticket details
            self.printer.set(align='left')
            self.printer.text(f"Ticket No : {ticket_data['ticket_number']}\n")
            self.printer.text(f"Plate No  : {ticket_data['plate_number']}\n")
            self.printer.text(f"Time In   : {ticket_data['entry_time']}\n")
            self.printer.text(f"Type      : {ticket_data['vehicle_type']}\n\n")
            
            # Print barcode
            self.printer.set(align='center')
            # Print barcode using native printer command
            self.printer.barcode(ticket_data['ticket_number'], 'CODE128', function_type='B')
            
            # Also print barcode image for backup
            self.printer.image(barcode_path)
            
            # Print footer
            self.printer.text("\n================================\n")
            self.printer.text("Please keep this ticket safe\n")
            self.printer.text("Lost ticket will be fined\n")
            self.printer.text("================================\n\n\n")
            
            # Cut paper
            self.printer.cut()
            
            # Clean up temporary barcode file
            if os.path.exists(barcode_path):
                os.remove(barcode_path)
                
            return True
            
        except Exception as e:
            print(f"Error printing ticket: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    # Test ticket printing
    printer = TicketPrinter()
    test_data = {
        'ticket_number': 'PKR-001-123',
        'plate_number': 'B 1234 CD',
        'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'vehicle_type': 'Car'
    }
    printer.print_ticket(test_data) 