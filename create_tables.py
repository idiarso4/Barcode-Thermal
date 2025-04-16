import psycopg2
import configparser
import hashlib

def create_tables():
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Connect to database
    db_config = config['database']
    conn = psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host']
    )
    
    cursor = conn.cursor()
    
    try:
        # Drop existing tables if they exist
        cursor.execute("""
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS tickets CASCADE;
        """)
        
        # Create users table
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(64) NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Create tickets table
        cursor.execute("""
            CREATE TABLE tickets (
                id SERIAL PRIMARY KEY,
                ticket_id VARCHAR(50) UNIQUE NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                image_path VARCHAR(255),
                status VARCHAR(20) NOT NULL,
                vehicle_type VARCHAR(20),
                license_plate VARCHAR(20),
                fee INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Create default admin user
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        """, ('admin', admin_password, 'admin'))
        
        conn.commit()
        print("✅ Tabel berhasil dibuat")
        print("✅ User admin berhasil dibuat (username: admin, password: admin123)")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_tables() 