# Sistem Parkir RSI BNA

Sistem manajemen parkir dengan fitur:
- Capture kamera otomatis
- Cetak tiket thermal
- Deteksi kendaraan dengan loop detector
- Manajemen database tiket parkir
- Laporan keuangan

## Persyaratan Sistem

- Python 3.8+
- PostgreSQL Database
- Printer Thermal EPSON TM-T82X
- Kamera IP Dahua / Kamera USB
- Arduino (untuk loop detector)

## Instalasi

1. Clone repository ini
```bash
git clone https://github.com/username/parking-system.git
cd parking-system
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Buat file konfigurasi
```bash
cp config.example.ini config.ini
```
Edit `config.ini` sesuai dengan konfigurasi sistem Anda.

4. Buat database PostgreSQL dan sesuaikan konfigurasi di `config.ini`

## Penggunaan

1. Jalankan program
```bash
python parking_camera_windows.py
```

2. Sistem akan:
   - Mendeteksi kamera
   - Mendeteksi printer
   - Terhubung ke database
   - Menunggu input dari push button/keyboard

3. Saat kendaraan masuk:
   - Tekan tombol fisik atau '1' pada keyboard
   - Sistem akan mengambil gambar
   - Menyimpan data ke database
   - Mencetak tiket

## Konfigurasi

File `config.ini` berisi pengaturan untuk:
- Kamera (IP/Local)
- Database
- Printer
- Path penyimpanan
- Dan lainnya

## Troubleshooting

1. Kamera tidak terdeteksi:
   - Periksa koneksi kamera
   - Pastikan IP dan kredensial benar
   - Coba restart kamera

2. Printer error:
   - Pastikan printer menyala dan terhubung
   - Cek ketersediaan kertas
   - Restart print spooler service

3. Database error:
   - Periksa koneksi database
   - Pastikan service PostgreSQL berjalan
   - Verifikasi kredensial database

## Lisensi

Copyright © 2024 RSI BNA. All rights reserved.

## Kontak

Untuk bantuan dan informasi lebih lanjut:
- Email: support@rsibna.com
- Telepon: (0286) 123456 

## Printer Commands (ESC/POS)

### Barcode Printing Sequence
Urutan perintah untuk mencetak barcode pada printer EPSON TM-T82X:

1. Set posisi HRI (Human Readable Interpretation) di bawah barcode:
   ```
   \x1D\x48\x02
   ```

2. Set tinggi barcode (80 dots):
   ```
   \x1D\x68\x50
   ```

3. Set lebar barcode (multiplier 2):
   ```
   \x1D\x77\x02
   ```

4. Center alignment untuk barcode:
   ```
   \x1B\x61\x01
   ```

5. Pilih tipe barcode CODE128:
   ```
   \x1D\x6B\x49
   ```

6. Kirim panjang data barcode:
   ```
   bytes([len(ticket_number)])
   ```

7. Kirim data barcode:
   ```
   ticket_number.encode()
   ```

8. Kirim terminator NUL:
   ```
   \x00
   ```

9. Tambah line feeds:
   ```
   \n\n
   ```

### Known Issues
- [ ] Barcode tidak muncul pada tiket meskipun urutan perintah sudah benar
- [x] Printer terdeteksi dan dapat mencetak teks
- [x] Format tiket sudah sesuai dengan kebutuhan

### Troubleshooting
1. Pastikan printer EPSON TM-T82X mendukung barcode CODE128
2. Cek apakah data barcode yang dikirim valid (tidak mengandung karakter khusus)
3. Verifikasi bahwa semua perintah ESC/POS diterima dengan benar oleh printer
4. Pastikan tidak ada konflik dengan pengaturan printer lainnya 