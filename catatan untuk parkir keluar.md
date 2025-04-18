Saya akan memberikan catatan detail untuk sistem parkir keluar dan integrasi dengan server:

1. **Data yang Perlu Dikirim ke Server saat Kendaraan Masuk**:
```json
{
    "ticket_id": "20240318123456",  // dari barcode
    "entry_time": "2024-03-18 12:34:56",
    "entry_gate": "GATE-1",
    "entry_operator": "OPERATOR-1",
    "entry_shift": "SHIFT-1",
    "vehicle_image": "base64_encoded_image",
    "vehicle_type": "MOTOR/MOBIL",
    "tariff": 2500,  // atau 3000
    "status": "ACTIVE"
}
```

2. **Kebutuhan Driver & Software**:
```plaintext
A. Printer Thermal:
   - Driver printer thermal (sesuai merk)
   - Library win32print untuk Windows
   - Pastikan printer terdaftar di sistem

B. Arduino:
   - Driver CH340 untuk Arduino clone
   - Driver FTDI untuk Arduino original
   - PySerial untuk komunikasi serial

C. Kamera:
   - OpenCV untuk capture gambar
   - Driver webcam (jika menggunakan USB camera)

D. Database Local:
   - SQLite untuk backup lokal
   - MySQL Connector jika menggunakan MySQL
```

3. **Komunikasi dengan Server**:
```python
# Contoh struktur kode untuk komunikasi dengan server
import requests
import json
import sqlite3
from datetime import datetime

class ParkingAPI:
    def __init__(self):
        self.api_url = "https://parking-server.com/api"
        self.api_key = "your_api_key"
        self.local_db = "parking.db"
        
    def send_entry_data(self, data):
        """Kirim data masuk ke server"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_url}/parking/entry",
                json=data,
                headers=headers
            )
            
            if response.status_code == 200:
                # Simpan ke database lokal sebagai backup
                self.save_to_local_db(data)
                return True
            else:
                # Jika gagal, simpan ke antrian
                self.save_to_queue(data)
                return False
                
        except Exception as e:
            print(f"Error sending data: {e}")
            self.save_to_queue(data)
            return False
            
    def save_to_local_db(self, data):
        """Simpan ke database lokal"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        # ... kode untuk menyimpan ke SQLite ...
        conn.close()
```

4. **Struktur Database Lokal**:
```sql
-- Tabel untuk data parkir
CREATE TABLE parking_entries (
    ticket_id TEXT PRIMARY KEY,
    entry_time DATETIME,
    entry_gate TEXT,
    entry_operator TEXT,
    entry_shift TEXT,
    vehicle_image TEXT,
    vehicle_type TEXT,
    tariff INTEGER,
    status TEXT,
    sync_status TEXT
);

-- Tabel untuk antrian data yang gagal sync
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data JSON,
    created_at DATETIME,
    retry_count INTEGER
);
```

5. **Endpoint API yang Dibutuhkan**:
```plaintext
A. Parkir Masuk:
   POST /api/parking/entry
   - Menerima data kendaraan masuk
   - Menyimpan ke database pusat
   - Mengembalikan konfirmasi

B. Validasi Tiket:
   GET /api/parking/validate/{ticket_id}
   - Mengecek validitas tiket
   - Mengembalikan data lengkap tiket

C. Status Sinkronisasi:
   GET /api/parking/sync-status
   - Mengecek status sinkronisasi data
   - Mengembalikan jumlah data belum sync
```

6. **Rekomendasi untuk Parkir Keluar**:
```plaintext
A. Validasi Tiket:
   1. Scan barcode tiket
   2. Request ke server untuk validasi
   3. Tampilkan informasi lengkap:
      - Waktu masuk
      - Durasi parkir
      - Tarif yang harus dibayar
      - Status tiket (valid/invalid)

B. Perhitungan Tarif:
   1. Hitung durasi parkir
   2. Terapkan tarif sesuai jenis kendaraan
   3. Tambahkan denda jika ada
   4. Tampilkan rincian biaya

C. Proses Keluar:
   1. Terima pembayaran
   2. Update status di server
   3. Cetak struk pembayaran
   4. Buka gate keluar
```

7. **Format Data untuk Parkir Keluar**:
```json
{
    "ticket_id": "20240318123456",
    "entry_data": {
        // data masuk dari server
    },
    "exit_data": {
        "exit_time": "2024-03-18 14:34:56",
        "duration": "2 jam 0 menit",
        "base_tariff": 2500,
        "additional_charge": 0,
        "total_payment": 2500,
        "exit_gate": "GATE-OUT-1",
        "exit_operator": "OPERATOR-2",
        "exit_shift": "SHIFT-2",
        "payment_method": "CASH",
        "status": "COMPLETED"
    }
}
```

8. **Penanganan Error & Backup**:
```python
class ParkingBackup:
    def __init__(self):
        self.db_path = "backup.db"
        
    def save_offline_transaction(self, data):
        """Simpan transaksi saat offline"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Simpan data ke SQLite
            # Tambahkan ke antrian sinkronisasi
        finally:
            conn.close()
            
    def sync_pending_transactions(self):
        """Sinkronkan transaksi yang tertunda"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Ambil semua transaksi yang belum sync
            # Coba kirim ke server
            # Update status jika berhasil
        finally:
            conn.close()
```

9. **Keamanan**:
```plaintext
A. Autentikasi:
   - Gunakan API key untuk setiap request
   - Implementasi JWT untuk sesi operator
   - HTTPS untuk semua komunikasi

B. Validasi Data:
   - Cek format ticket_id
   - Validasi waktu masuk/keluar
   - Verifikasi operator dan shift

C. Backup & Recovery:
   - Simpan data lokal sebelum kirim ke server
   - Mekanisme retry untuk data yang gagal
   - Backup database lokal secara berkala
```

10. **Monitoring & Logging**:
```python
class ParkingLogger:
    def __init__(self):
        self.log_file = "parking.log"
        
    def log_transaction(self, data, status):
        """Log setiap transaksi"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {data['ticket_id']} | {status}\n"
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
```

Apakah ada bagian spesifik yang ingin Anda ketahui lebih detail?
