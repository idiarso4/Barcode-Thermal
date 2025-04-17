# Dokumentasi Implementasi Tiket Parkir

## Komponen Kritis yang Harus Ada

### 1. Dependensi yang Diperlukan
```python
import win32print
import barcode
from barcode.writer import ImageWriter
```

### 2. Konfigurasi Printer
- Printer harus diset sebagai default printer di Windows
- Printer thermal harus mendukung ESC/POS commands
- Driver printer harus terinstall dengan benar

### 3. Format Barcode yang Benar
```python
# Konfigurasi barcode yang terbukti berhasil:
win32print.WritePrinter(printer_handle, b"\x1D\x48\x02")  # HRI below barcode
win32print.WritePrinter(printer_handle, b"\x1D\x68\x50")  # Barcode height = 80 dots
win32print.WritePrinter(printer_handle, b"\x1D\x77\x02")  # Barcode width = 2
win32print.WritePrinter(printer_handle, b"\x1D\x6B\x04")  # Select CODE39

# Format data barcode yang benar
simple_number = ticket_number.split('_')[1] if '_' in ticket_number else ticket_number[-10:]
barcode_data = f"*{simple_number}*".encode()  # Format CODE39 dengan asterisk
```

### 4. Urutan Perintah yang Harus Dipatuhi
1. Initialize printer
```python
win32print.WritePrinter(printer_handle, b"\x1B\x40")  # Initialize printer
```

2. Set alignment sebelum header
```python
win32print.WritePrinter(printer_handle, b"\x1B\x61\x01")  # Center alignment
```

3. Set text size untuk header
```python
win32print.WritePrinter(printer_handle, b"\x1B\x21\x30")  # Double width/height
```

4. Reset text size sebelum barcode
```python
win32print.WritePrinter(printer_handle, b"\x1B\x21\x00")  # Normal text
```

5. Kirim data barcode setelah konfigurasi

6. Feed dan cut paper di akhir
```python
win32print.WritePrinter(printer_handle, b"\x1B\x64\x05")  # Feed 5 lines
win32print.WritePrinter(printer_handle, b"\x1D\x56\x41\x00")  # Cut paper
```

### 5. Penanganan Printer yang Benar
```python
# Buka printer
printer_handle = win32print.OpenPrinter(self.printer_name)

# Start document dengan format RAW
job_id = win32print.StartDocPrinter(printer_handle, 1, ("Parking Ticket", None, "RAW"))
win32print.StartPagePrinter(printer_handle)

# Setelah selesai print
win32print.EndPagePrinter(printer_handle)
win32print.EndDocPrinter(printer_handle)
win32print.ClosePrinter(printer_handle)
```

## Hal-hal yang Tidak Boleh Diabaikan

1. **Format Data Barcode**
   - Harus ada asterisk (*) di awal dan akhir untuk CODE39
   - Panjang nomor tiket tidak boleh lebih dari 10 karakter
   - Gunakan encode() untuk konversi ke bytes

2. **Timing dan Urutan**
   - Initialize printer harus dilakukan di awal
   - Reset text size sebelum print barcode
   - Berikan feed lines yang cukup sebelum cut

3. **Error Handling**
   - Selalu periksa printer_available sebelum mencoba print
   - Tutup printer handle dalam blok finally atau setelah error
   - Bersihkan resources jika terjadi error

4. **Ukuran dan Format**
   - Barcode height: 80 dots (tidak lebih)
   - Barcode width: level 2 (optimal untuk scanning)
   - HRI (Human Readable Interpretation) di bawah barcode

5. **Printer Setup**
   - Mode RAW harus digunakan untuk ESC/POS commands
   - Printer harus dalam keadaan online dan siap
   - Kertas harus tersedia dan sesuai ukuran

## Troubleshooting Umum

1. Jika barcode tidak muncul:
   - Pastikan format data benar (dengan asterisk)
   - Periksa urutan perintah barcode
   - Pastikan reset text size sebelum barcode

2. Jika ukuran tidak sesuai:
   - Periksa perintah text size (\x1B\x21)
   - Sesuaikan barcode height dan width
   - Pastikan printer mendukung ukuran yang diset

3. Jika printer error:
   - Periksa status printer di Windows
   - Pastikan mode RAW digunakan
   - Reset printer fisik jika perlu
