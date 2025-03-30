# Sistem Parkir Lokal RSI BNA

Sistem parkir lokal dengan kamera dan push button untuk RSI Banjarnegara.

## Fitur

1. **Capture Otomatis**
   - Mengambil gambar saat tombol ditekan
   - Format nama file: TKT[tanggal][jam]_[nomor].jpg
   - Resolusi gambar: 1920x1080

2. **Manajemen File**
   - Penyimpanan otomatis di folder capture_images
   - Penomoran file berurutan
   - Peringatan jika storage hampir penuh

3. **Logging**
   - Log aktivitas sistem
   - Log error untuk troubleshooting
   - Timestamp untuk setiap event

## Persyaratan Sistem

### Hardware
- Raspberry Pi/Komputer Linux
- Webcam/Kamera USB (mendukung 1080p)
- Push Button
- Kabel jumper

### Software
- Python 3.7+
- OpenCV
- RPi.GPIO

## Instalasi

1. **Update sistem**:
```bash
sudo apt-get update
sudo apt-get upgrade
```

2. **Install dependencies sistem**:
```bash
sudo apt-get install -y python3-opencv
sudo apt-get install -y python3-rpi.gpio
```

3. **Clone repository**:
```bash
git clone [URL_REPO]
cd parking_system
```

4. **Install Python dependencies**:
```bash
pip3 install -r requirements.txt
```

5. **Buat folder untuk gambar**:
```bash
mkdir capture_images
```

6. **Set permission**:
```bash
sudo chmod -R 777 capture_images
sudo chmod +x parking_camera.py
```

## Koneksi Hardware

### Push Button
```
Push Button -> Raspberry Pi
GND        -> Pin GND
Signal     -> GPIO 18 (Pin 12)
VCC        -> 3.3V (Pin 1)
```

### Kamera
- Hubungkan kamera ke port USB
- Pastikan kamera terdeteksi:
```bash
ls /dev/video*
```

## Menjalankan Program

1. **Mode normal**:
```bash
python3 parking_camera.py
```

2. **Mode debug** (dengan output lengkap):
```bash
python3 parking_camera.py 2> debug.log
```

## Troubleshooting

### 1. Kamera Tidak Terdeteksi
```bash
# Cek device kamera
ls /dev/video*

# Cek permission
sudo usermod -a -G video $USER
```

### 2. Push Button Tidak Berespons
```bash
# Cek GPIO
gpio readall

# Test GPIO manual
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP); print(GPIO.input(18))"
```

### 3. Error Permission
```bash
# Set permission folder
sudo chmod -R 777 capture_images

# Set permission program
sudo chmod +x parking_camera.py
```

## Maintenance

### Backup Data
```bash
# Backup manual
cp -r capture_images /path/to/backup

# Backup otomatis (tambahkan ke crontab)
0 1 * * * rsync -av /path/to/capture_images /path/to/backup
```

### Pembersihan Storage
```bash
# Cek storage
df -h .

# Hapus file lama (lebih dari 30 hari)
find capture_images -type f -mtime +30 -delete
```

## Support

Jika mengalami masalah:
- Log file: `parking.log`
- Debug mode: Jalankan dengan `2> debug.log`
- Kontak support: [NOMOR_SUPPORT]

## Lisensi

Copyright © 2024 RSI Banjarnegara 