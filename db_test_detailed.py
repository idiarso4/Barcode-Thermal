import psycopg2
import socket
import sys

def test_network():
    print("\n1. Testing basic network connectivity...")
    try:
        # Try to create a socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        
        result = sock.connect_ex(('192.168.2.6', 5432))
        if result == 0:
            print("✅ Port 5432 is open and accepting connections")
        else:
            print(f"❌ Port 5432 is not accessible (Error code: {result})")
    except Exception as e:
        print(f"❌ Network test failed: {e}")
    finally:
        sock.close()

def test_db_connection():
    print("\n2. Testing PostgreSQL connection...")
    try:
        print("Attempting to connect with these parameters:")
        print("Host: 192.168.2.6")
        print("Port: 5432")
        print("Database: parkir2")
        print("User: postgres")
        
        conn = psycopg2.connect(
            host="192.168.2.6",
            port="5432",
            database="parkir2",
            user="postgres",
            password="postgres",
            connect_timeout=10  # 10 seconds timeout
        )
        
        print("✅ Successfully connected to PostgreSQL!")
        
        # Get server version
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        # Test query execution
        print("\n3. Testing query execution...")
        cur.execute('SELECT current_timestamp;')
        timestamp = cur.fetchone()
        print(f"Server timestamp: {timestamp[0]}")
        
        cur.close()
        conn.close()
        print("\n✅ All tests completed successfully!")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection failed!")
        print(f"Error details: {str(e)}")
        print("\nPossible solutions:")
        print("1. Check if PostgreSQL is running on the server")
        print("2. Verify postgresql.conf has listen_addresses = '*'")
        print("3. Check pg_hba.conf allows connections from 192.168.2.0/24")
        print("4. Ensure firewall allows TCP port 5432")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")

if __name__ == "__main__":
    print("=== PostgreSQL Connection Test ===")
    test_network()
    test_db_connection() 