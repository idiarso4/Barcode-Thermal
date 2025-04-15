import os
import tempfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import win32print
import win32ui
from django.conf import settings

class ReceiptPrinter:
    def __init__(self):
        self.receipt_width = 380
        self.margin = 20
        self.line_height = 25
        
        # Load font
        try:
            font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
            self.font_header = ImageFont.truetype(font_path, 20)
            self.font_normal = ImageFont.truetype(font_path, 16)
        except:
            self.font_header = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
    
    def create_receipt_image(self, data):
        """Membuat gambar struk pembayaran"""
        # Hitung tinggi struk berdasarkan konten
        content_height = len(data.keys()) * self.line_height + 100
        
        # Buat gambar dengan background putih
        image = Image.new('RGB', (self.receipt_width, content_height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Header struk
        y = self.margin
        draw.text((self.margin, y), "STRUK PEMBAYARAN PARKIR", font=self.font_header, fill='black')
        y += self.line_height * 1.5
        
        # Informasi transaksi
        items = [
            ('No. Transaksi', data['transaction_id']),
            ('Tanggal', data['datetime']),
            ('No. Tiket', data['ticket_id']),
            ('Plat Nomor', data['vehicle']),
            ('Jenis Kendaraan', data['vehicle_type']),
            ('Waktu Masuk', data['entry_time']),
            ('Durasi', data['duration']),
            ('Tarif', f"Rp {data['fee']:,.0f}"),
            ('Dibayar', f"Rp {data['amount_paid']:,.0f}"),
            ('Kembalian', f"Rp {data['change']:,.0f}"),
            ('Metode', data['payment_method']),
            ('Operator', data['operator'])
        ]
        
        for label, value in items:
            draw.text((self.margin, y), label, font=self.font_normal, fill='black')
            draw.text((self.receipt_width//2, y), ': ' + str(value), font=self.font_normal, fill='black')
            y += self.line_height
        
        # Catatan jika ada
        if data.get('notes'):
            y += self.line_height//2
            draw.text((self.margin, y), "Catatan:", font=self.font_normal, fill='black')
            y += self.line_height
            draw.text((self.margin, y), data['notes'], font=self.font_normal, fill='black')
            y += self.line_height
        
        # Footer
        y += self.line_height
        draw.text((self.margin, y), "Terima kasih atas kunjungan Anda", font=self.font_normal, fill='black')
        
        return image
    
    def print_receipt(self, data):
        """Mencetak struk pembayaran"""
        try:
            # Buat gambar struk
            image = self.create_receipt_image(data)
            
            # Simpan ke file temporary
            temp_file = os.path.join(tempfile.gettempdir(), f"receipt_{data['transaction_id']}.png")
            image.save(temp_file)
            
            # Cetak menggunakan printer default
            printer_name = win32print.GetDefaultPrinter()
            
            # Buka printer
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                # Mulai dokumen
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)
                hdc.StartDoc('Struk Parkir')
                hdc.StartPage()
                
                # Cetak gambar
                dib = ImageWin.Dib(image)
                dib.draw(hdc.GetHandleOutput(), (0, 0, self.receipt_width, image.size[1]))
                
                # Selesai
                hdc.EndPage()
                hdc.EndDoc()
                hdc.DeleteDC()
                
                return True
            finally:
                win32print.ClosePrinter(hprinter)
                
                # Hapus file temporary
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        except Exception as e:
            print(f"Error mencetak struk: {str(e)}")
            return False 