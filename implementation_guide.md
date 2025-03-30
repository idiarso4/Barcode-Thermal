# Panduan Implementasi Solusi Parkir RSI BNA

## A. Persiapan Server

### 1. Update Database
```sql
-- Pastikan semua kolom boolean memiliki default value
ALTER TABLE public."Vehicles"
ALTER COLUMN "is_parked" SET DEFAULT true,
ALTER COLUMN "is_lost" SET DEFAULT false,
ALTER COLUMN "is_paid" SET DEFAULT false,
ALTER COLUMN "is_valid" SET DEFAULT true;

-- Tambah kolom untuk tracking mode offline
ALTER TABLE public."Vehicles"
ADD COLUMN "is_offline" boolean DEFAULT false,
ADD COLUMN "sync_status" varchar(50) DEFAULT 'synced';
```

### 2. Update API Endpoint
```python
@app.route('/api/masuk', methods=['POST'])
def vehicle_entry():
    try:
        data = request.get_json()
        
        # Validasi input
        if not data.get('plat'):
            return jsonify({
                'success': False,
                'message': 'Nomor plat wajib diisi'
            }), 400
            
        # Set default values
        data.setdefault('jenis', 'Motor')
        data.setdefault('is_parked', True)
        data.setdefault('is_lost', False)
        data.setdefault('is_paid', False)
        data.setdefault('is_valid', True)
        
        # Proses entry
        result = db.add_vehicle(data)
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error processing entry: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

## B. Setup Client

### 1. Install Dependencies
```bash
# Install required packages
pip install requests python-escpos psycopg2-binary

# Install printer driver
# Windows: Download from Epson website
# Linux: apt-get install printer-driver-escpos
```

### 2. File Structure
```
parking_system/
├── config/
│   ├── config.ini
│   └── logging.ini
├── data/
│   ├── counter.txt
│   └── offline_data.json
├── logs/
│   └── parking_client.log
├── src/
│   ├── __init__.py
│   ├── parking_client.py
│   ├── printer_handler.py
│   └── db_handler.py
└── tests/
    └── test_parking.py
```

### 3. Konfigurasi
```ini
# config.ini
[server]
host = 192.168.2.6
port = 5051
api_base = /api

[database]
host = 192.168.2.6
port = 5432
name = parkir2
user = postgres
password = ****

[printer]
vendor_id = 0x04b8
product_id = 0x0202
```

## C. Monitoring

### 1. Setup Logging
```python
# logging.ini
[loggers]
keys=root,parkingClient

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_parkingClient]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=parkingClient
propagate=0
```

### 2. Health Check
```python
def check_system_health():
    status = {
        'server': test_server_connection(),
        'database': test_db_connection(),
        'printer': test_printer_connection(),
        'offline_mode': check_offline_data()
    }
    return status
```

## D. Testing

### 1. Unit Tests
```python
def test_offline_mode():
    client = ParkingClient()
    result = client.process_vehicle('B1234XY', 'Motor')
    assert result['ticket'].startswith('OFF')
    assert os.path.exists('data/offline_data.json')
```

### 2. Integration Tests
```python
def test_sync_process():
    client = ParkingClient()
    # Add offline data
    client.process_vehicle('B1234XY', 'Motor')
    # Try sync
    assert client.sync_offline_data()
    # Verify data in database
    assert db.get_vehicle('B1234XY') is not None
```

## E. Maintenance

### 1. Backup Script
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
tar -czf backup_$DATE.tar.gz data/
```

### 2. Monitoring Script
```python
def monitor_system():
    while True:
        status = check_system_health()
        if not all(status.values()):
            send_alert()
        time.sleep(300)  # Check every 5 minutes
```

## F. Troubleshooting

### 1. Database Issues
```sql
-- Check connection count
SELECT count(*) FROM pg_stat_activity;

-- Kill hanging connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'parkir2' AND state = 'idle';
```

### 2. Printer Issues
```python
def reset_printer():
    printer.close()
    time.sleep(1)
    printer.open()
    printer.init()
```

## G. Recovery Plan

1. Backup data offline setiap jam
2. Simpan log minimal 7 hari
3. Test restore data mingguan
4. Dokumentasi proses recovery 