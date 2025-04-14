import win32print
import time
import os

def check_printer_queue():
    """Periksa antrian print dan bersihkan"""
    try:
        print("Memeriksa antrian printer...")
        # Buka printer default
        printer_name = win32print.GetDefaultPrinter()
        if not printer_name:
            print("❌ Tidak ada default printer yang diset")
            return
            
        print(f"Default printer: {printer_name}")
        
        # Dapatkan informasi detail printer
        printer_handle = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(printer_handle, 2)
        
        # Tampilkan status printer
        status = printer_info['Status']
        status_messages = {
            0: "Ready / Idle",
            1: "Paused",
            2: "Error",
            3: "Pending Deletion",
            4: "Paper Jam",
            5: "Out of Paper",
            6: "Manual Feed Required",
            7: "Paper Problem",
            8: "Offline",
            256: "IO Active",
            512: "Busy",
            1024: "Printing",
            4096: "Initializing",
            8192: "Warming Up",
            16384: "Toner/Ink Low",
            32768: "No Toner/Ink",
            65536: "Page Punt (Unable to Print Page)",
            131072: "User Intervention Required",
            262144: "Out of Memory",
            524288: "Door Open",
            1048576: "Server Unknown",
            2097152: "Power Save",
        }
        
        print(f"Status Printer: {status} - ", end="")
        for bit, message in status_messages.items():
            if status & bit:
                print(message, end=" ")
        print()
        
        # Tampilkan jobs dalam antrian
        jobs = win32print.EnumJobs(printer_handle, 0, 999)
        if jobs:
            print(f"Antrian printer memiliki {len(jobs)} jobs:")
            for job in jobs:
                print(f"  - Job {job['JobId']}: {job['Document']} ({job['Status']})")
            
            # Tanyakan apakah ingin membersihkan antrian
            response = input("Bersihkan antrian printer? (y/n): ")
            if response.lower() == 'y':
                print("Membersihkan antrian printer...")
                for job in jobs:
                    try:
                        win32print.SetJob(printer_handle, job['JobId'], 0, None, win32print.JOB_CONTROL_DELETE)
                        print(f"  ✅ Job {job['JobId']} dihapus")
                    except Exception as e:
                        print(f"  ❌ Error menghapus job {job['JobId']}: {str(e)}")
        else:
            print("Antrian printer kosong")
            
        win32print.ClosePrinter(printer_handle)
        
    except Exception as e:
        print(f"❌ Error memeriksa antrian: {str(e)}")

def print_test_page():
    """Cetak halaman test sederhana"""
    try:
        # Get default printer
        printer_name = win32print.GetDefaultPrinter()
        if not printer_name:
            print("❌ Tidak ada default printer yang diset")
            return False
            
        print(f"Mencetak test page ke printer: {printer_name}")
        
        # Buka printer
        printer_handle = win32print.OpenPrinter(printer_name)
        
        # Start document
        job_id = win32print.StartDocPrinter(printer_handle, 1, ("Test Page", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        
        # Initialize printer
        win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
        win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
        
        # Header - double height & width
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width & height
        win32print.WritePrinter(printer_handle, b"TEST PRINTER\n")
        win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
        win32print.WritePrinter(printer_handle, b"================\n\n")
        
        # Print some text
        win32print.WritePrinter(printer_handle, b"Ini adalah test halaman\n")
        win32print.WritePrinter(printer_handle, b"Jika teks ini tercetak\n")
        win32print.WritePrinter(printer_handle, b"maka printer berfungsi\n")
        win32print.WritePrinter(printer_handle, b"dengan baik.\n\n")
        
        # Print timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        win32print.WritePrinter(printer_handle, f"Waktu: {timestamp}\n\n".encode())
        
        # Feed and cut
        win32print.WritePrinter(printer_handle, b"\x1B\x64\x05")  # Feed 5 lines
        win32print.WritePrinter(printer_handle, b"\x1D\x56\x41\x00")  # Cut paper
        
        # Close printer
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        
        print("✅ Test page berhasil dikirim ke printer")
        return True
        
    except Exception as e:
        print(f"❌ Error saat mencetak test page: {str(e)}")
        return False

def print_via_file():
    """Cetak menggunakan file perantara"""
    try:
        print("\nMencoba alternatif mencetak via file perantara...")
        
        # Buat file temporer dengan perintah ESC/POS
        temp_file = "temp_print.prn"
        with open(temp_file, "wb") as f:
            # Initialize printer
            f.write(b"\x1B\x40")  # Initialize printer
            f.write(b"\x1B\x61\x01")  # Center alignment
            
            # Header - double height & width
            f.write(b"\x1B\x21\x30")  # Double width & height
            f.write(b"TEST PRINTER\n")
            f.write(b"\x1B\x21\x00")  # Normal text
            f.write(b"================\n\n")
            
            # Print some text
            f.write(b"Metode Alternatif\n")
            f.write(b"Cetak via File\n\n")
            
            # Print timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Waktu: {timestamp}\n\n".encode())
            
            # Feed and cut
            f.write(b"\x1B\x64\x05")  # Feed 5 lines
            f.write(b"\x1D\x56\x41\x00")  # Cut paper
        
        # Dapatkan default printer
        printer_name = win32print.GetDefaultPrinter()
        if not printer_name:
            print("❌ Tidak ada default printer yang diset")
            return False
        
        print(f"Mengirim file ke printer: {printer_name}")
        
        # Kirim file ke printer menggunakan command line
        os.system(f'copy /b "{temp_file}" "{printer_name}"')
        
        print("✅ File berhasil dikirim ke printer")
        
        # Hapus file temporer
        try:
            os.remove(temp_file)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"❌ Error saat mencetak via file: {str(e)}")
        return False

def main():
    print("\n=== SISTEM TEST PRINTER ===\n")
    
    # Periksa antrian printer
    check_printer_queue()
    
    print("\n=== MENU TEST PRINTER ===")
    print("1. Cetak test page (metode RAW)")
    print("2. Cetak test page (metode file)")
    print("3. Keluar")
    
    while True:
        choice = input("\nPilih menu (1-3): ")
        
        if choice == '1':
            print_test_page()
        elif choice == '2':
            print_via_file()
        elif choice == '3':
            print("Program dihentikan.")
            break
        else:
            print("Pilihan tidak valid! Silahkan pilih 1-3.")

if __name__ == "__main__":
    main() 