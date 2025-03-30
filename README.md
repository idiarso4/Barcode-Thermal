# Sistem Parkir RSI BNA

Sistem parkir otomatis dengan kamera CCTV dan printer thermal untuk RSI Banjarnegara.

## Fitur

- Capture gambar kendaraan otomatis menggunakan kamera CCTV Dahua
- Cetak tiket parkir menggunakan printer thermal
- Input menggunakan pushbutton
- Penyimpanan data di database PostgreSQL
- Antarmuka yang mudah digunakan
- Logging sistem untuk monitoring dan troubleshooting

## Persyaratan Sistem

- Windows 10/11
- Python 3.8+
- PostgreSQL Database Server
- Kamera CCTV Dahua (RTSP support)
- Printer Thermal (EPSON TM-T82X atau kompatibel)
- Arduino dengan pushbutton

## Persyaratan Python

```
opencv-python
numpy
pyserial
psycopg2
requests
pywin32
```

## Konfigurasi

1. Salin `config.ini.example` ke `config.ini`
2. Sesuaikan konfigurasi berikut:

```ini
[camera]
rtsp_url = rtsp://admin:password@ip_address:554/cam/realmonitor?channel=1&subtype=0

[database]
host = localhost
port = 5432
dbname = parkir2
user = postgres
password = your_password

[serial]
port = COM7
baudrate = 9600
```

## Instalasi

1. Clone repository:
```bash
git clone https://github.com/idiarso4/Barcode-Thermal.git
cd Barcode-Thermal
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup database:
```bash
python db_test.py
```

4. Jalankan aplikasi:
```bash
python parking_camera_windows.py
```

## Penggunaan

1. Pastikan semua perangkat terhubung:
   - Kamera CCTV dapat diakses melalui RTSP
   - Printer thermal terpasang dan diset sebagai default printer
   - Arduino dengan pushbutton terhubung ke port serial yang benar

2. Jalankan aplikasi:
   - Program akan mendeteksi kamera, printer, dan pushbutton secara otomatis
   - Status koneksi akan ditampilkan di console
   - Sistem siap menerima input dari pushbutton

3. Proses parkir:
   - Tekan pushbutton untuk memulai proses
   - Sistem akan mengambil gambar dari kamera
   - Tiket parkir akan dicetak otomatis
   - Data disimpan ke database

## Troubleshooting

### Kamera tidak terdeteksi
- Periksa koneksi jaringan ke kamera
- Pastikan URL RTSP benar
- Periksa username dan password kamera

### Printer tidak berfungsi
- Pastikan printer terhubung dan menyala
- Set printer sebagai default printer Windows
- Periksa ketersediaan kertas
- Restart aplikasi jika diperlukan

### Pushbutton tidak merespon
- Periksa koneksi kabel Arduino
- Pastikan port COM yang benar di config.ini
- Periksa baudrate (default: 9600)

## Struktur Direktori

```
├── parking_camera_windows.py    # Program utama
├── config.ini                   # File konfigurasi
├── requirements.txt             # Dependency Python
├── db_test.py                  # Setup database
├── capture_images/             # Folder penyimpanan gambar
└── logs/                       # File log sistem
```

## Lisensi

Copyright © 2024 RSI Banjarnegara. All rights reserved.

## Kontak

Untuk bantuan dan informasi lebih lanjut:
- Email: support@rsibna.com
- Telepon: (0286) 123456 