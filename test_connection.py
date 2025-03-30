from db_connector import ParkingClient
import time

def test_connections():
    print("Testing API Connection...")
    api_client = ParkingClient(use_api=True)
    api_result = api_client.test_connection()
    print(f"API Connection: {'✅ Success' if api_result else '❌ Failed'}")
    api_client.close()

    print("\nTesting Direct Database Connection...")
    db_client = ParkingClient(use_api=False)
    db_result = db_client.test_connection()
    print(f"Database Connection: {'✅ Success' if db_result else '❌ Failed'}")
    db_client.close()

    if not api_result and not db_result:
        print("\n❌ Both connections failed!")
        print("Troubleshooting steps:")
        print("1. Check if PostgreSQL server is running on 192.168.2.6")
        print("2. Verify port 5432 is open and accessible")
        print("3. Confirm database 'parkir2' exists")
        print("4. Verify credentials in .env file")
        print("5. Check if API server is running on http://192.168.2.6:5050")
        print("6. Ensure network connectivity to the server")
    elif not api_result:
        print("\n⚠️ API connection failed but database connection works")
        print("Check if the API server is running and accessible")
    elif not db_result:
        print("\n⚠️ Database connection failed but API works")
        print("Check PostgreSQL server configuration and credentials")

if __name__ == "__main__":
    test_connections() 