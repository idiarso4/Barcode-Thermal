import psycopg2
from psycopg2 import sql

def check_table_structure():
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
        
        # Check table structure
        cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'captureticket'
        ORDER BY ordinal_position;
        """)
        
        print("\nTable Structure:")
        print("=" * 80)
        for col in cur.fetchall():
            print(f"Column: {col[0]}")
            print(f"Type: {col[1]}")
            print(f"Max Length: {col[2]}")
            print(f"Nullable: {col[3]}")
            print("-" * 40)
        
        # Check sample data
        cur.execute("""
        SELECT *
        FROM captureticket
        ORDER BY date_masuk DESC
        LIMIT 5;
        """)
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        print("\nSample Data:")
        print("=" * 80)
        print("Columns:", columns)
        for row in rows:
            print(row)
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_table_structure() 