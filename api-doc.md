# API Documentation - Sistem Parkir RSI BNA

## System Requirements

### Hardware Requirements
1. **Camera (IP Camera)**
   - Type: Dahua IP Camera (recommended)
   - Resolution: Minimum 1280x720
   - Protocol: RTSP/HTTP
   - Connection: Ethernet

2. **Arduino Device**
   - Board: Arduino Uno/Nano
   - Port: COM port (usually COM3-COM9)
   - Baud Rate: 9600
   - Connection: USB

3. **Thermal Printer**
   - Type: EPSON TM-series
   - Connection: USB
   - Driver: EPSON ESC/POS compatible
   - Paper: 80mm thermal paper

4. **Server Requirements**
   - CPU: Minimum 2 cores
   - RAM: Minimum 4GB
   - Storage: Minimum 500GB
   - OS: Windows 10 or newer
   - Network: Ethernet connection

### Software Requirements
```bash
# Python Version
Python 3.8 or newer

# Python Packages
opencv-python==4.5.3.56
numpy==1.21.2
requests==2.26.0
psycopg2-binary==2.9.1
pyserial==3.5
python-escpos==2.2.0
Pillow==8.3.2
python-barcode==0.13.1

# Database
PostgreSQL 12 or newer
```

## Device Configuration

### 1. Camera Configuration
```ini
[camera]
# Camera connection settings
ip = 192.168.2.100
username = admin
password = admin123
port = 554
protocol = rtsp

# Image settings
width = 1280
height = 720
fps = 15
format = MJPG
```

### 2. Arduino Configuration
```ini
[button]
# Arduino settings
type = serial
port = COM3
baudrate = 9600
timeout = 1.0
debounce_delay = 0.5

# Pin configuration
button_pin = 2
led_pin = 13
```

### 3. Printer Configuration
```ini
[printer]
# Printer settings
model = TM-T82
vendor_id = 0x04b8
product_id = 0x0202
paper_width = 80
dpi = 180

# Print settings
font_size = 1
text_align = center
cut_type = partial
```

## Server Connection Details

### Base URL
```
http://192.168.2.6:5051/api
```

### Server Configuration
```ini
[server]
host = 192.168.2.6
port = 5051
api_base = /api
```

### Database Configuration
```ini
[database]
host = 192.168.2.6
port = 5432
name = parkir2
user = postgres
password = [secure password required]
```

## API Endpoints

### 1. Test Connection
Test server availability and get vehicle count.

**Endpoint:** `/test`  
**Method:** GET  
**Response:**
```json
{
    "success": true,
    "total_kendaraan": 150
}
```

### 2. Vehicle Entry
Register a new vehicle entering the parking lot.

**Endpoint:** `/masuk`  
**Method:** POST  
**Request Body:**
```json
{
    "plat": "B1234XY",
    "jenis": "Motor"  // Optional, defaults to "Motor"
}
```
**Response:**
```json
{
    "success": true,
    "data": {
        "tiket": "PKR202504150001",
        "plat": "B1234XY",
        "waktu": "2025-04-15 18:49:04",
        "jenis": "Motor",
        "is_parked": true,
        "is_lost": false,
        "is_paid": false,
        "is_valid": true
    }
}
```

### 3. Offline Mode
The system supports offline operation when server connection is unavailable:

- Tickets are generated with "OFF" prefix
- Data is stored locally in `offline_data.json`
- Automatic sync when connection is restored

## Important Notes

### 1. Device Setup
- Camera must be on the same network as the server
- Arduino must be connected before starting the application
- Printer must be set as default Windows printer
- All devices should be tested individually before running the system

### 2. Network Configuration
- Use static IP for all devices
- Configure firewall to allow required ports
- Ensure stable network connection
- Recommended to use dedicated network switch

### 3. Maintenance
- Regular backup of database (daily)
- Clean camera lens weekly
- Check printer head monthly
- Test Arduino buttons daily
- Monitor disk space for images

### 4. Troubleshooting Common Issues

#### Camera Issues
- Check network connection
- Verify IP address and credentials
- Ensure proper lighting conditions
- Clean lens if image is blurry

#### Arduino Issues
- Check USB connection
- Verify COM port in Device Manager
- Reset Arduino if unresponsive
- Check button physical connection

#### Printer Issues
- Check paper supply
- Clear paper jams
- Clean printer head
- Verify printer is online and ready

### 5. Backup Procedures
1. Database Backup
   ```bash
   pg_dump -U postgres parkir2 > backup_$(date +%Y%m%d).sql
   ```

2. Image Backup
   ```bash
   # Backup capture directory
   xcopy /E /I /Y capture backup\capture_%date:~-4,4%%date:~-7,2%%date:~-10,2%
   ```

### 6. Emergency Procedures
1. If server is down:
   - System will operate in offline mode
   - Tickets will be generated with "OFF" prefix
   - Data will be synced when server is back online

2. If printer fails:
   - System will continue capturing
   - Save ticket numbers manually
   - Contact technical support for printer service

3. If camera fails:
   - System will use dummy image mode
   - Log the issue
   - Contact technical support

### 7. Security Considerations
1. Change default passwords
2. Use HTTPS in production
3. Implement API authentication
4. Regular security updates
5. Monitor access logs
6. Restrict physical access to devices

## Support Contact

For technical support:
- Email: support@rsi-bna.com
- Phone: [Contact Number]
- Hours: 24/7 