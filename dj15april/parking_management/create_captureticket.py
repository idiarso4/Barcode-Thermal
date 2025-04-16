import psycopg2
from psycopg2 import sql

def create_captureticket_table():
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Create the captureticket table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS captureticket (
            id SERIAL PRIMARY KEY,
            plat_no VARCHAR(20) NOT NULL,
            date_masuk TIMESTAMP NOT NULL,
            date_keluar TIMESTAMP,
            status VARCHAR(50) NOT NULL,
            biaya DECIMAL(10,2)
        );
        """
        
        cur.execute(create_table_query)
        
        # Create index on plat_no and date_masuk for better performance
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_captureticket_plat_no 
        ON captureticket(plat_no);
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_captureticket_date_masuk 
        ON captureticket(date_masuk DESC);
        """)
        
        # Commit the changes
        conn.commit()
        
        print("Table captureticket created successfully!")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_captureticket_table() 