import os
import psycopg2
import sys

def check_connection():
    # Get configuration exactly as the app does
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "garmin")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    print(f"--- Configuration ---")
    print(f"Host: {host}:{port}")
    print(f"Database: {dbname}")
    print(f"User: {user}")
    print(f"Password: '{password}'") 
    
    print("\n--- Attempting Connection ---")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        print("SUCCESS: Connection established successfully!")
        
        # Verify database version and write ability
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"Database Version: {version}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE: Connection failed.")
        print(f"Error details: {e}")
        return False

if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
