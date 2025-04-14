import serial
import time
import logging
import os
import sys
import win32print

# Setup logging
logging.basicConfig(
    filename='arduino_direct.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('arduino_direct')

def print_ticket(ticket_number):
    """Cetak tiket dengan nomor tertentu"""
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        if not printer_name:
            print("❌ Tidak ada default printer yang diset")
            return
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\nMencetak tiket:")
        print(f"Nomor: {ticket_number}")
        print(f"Waktu: {timestamp}")
        
        # Buka printer
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            print("✅ Berhasil membuka koneksi printer")
        except Exception as e:
            print(f"❌ Gagal membuka printer: {str(e)}")
            return
            
        try:
            # Start document
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Initialize printer
            win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            
            # Header - double height & width
            win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width & height
            win32print.WritePrinter(printer_handle, b"RSI BANJARNEGARA\n")
            win32print.WritePrinter(printer_handle, b"TIKET PARKIR\n")
            win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
            win32print.WritePrinter(printer_handle, b"================================\n")
            
            # Ticket details - left align, normal text
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x00")  # Left alignment
            win32print.WritePrinter(printer_handle, f"Nomor : {ticket_number}\n".encode())
            win32print.WritePrinter(printer_handle, f"Waktu : {timestamp}\n".encode())
            win32print.WritePrinter(printer_handle, b"================================\n")
            
            # Barcode section - optimized for thermal printer
            win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")  # HRI below barcode
            win32print.WritePrinter(printer_handle, b"\x1D\x68\x50")  # Barcode height = 80 dots
            win32print.WritePrinter(printer_handle, b"\x1D\x77\x02")  # Barcode width = 2
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            
            # Use CODE39 with clear format
            win32print.WritePrinter(printer_handle, b"\x1D\x6B\x04")  # Select CODE39
            
            # Simplify ticket number for better scanning
            simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number  # Ambil hanya nomor urut
            barcode_data = f"*{simple_number}*".encode()  # Format CODE39
            win32print.WritePrinter(printer_handle, barcode_data)
            
            # Extra space after barcode
            win32print.WritePrinter(printer_handle, b"\n\n")
            
            # Footer - center align
            win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
            win32print.WritePrinter(printer_handle, b"Terima kasih\n")
            win32print.WritePrinter(printer_handle, b"Jangan hilangkan tiket ini\n")
            
            # Feed and cut
            win32print.WritePrinter(printer_handle, b"\x1B\x64\x05")  # Feed 5 lines
            win32print.WritePrinter(printer_handle, b"\x1D\x56\x41\x00")  # Cut paper
            
            print("✅ Berhasil mengirim data ke printer")
            
            # Close printer
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            
            print("✅ Tiket berhasil dicetak")
            return True
            
        except Exception as e:
            print(f"❌ Gagal mengirim data ke printer: {str(e)}")
            raise
        
    except Exception as e:
        print(f"❌ Error saat mencetak tiket: {str(e)}")
        return False

def main():
    # Cek apakah ada file arduino_port.txt dan baca port yang tersimpan
    if os.path.exists("arduino_port.txt"):
        with open("arduino_port.txt", "r") as f:
            saved_port = f.read().strip()
    else:
        saved_port = "COM7"  # Default port
    
    print(f"Menggunakan port Arduino: {saved_port}")
    
    # Koneksi ke Arduino
    try:
        ser = serial.Serial(
            port=saved_port,
            baudrate=9600,
            timeout=None  # Tunggu sampai data tersedia
        )
        
        print("✅ Terhubung ke Arduino")
        
        # Bersihkan buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Loop membaca data
        counter = 1
        print("\nMenunggu tombol ditekan pada Arduino...")
        
        while True:
            try:
                # Baca data dari Arduino (blocking)
                line = ser.readline().decode(errors='ignore').strip()
                
                # Log data yang diterima
                if line:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] Data dari Arduino: '{line}'")
                    logger.info(f"Data dari Arduino: '{line}'")
                    
                    # Cek apakah data valid
                    try:
                        # Coba ubah ke integer jika memungkinkan
                        value = int(line)
                        print(f"✅ Nilai tombol terdeteksi: {value}")
                        
                        # Buat nomor tiket
                        ticket_time = time.strftime("%Y%m%d%H%M%S")
                        ticket_number = f"TKT{ticket_time}_{counter:04d}"
                        counter += 1
                        
                        # Cetak tiket
                        print_ticket(ticket_number)
                        
                        print("\nMenunggu tombol ditekan pada Arduino...")
                    except ValueError:
                        # Jika tidak bisa diubah ke integer
                        if "READY" in line or "STATUS" in line:
                            print(f"ℹ️ Status Arduino: {line}")
                        else:
                            print(f"⚠️ Data tidak valid: '{line}'")
            except KeyboardInterrupt:
                # Keluar dari program dengan Ctrl+C
                print("\nProgram dihentikan oleh pengguna")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                logger.error(f"Error: {str(e)}")
                time.sleep(1)  # Delay sebelum mencoba lagi
        
    except Exception as e:
        print(f"❌ Error koneksi ke Arduino: {str(e)}")
        logger.error(f"Error koneksi: {str(e)}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Koneksi Arduino ditutup")

if __name__ == "__main__":
    main() 