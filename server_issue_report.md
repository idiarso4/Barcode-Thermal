# Laporan Masalah Server Parkir RSI BNA
Tanggal: 30 Maret 2025
Waktu: 16:55 WIB
Pelapor: Tim Client Parkir

## Status Sistem
- Aplikasi client berjalan di mode offline
- Arduino tidak terdeteksi
- Printer thermal berfungsi normal
- Koneksi API berhasil, tapi endpoint /masuk error

## Detail Masalah

### 1. Koneksi API
✅ **Endpoint yang Berhasil**
- GET /api/test
  ```json
  {
    "message": "Koneksi berhasil",
    "success": true,
    "total_kendaraan": 11
  }
  ```

❌ **Endpoint yang Error**
- POST /api/masuk
  - Status: 500 Internal Server Error
  - Error Message:
    ```
    Error: null value in column "IsParked" of relation "Vehicles" violates not-null constraint
    DETAIL: Failing row contains (81, B1234XY, Motor, OFF0001, 2, null, null, null, 2025-03-30 16:45:30.38089, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, f, f, t, t).
    ```

### 2. Database PostgreSQL
**Konfigurasi**
- Host: 192.168.2.6
- Port: 5432
- Database: parkir2
- Table: Vehicles

**Masalah**
1. Koneksi sering terputus dengan error:
   ```
   connection to server at "192.168.2.6", port 5432 failed: Connection refused (0x0000274D/10061)
   Is the server running on that host and accepting TCP/IP connections?
   ```
2. Struktur tabel tidak sesuai dengan API request:
   - Kolom `IsParked` tidak boleh null
   - Format data boolean tidak jelas (true/false vs 1/0 vs t/f)

### 3. Timeline Kejadian
```
02:59:37 - API connection test failed (404)
02:59:39 - Database connection refused
04:01:47 - Printer initialized successfully
13:22:01 - API connection successful
13:22:01 - Printer EPSON TM-T82X detected
13:23:18 - Vehicle processing attempted
```

## Dampak
1. Sistem terpaksa beroperasi dalam mode offline
2. Tiket menggunakan format offline (OFF0001, OFF0002, dst)
3. Data kendaraan tidak tersimpan di database pusat
4. Sinkronisasi data tertunda

## Request untuk Tim Backend

### 1. Database
- [ ] Periksa service PostgreSQL di 192.168.2.6
- [ ] Verifikasi firewall untuk port 5432
- [ ] Kirim struktur tabel Vehicles yang lengkap
- [ ] Konfirmasi format data untuk field boolean

### 2. API
- [ ] Update dokumentasi API dengan field wajib
- [ ] Konfirmasi format request yang benar:
  ```json
  {
    "plat": "B1234XY",
    "jenis": "Motor",
    "IsParked": true  // Format?
  }
  ```
- [ ] Tambahkan validasi request di API
- [ ] Sediakan endpoint untuk sinkronisasi data offline

### 3. Monitoring
- [ ] Aktifkan monitoring untuk:
  - Koneksi database
  - Response time API
  - Error rate
  - Server resources

## Solusi Sementara
1. Sistem menggunakan mode offline
2. Data disimpan di file lokal (counter.txt)
3. Tiket dicetak dengan format offline
4. Log error disimpan di parking_client.log

## Solusi yang Diusulkan

### 1. Perbaikan Database
```sql
-- Update struktur tabel untuk menangani null values
INSERT INTO public."Vehicles" 
("VehicleNumber", "VehicleType", "TicketNumber", "VehicleTypeId", 
 "EntryTime", "is_parked", "is_lost", "is_paid", "is_valid")
VALUES 
(%s, %s, %s, %s, %s, true, false, false, true)
```

### 2. Implementasi Fault Tolerance
```python
def process_vehicle_entry(plat, jenis):
    try:
        # Coba online mode
        response = send_to_server(plat, jenis)
        if response and response.get('success'):
            return response['data']
            
    except Exception as e:
        logger.warning(f"Server error, switching to offline mode: {str(e)}")
        
    # Fallback ke offline mode
    return process_offline_entry(plat, jenis)
```

### 3. Sistem Backup & Recovery
- File JSON untuk data offline: `offline_data.json`
- Counter untuk nomor tiket: `counter.txt`
- Auto-sync saat koneksi kembali

### 4. Logging & Monitoring
```python
logging.basicConfig(
    filename='parking_client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## Langkah Implementasi

### 1. Update Dependencies
```bash
pip install requests python-escpos
```

### 2. Konfigurasi Server
- Update query database untuk handle null values
- Aktifkan validasi request di API
- Setup monitoring koneksi

### 3. Konfigurasi Client
- Install printer driver EPSON TM-T82X
- Setup file permissions untuk logging
- Konfigurasi backup path

### 4. Testing
- [ ] Test koneksi database
- [ ] Test printer
- [ ] Test mode offline
- [ ] Test sinkronisasi
- [ ] Validasi format tiket

## Estimasi Waktu
- Setup Server: 2 jam
- Konfigurasi Client: 1 jam
- Testing: 2 jam
- Monitoring: 1 jam

## Backup Plan
1. Sistem tetap beroperasi offline
2. Data disimpan lokal dan dibackup
3. Sinkronisasi manual jika diperlukan

## Kontak
- Tim Client: [Nomor kontak]
- Lokasi: RSI Banjarnegara
- Prioritas: TINGGI (Sistem Parkir Utama)

## Attachment
- [x] parking_client.log
- [x] counter.txt
- [x] Database error screenshots
- [x] API response logs

## Screenshot Program
```
==================================================
     TERMINAL MASUK PARKIR RSI BANJARNEGARA       
==================================================
Mode: Otomatis (Push Button)
Status: Menunggu kendaraan...
Tekan Ctrl+C untuk menghentikan program
✅ Koneksi ke API berhasil
📊 Total kendaraan: 11
Sistem Parkir RSI BNA
======================
Mode: Keyboard Input (Arduino tidak terdeteksi)
Tekan 'p' untuk simulasi kendaraan masuk       
Tekan Ctrl+C untuk keluar
``` 