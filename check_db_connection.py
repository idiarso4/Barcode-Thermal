import psycopg2
from psycopg2 import Error

def check_database_connection():
    # Database connection details
    db_config = {
        "host": "192.168.2.6",
        "port": "5432",
        "database": "parkir2",
        "user": "postgres",
        "password": "postgres"
    }
    
    try:
        # Mencoba membuat koneksi
        print("Mencoba koneksi ke database...")
        print(f"Host: {db_config['host']}")
        print(f"Port: {db_config['port']}")
        print(f"Database: {db_config['database']}")
        print(f"User: {db_config['user']}")
        
        connection = psycopg2.connect(**db_config)
        
        # Mengecek versi database
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        print("\nStatus Koneksi:")
        print("✅ Berhasil terhubung ke database!")
        print(f"📊 Versi Database: {db_version[0]}")
        
        # Mengecek tabel parking_tickets
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'parking_tickets'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                print("✅ Tabel 'parking_tickets' ditemukan")
                
                # Mengecek struktur tabel
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'parking_tickets';
                """)
                columns = cursor.fetchall()
                
                print("\nStruktur tabel parking_tickets:")
                for column in columns:
                    print(f"- {column[0]}: {column[1]}")
            else:
                print("❌ Tabel 'parking_tickets' tidak ditemukan")
                print("\nMembuat tabel parking_tickets...")
                
                # Membuat tabel jika belum ada
                cursor.execute("""
                    CREATE TABLE parking_tickets (
                        ticket_number VARCHAR PRIMARY KEY,
                        plate_number VARCHAR NOT NULL,
                        entry_time TIMESTAMP NOT NULL,
                        status VARCHAR NOT NULL
                    );
                """)
                connection.commit()
                print("✅ Tabel 'parking_tickets' berhasil dibuat!")
                
        except Error as e:
            print(f"❌ Error saat mengecek/membuat tabel: {e}")
        
    except Error as e:
        print("\nStatus Koneksi:")
        print("❌ Gagal terhubung ke database!")
        print(f"Error: {e}")
        
        # Memberikan saran troubleshooting
        print("\nSaran troubleshooting:")
        print("1. Pastikan PostgreSQL server berjalan di 192.168.2.6")
        print("2. Periksa firewall mengizinkan koneksi ke port 5432")
        print("3. Pastikan kredensial database benar")
        print("4. Cek apakah database 'parkir2' sudah dibuat")
        
    finally:
        # Menutup koneksi
        if 'connection' in locals():
            cursor.close()
            connection.close()
            print("\nKoneksi database ditutup.")

if __name__ == "__main__":
    check_database_connection() 