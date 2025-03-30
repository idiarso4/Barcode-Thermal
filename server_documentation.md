# RSI BNA Client - Server Documentation

## System Updates

### Database Updates
- All status columns are now available:
  * `is_parked` (default: true)
  * `is_lost` (default: false)
  * `is_paid` (default: false)
  * `is_valid` (default: true)
- All constraint errors have been resolved

### API Format

#### Request Format
```json
{
    "plat": "B1234XY",    // Required
    "jenis": "Motor"      // Optional (Motor/Mobil)
}
```

#### Response Format
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

## Testing Instructions

### Connection Test
```bash
curl http://192.168.2.6:5051/api/test
```

### Vehicle Entry Test
```bash
curl -X POST http://192.168.2.6:5051/api/masuk \
  -H "Content-Type: application/json" \
  -d '{"plat":"B1234XY","jenis":"Motor"}'
```

## Important Client Notes

### Ticket Format
- Format: `OFF` + 4 digits (example: OFF0001)
- Automatic increment for sequence numbers
- Ticket must be stored for exit gate processing

### Vehicle Status
All entering vehicles automatically set to:
- `is_parked` = true
- `is_lost` = false
- `is_paid` = false
- `is_valid` = true

### Error Handling
- Clear error messages will be provided
- Implement offline data storage for server unavailability

## Next Steps

### Client Tasks
1. Update program with new format
2. Test multiple vehicle entries
3. Verify database data

### Monitoring Requirements
- Monitor response time
- Log any errors
- Perform regular data backups

## Support Information
- Technical Support available 24/7
- Contact for:
  1. New error discoveries
  2. Additional clarification needed
  3. Feature enhancement requests

Support team is available for assistance at any time. 