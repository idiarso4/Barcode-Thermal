import psycopg2

def create_table():
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
        
        # Create the table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS captureticket (
                id SERIAL PRIMARY KEY,
                plat_no VARCHAR(20),
                date_masuk TIMESTAMP,
                date_keluar TIMESTAMP NULL,
                status VARCHAR(50),
                biaya DECIMAL(10,2) NULL
            )
        """)
        
        # Commit the transaction
        conn.commit()
        print("Table created successfully!")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_table() 