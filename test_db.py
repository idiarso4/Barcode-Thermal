import psycopg2
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parking.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('db_test')

DB_CONFIG = {
    'host': '192.168.2.6',
    'port': '5432',
    'database': 'parkir2',
    'user': 'postgres',
    'password': 'postgres'
}

def test_db():
    try:
        logger.info("Attempting database connection...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Test query
        cur.execute('SELECT COUNT(*) FROM public."Vehicles"')
        count = cur.fetchone()[0]
        
        result = f"""
Database Connection Test:
------------------------
Host: {DB_CONFIG['host']}
Database: {DB_CONFIG['database']}
Status: Connected
Total Vehicles: {count}
        """
        logger.info(result)
        print(result)
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        error_msg = f"""
Database Connection Error:
------------------------
Error: {str(e)}
        """
        logger.error(error_msg)
        print(error_msg)
        return False

if __name__ == "__main__":
    test_db() 