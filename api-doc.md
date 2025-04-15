# API Documentation - Sistem Parkir RSI BNA

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

### Error Handling

#### Common Error Responses
```json
{
    "success": false,
    "message": "Error description"
}
```

#### HTTP Status Codes
- 200: Success
- 400: Bad Request (invalid input)
- 500: Server Error

## Client Implementation

### Required Dependencies
```bash
pip install requests python-escpos psycopg2-binary
```

### Example Code
```python
import requests

class ParkingClient:
    def __init__(self):
        self.base_url = "http://192.168.2.6:5051/api"
        
    def test_connection(self):
        try:
            response = requests.get(f"{self.base_url}/test")
            return response.ok, response.json()
        except Exception as e:
            return False, None
            
    def process_vehicle(self, plat):
        try:
            response = requests.post(
                f"{self.base_url}/masuk",
                json={"plat": plat},
                timeout=5
            )
            return response.ok, response.json()
        except Exception:
            # Switch to offline mode
            return self.process_offline(plat)
```

## Health Monitoring

### System Health Check
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

### Monitoring Intervals
- Connection test: Every 5 minutes
- Database backup: Daily
- Log retention: 7 days

## Security Considerations

1. Use HTTPS for production environments
2. Implement API authentication
3. Regular security updates
4. Secure database credentials
5. Monitor for unusual activity

## Troubleshooting

### Common Issues

1. Connection Refused
   - Check if server is running
   - Verify IP address and port
   - Check firewall settings

2. Database Connection Failed
   - Verify PostgreSQL service is running
   - Check connection limits
   - Verify credentials

3. Sync Failures
   - Check network connectivity
   - Verify data integrity
   - Check disk space for logs

### Support Contact

For technical support:
- Email: support@rsi-bna.com
- Phone: [Contact Number]
- Hours: 24/7 