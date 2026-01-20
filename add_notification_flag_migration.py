"""
Migration script to add auto_reveal_notified flag to Session table.
Fixes BUG 8: Notification spam when multiple players submit Game 2.

Run on Railway PostgreSQL database.
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    print("Make sure you have a .env file with DATABASE_URL set to your Railway PostgreSQL connection string")
    exit(1)

def run_migration():
    """Add auto_reveal_notified column to sessions table."""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("Adding auto_reveal_notified column to sessions table...")
        
        cursor.execute("""
            ALTER TABLE sessions 
            ADD COLUMN IF NOT EXISTS auto_reveal_notified BOOLEAN DEFAULT FALSE NOT NULL;
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sessions' 
            AND column_name = 'auto_reveal_notified';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"Verified: Column {result[0]} ({result[1]}) exists")
        else:
            print("Warning: Column not found after migration")
            
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
