import requests
import json
from datetime import datetime

def test_server():
    base_url = "http://192.168.2.6:5051/api"
    
    print("\n=== Test Koneksi Server ===")
    
    # 1. Test koneksi dasar
    try:
        response = requests.get(f"{base_url}/test")
        if response.ok:
            data = response.json()
            print("✅ Koneksi ke server berhasil")
            print(f"📊 Total kendaraan: {data.get('total_kendaraan', 'tidak tersedia')}")
        else:
            print(f"❌ Gagal: Server merespon dengan kode {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Gagal terhubung ke server: {str(e)}")
        return

    # 2. Test input kendaraan
    print("\n=== Test Input Kendaraan ===")
    
    # Format data sesuai dokumentasi
    test_data = {
        "plat": "B1234TEST"
    }
    
    print("\nMengirim data:", json.dumps(test_data, indent=2))
    
    try:
        response = requests.post(
            f"{base_url}/masuk",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print("\nResponse Status:", response.status_code)
        print("Response Headers:", dict(response.headers))
        
        try:
            result = response.json()
            print("\nResponse Body:", json.dumps(result, indent=2))
            
            if response.ok and result.get('success'):
                print("\n✅ Test input kendaraan berhasil")
                print("\nDetail Tiket:")
                print(f"Nomor Tiket : {result['data']['tiket']}")
                print(f"Nomor Plat  : {result['data']['plat']}")
                print(f"Waktu Masuk : {result['data']['waktu']}")
            else:
                print(f"\n❌ Gagal: {result.get('message', 'Tidak ada pesan error')}")
        except json.JSONDecodeError:
            print("\nResponse Body (raw):", response.text)
            print("❌ Gagal: Response bukan format JSON valid")
            
    except Exception as e:
        print(f"❌ Gagal melakukan test input: {str(e)}")

if __name__ == "__main__":
    print("""
==================================================
     TEST KONEKSI SERVER PARKIR RSI BNA
==================================================
    """)
    test_server() 