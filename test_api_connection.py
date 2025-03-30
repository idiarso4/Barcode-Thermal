from parking_api import ParkingAPI
import json
from datetime import datetime

def test_api():
    api = ParkingAPI()
    
    print("=== Test Koneksi API ===")
    success, result = api.test_connection()
    print(f"Status: {'✅ Berhasil' if success else '❌ Gagal'}")
    print("Response:", json.dumps(result, indent=2))
    
    if success:
        print("\n=== Test Input Kendaraan ===")
        # Generate plate number with timestamp to ensure uniqueness
        plate = f"RSI{datetime.now().strftime('%H%M%S')}"
        success, result = api.add_vehicle(plate, "Motor")
        print(f"Status: {'✅ Berhasil' if success else '❌ Gagal'}")
        print("Response:", json.dumps(result, indent=2))
        
        if success:
            print("\n=== Test Daftar Kendaraan ===")
            success, result = api.get_vehicles()
            print(f"Status: {'✅ Berhasil' if success else '❌ Gagal'}")
            print("Response:", json.dumps(result, indent=2))
            
            # If we got a ticket number from vehicle entry, test exit
            if 'tiket' in result.get('data', [{}])[0]:
                print("\n=== Test Kendaraan Keluar ===")
                ticket = result['data'][0]['tiket']
                success, result = api.vehicle_exit(ticket)
                print(f"Status: {'✅ Berhasil' if success else '❌ Gagal'}")
                print("Response:", json.dumps(result, indent=2))

if __name__ == "__main__":
    test_api() 