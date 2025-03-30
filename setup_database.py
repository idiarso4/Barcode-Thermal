import psycopg2
from psycopg2 import Error
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='database_setup.log'
)
logger = logging.getLogger(__name__)

def setup_database():
    # Database connection details
    db_configs = [
        {
            "host": "localhost",
            "port": "5432",
            "database": "parkir2",
            "user": "postgres",
            "password": "postgres"
        },
        {
            "host": "192.168.2.6",
            "port": "5432",
            "database": "parkir2",
            "user": "postgres",
            "password": "postgres"
        }
    ]
    
    max_retries = 3
    
    for db_config in db_configs:
        retry_count = 0
        print(f"\nTrying connection to {db_config['host']}...")
        
        while retry_count < max_retries:
            try:
                logger.info(f"Attempting to connect to database at {db_config['host']}...")
                print(f"Attempt {retry_count + 1} of {max_retries}")
                print(f"Connecting to PostgreSQL at {db_config['host']}:{db_config['port']}")
                
                # Try to connect
                connection = psycopg2.connect(**db_config)
                cursor = connection.cursor()
                
                print(f"✅ Successfully connected to {db_config['host']}")
                
                # Check if Vehicles table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'vehicles'
                    );
                """)
                
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    logger.info("Creating Vehicles table...")
                    print("Creating Vehicles table...")
                    
                    # Create Vehicles table
                    cursor.execute("""
                        CREATE TABLE public.vehicles (
                            id SERIAL PRIMARY KEY,
                            plate_number VARCHAR(20) NOT NULL,
                            vehicle_type VARCHAR(10) NOT NULL,
                            ticket_number VARCHAR(50) UNIQUE NOT NULL,
                            entry_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            is_parked BOOLEAN DEFAULT true,
                            exit_time TIMESTAMP
                        );
                    """)
                    
                    # Create index on plate_number
                    cursor.execute("""
                        CREATE INDEX idx_plate_number ON public.vehicles(plate_number);
                    """)
                    
                    # Create index on ticket_number
                    cursor.execute("""
                        CREATE INDEX idx_ticket_number ON public.vehicles(ticket_number);
                    """)
                    
                    connection.commit()
                    logger.info("Vehicles table created successfully")
                    print("✅ Database setup completed successfully!")
                else:
                    logger.info("Vehicles table already exists")
                    print("✅ Database tables are already set up")
                
                # Test insert
                try:
                    cursor.execute("""
                        INSERT INTO public.vehicles 
                        (plate_number, vehicle_type, ticket_number) 
                        VALUES 
                        ('TEST123', 'Motor', 'TEST-001')
                        ON CONFLICT (ticket_number) DO NOTHING;
                    """)
                    connection.commit()
                    logger.info("Test insert successful")
                    print("✅ Database write test successful")
                    
                    # If we get here, everything worked with this config
                    # Update app3.py with the working configuration
                    update_app_config(db_config)
                    return True
                    
                except Error as e:
                    logger.error(f"Test insert failed: {e}")
                    print(f"❌ Database write test failed: {e}")
                
            except Error as e:
                retry_count += 1
                logger.error(f"Database connection attempt {retry_count} failed: {e}")
                print(f"❌ Connection failed: {e}")
                
                if retry_count < max_retries:
                    wait_time = 5 * retry_count
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print("\nTroubleshooting steps for", db_config['host'])
                    print("1. Verify PostgreSQL is running on the server")
                    print("2. Check if port 5432 is open in the firewall")
                    print("3. Verify database 'parkir2' exists")
                    print("4. Check if the user 'postgres' has proper permissions")
                    print("5. Try connecting using psql or pgAdmin to verify credentials")
                    if db_config['host'] == 'localhost':
                        print("6. Check if PostgreSQL service is running:")
                        print("   - Open Services (services.msc)")
                        print("   - Look for 'PostgreSQL' service")
                        print("   - Make sure it's running")
                    
            finally:
                if 'connection' in locals():
                    cursor.close()
                    connection.close()
                    logger.info("Database connection closed")
    
    print("\n❌ Could not connect to any database server")
    return False

def update_app_config(working_config):
    """Update app3.py with working database configuration"""
    try:
        with open('app3.py', 'r') as file:
            content = file.read()
            
        # Update the configuration
        content = content.replace(
            'DB_HOST = "192.168.2.6"',
            f'DB_HOST = "{working_config["host"]}"'
        )
        
        with open('app3.py', 'w') as file:
            file.write(content)
            
        print(f"\n✅ Updated app3.py with working configuration ({working_config['host']})")
    except Exception as e:
        print(f"❌ Failed to update app3.py: {e}")

if __name__ == "__main__":
    setup_database() 