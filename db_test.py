import psycopg2

# Database connection details
DB_HOST = "192.168.2.6"
DB_PORT = "5432"
DB_NAME = "parkir2"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

def test_connection():
    try:
        # Try to establish a connection
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # If connection successful, print success message
        print("✅ Successfully connected to the database!")
        
        # Get server version
        cursor = connection.cursor()
        cursor.execute('SELECT version();')
        db_version = cursor.fetchone()
        print(f"Database version: {db_version[0]}")
        
        # Close cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed successfully.")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed!")
        print(f"Error details: {str(e)}")
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    test_connection() 