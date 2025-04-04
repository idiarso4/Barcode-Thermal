import os
from datetime import datetime
import barcode
from barcode import Code39
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code39
from reportlab.lib.pagesizes import A4

def generate_ticket_number():
    """Generate nomor tiket dengan format yang sama dengan sistem parkir"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    counter = "1234"
    return f"TKT{timestamp}-{counter}"

def create_barcode_image(ticket_number, output_dir="sample_barcodes"):
    """Buat barcode dalam format PNG"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Generate barcode image dengan python-barcode
    code39_barcode = Code39(ticket_number, writer=ImageWriter(), add_checksum=False)
    filename = code39_barcode.save(os.path.join(output_dir, f"barcode_{ticket_number}"))
    print(f"✓ Barcode image disimpan: {filename}")
    return filename

def create_barcode_pdf(ticket_number, output_dir="sample_barcodes"):
    """Buat tiket parkir lengkap dengan barcode dalam PDF"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    pdf_file = os.path.join(output_dir, f"ticket_{ticket_number}.pdf")
    c = canvas.Canvas(pdf_file, pagesize=A4)
    
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(A4[0]/2, 280*mm, "RSI BANJARNEGARA")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(A4[0]/2, 273*mm, "TIKET PARKIR")
    
    # Garis pemisah
    c.line(30*mm, 270*mm, 180*mm, 270*mm)
    
    # Informasi tiket
    c.setFont("Helvetica", 10)
    timestamp = datetime.now()
    c.drawString(40*mm, 260*mm, f"Tanggal : {timestamp.strftime('%d-%m-%Y')}")
    c.drawString(40*mm, 255*mm, f"Jam     : {timestamp.strftime('%H:%M:%S')}")
    c.drawString(40*mm, 250*mm, f"No.     : {ticket_number}")
    
    # Barcode
    barcode_code39 = code39.Standard39(ticket_number, barHeight=20*mm, barWidth=0.5*mm, checksum=0)
    barcode_code39.drawOn(c, 40*mm, 220*mm)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(A4[0]/2, 210*mm, "Simpan tiket ini dengan baik")
    
    c.save()
    print(f"✓ PDF tiket disimpan: {pdf_file}")
    return pdf_file

def main():
    print("\nMembuat Contoh Barcode untuk Testing")
    print("=" * 40)
    
    # Generate nomor tiket
    ticket_number = generate_ticket_number()
    print(f"\nNomor Tiket: {ticket_number}")
    
    # Buat output dalam berbagai format
    print("\nMembuat barcode dalam berbagai format...")
    img_file = create_barcode_image(ticket_number)
    pdf_file = create_barcode_pdf(ticket_number)
    
    print("\nFile yang dihasilkan:")
    print(f"1. Image (PNG): {img_file}")
    print(f"2. PDF Tiket : {pdf_file}")
    
    print("\nCara penggunaan:")
    print("1. Cetak file PDF untuk contoh tiket lengkap")
    print("2. Atau cetak file PNG untuk barcode saja")
    print("3. Test dengan scanner barcode")
    print("4. Pastikan scanner diset ke mode CODE39")
    print("\nTips scanning:")
    print("- Jaga agar hasil cetakan bersih")
    print("- Hindari lipatan pada barcode")
    print("- Scanner harus bisa membaca CODE39")
    print("- Jika scanner tidak membaca, coba sesuaikan:")
    print("  * Tinggi barcode")
    print("  * Ketebalan garis")
    print("  * Kontras cetakan")

if __name__ == "__main__":
    main() 