# Catatan Pengembangan Sistem Parkir RSI BNA

## Permasalahan Awal
1. Sistem memerlukan input manual untuk kendaraan masuk
2. Tidak ada integrasi dengan push button
3. Masalah koneksi database PostgreSQL
4. Barcode tidak muncul pada tiket
5. Format tiket tidak sesuai dengan kebutuhan printer thermal

## Solusi yang Diterapkan

### 1. Integrasi Arduino
- Menambahkan koneksi ke Arduino di port COM7
- Mengimplementasikan pembacaan sinyal dari push button
- Menambahkan pengecekan status "READY" dari Arduino
- Handling error jika Arduino tidak terdeteksi

### 2. Sistem Pencetakan Tiket
- Implementasi format ESC/POS untuk printer thermal
- Perbaikan format barcode menggunakan CODE39
- Parameter barcode yang dioptimalkan:
  - Tinggi: 100 dots
  - Lebar: Level 2
  - HRI (Human Readable Interpretation) di bawah barcode
- Penanganan bytes dan string literals yang benar

### 3. Mode Online-Offline
- Implementasi sistem fallback ke mode offline jika API tidak tersedia
- Format tiket offline: OFF0001, OFF0002, dst
- Penyimpanan counter di file counter.txt
- Auto-increment counter dengan reset di 9999

### 4. Format Tiket
```
=== PARKIR RSI BNA ===

[Mode Online]
Tiket: PK20240318123456
Masuk: 2024-03-18 12:34:56

[Mode Offline]
TIKET PARKIR
Nomor: OFF0001
Waktu: 2024-03-18 12:34:56

[BARCODE]

Terima kasih
Jangan hilangkan tiket ini
```

### 5. Penanganan Error
- Validasi printer tersedia
- Handling error koneksi Arduino
- Fallback ke mode offline jika API gagal
- Logging untuk troubleshooting

## Penggunaan Sistem

### Persyaratan Sistem
1. Arduino terhubung ke COM7
2. Printer thermal terdeteksi sebagai printer default
3. Push button terpasang dengan benar
4. Koneksi ke server API (opsional, ada mode offline)

### Cara Penggunaan
1. Jalankan aplikasi melalui file .bat
2. Sistem akan melakukan inisialisasi:
   - Deteksi printer
   - Koneksi Arduino
   - Cek status "READY"
3. Tekan push button untuk memproses kendaraan masuk
4. Tiket akan tercetak otomatis

### Troubleshooting
1. Jika barcode tidak muncul:
   - Pastikan printer mendukung CODE39
   - Cek format data barcode valid
2. Jika Arduino tidak terdeteksi:
   - Verifikasi koneksi di COM7
   - Pastikan tidak ada program lain yang menggunakan port
3. Jika API tidak tersedia:
   - Sistem akan otomatis beralih ke mode offline
   - Tiket tetap bisa dicetak dengan nomor offline

## Pemeliharaan
1. File counter.txt menyimpan nomor tiket terakhir untuk mode offline
2. Log error tersimpan untuk analisis masalah
3. Backup counter.txt secara berkala disarankan

# Catatan Integrasi API Sistem Parkir RSI BNA

## Endpoint API
- Base URL: http://192.168.2.6:5051/api
- Test Connection: GET /test
- Input Kendaraan: POST /masuk

## Format Request
```json
{
    "plat": "B1234XY",    // Wajib
    "jenis": "Motor"      // Opsional (Motor/Mobil)
}
```

## Format Response
```json
{
    "success": true,
    "message": "Kendaraan berhasil masuk",
    "data": {
        "id": 123,
        "plat": "B1234XY",
        "jenis": "Motor",
        "ticket": "OFF0001",
        "waktu": "2024-03-30 05:40:09",
        "status": {
            "is_parked": true,
            "is_lost": false,
            "is_paid": false,
            "is_valid": true
        }
    }
}
```

## Langkah Integrasi
1. Tetap gunakan sistem barcode yang sudah ada
2. Setelah baca input dari Arduino:
   - Kirim data ke API server
   - Jika server DOWN, gunakan sistem offline seperti biasa
   - Jika server UP, gunakan ticket number dari server

## Cara Penggunaan
1. Program tetap berjalan seperti biasa
2. Secara otomatis akan mencoba koneksi ke server
3. Jika server tidak tersedia, gunakan mode offline

# Pengaturan Barcode Printer EPSON TM-T82X

## Command Barcode yang Bekerja
Berikut adalah command ESC/POS untuk mencetak barcode yang bekerja dengan baik:

```python
commands.extend([
    b"\x1D\x48\x02",      # HRI position - below barcode
    b"\x1D\x68\x50",      # Barcode height = 80 dots
    b"\x1D\x77\x02",      # Barcode width multiplier (2)
    b"\x1D\x6B\x04",      # Select CODE39
    bytes([len(ticket_number)]) + ticket_number.encode(),  # Length + data
    b"\n\n"
])
```

## Penjelasan Command
1. `\x1D\x48\x02` - Mengatur posisi HRI (Human Readable Interpretation) di bawah barcode
2. `\x1D\x68\x50` - Mengatur tinggi barcode (80 dots)
3. `\x1D\x77\x02` - Mengatur lebar barcode (multiplier 2)
4. `\x1D\x6B\x04` - Memilih format CODE39
5. Data format: panjang data + data barcode

## Catatan Penting
- Gunakan CODE39 (format 04) karena mendukung angka dan huruf
- Jangan gunakan format UPC-A atau EAN13 karena terbatas hanya untuk angka
- Tidak perlu NUL terminator untuk CODE39
- Pastikan ada line feed (`\n\n`) setelah barcode



## Troubleshooting
Jika barcode tidak muncul:
1. Pastikan command sequence benar
2. Jangan ubah format CODE39 ke format lain
3. Pastikan data tidak melebihi batas panjang
4. Cek apakah printer mendukung command yang dikirim

# Ticket Format Support

Sistem parkir saat ini mendukung format tiket server (TKT* format) dengan baik. Beberapa fitur:

1. **Tiket Format Server**: Sistem mendukung format tiket panjang dengan prefiks TKT, misalnya: `TKT202503290219527426`
   - Untuk barcode, sistem menggunakan 10 digit terakhir untuk menyederhanakan pembacaan barcode
   - Tiket yang dicetak menampilkan nomor tiket lengkap di bagian atas

2. **Cara Testing**:
   - Menggunakan `python parking_direct_print.py` - Pilih opsi 2 untuk test format TKT
   - Menggunakan `python parking_client_simple.py --test-server-ticket` untuk test langsung

3. **Implementasi ESC/POS**:
   - Menggunakan win32print untuk akses printer secara langsung
   - Kompatibel dengan printer EPSON TM-T82X Receipt
   - Implementasi barcode menggunakan CODE39

4. **Mode Operasi**:
   - Koneksi ke server API untuk mengambil data tiket aktual
   - Mendukung mode Arduino (produksi) atau mode simulasi (testing)

## Contoh Format

Server memberikan format tiket: `TKT202503290219527426`

## Troubleshooting

Jika ada masalah cetak:
1. Pastikan printer dalam keadaan online dan kertas tersedia
2. Cek koneksi port serial Arduino pada COM7
3. Coba reset printer atau restart aplikasi
4. Gunakan mode test untuk memverifikasi fungsi printer

## Pemeliharaan

Program telah diupdate untuk mendukung format tiket server, dan akan terus bekerja dengan baik dalam production environment.