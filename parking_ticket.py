import os
from datetime import datetime
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import psycopg2
from psycopg2 import Error

class ParkingTicket:
    def __init__(self):
        self.ticket_width = 400
        self.ticket_height = 600
        self.margin = 20
        # Database connection details
        self.db_config = {
            "host": "192.168.2.6",
            "port": "5432",
            "database": "parkir2",
            "user": "postgres",
            "password": "postgres"
        }

    def connect_db(self):
        """Create database connection"""
        try:
            connection = psycopg2.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return None

    def save_to_database(self, ticket_number, plate_number):
        """Save ticket information to database"""
        connection = self.connect_db()
        if connection:
            try:
                cursor = connection.cursor()
                # Assuming we have a table named 'parking_tickets'
                insert_query = """
                INSERT INTO parking_tickets 
                (ticket_number, plate_number, entry_time, status) 
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    ticket_number,
                    plate_number,
                    datetime.now(),
                    'ACTIVE'
                ))
                connection.commit()
                return True
            except Error as e:
                print(f"Error saving to database: {e}")
                return False
            finally:
                if connection:
                    cursor.close()
                    connection.close()
        return False

    def generate_ticket_number(self):
        """Generate unique ticket number based on timestamp"""
        return datetime.now().strftime('PKR%Y%m%d%H%M%S')

    def create_ticket(self, plate_number):
        """Create parking ticket with barcode"""
        # Create blank ticket
        ticket = Image.new('RGB', (self.ticket_width, self.ticket_height), 'white')
        draw = ImageDraw.Draw(ticket)

        # Generate ticket number
        ticket_number = self.generate_ticket_number()

        try:
            # Generate barcode
            barcode = Code128(ticket_number, writer=ImageWriter())
            barcode_path = f"barcode_{ticket_number}"
            barcode.save(barcode_path)

            # Open and resize barcode image
            barcode_img = Image.open(f"{barcode_path}.png")
            barcode_img = barcode_img.resize((360, 100))

            # Add barcode to ticket
            ticket.paste(barcode_img, (self.margin, 200))

            # Add text information
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()

            # Add ticket details
            draw.text((self.margin, 50), "KARCIS PARKIR", font=font, fill='black')
            draw.text((self.margin, 100), f"No. Plat: {plate_number}", font=font, fill='black')
            draw.text((self.margin, 150), f"No. Tiket: {ticket_number}", font=font, fill='black')
            draw.text((self.margin, 320), f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                     font=font, fill='black')

            # Save the ticket image
            ticket_path = f"ticket_{ticket_number}.png"
            ticket.save(ticket_path)

            # Clean up temporary barcode file
            os.remove(f"{barcode_path}.png")

            # Save ticket information to database
            if self.save_to_database(ticket_number, plate_number):
                print("Ticket saved to database successfully")
            else:
                print("Failed to save ticket to database")

            return ticket_path

        except Exception as e:
            print(f"Error creating ticket: {str(e)}")
            return None

# Example usage
if __name__ == "__main__":
    parking_ticket = ParkingTicket()
    ticket_path = parking_ticket.create_ticket("B 1234 XYZ")
    if ticket_path:
        print(f"Ticket created successfully: {ticket_path}")
    else:
        print("Failed to create ticket") 