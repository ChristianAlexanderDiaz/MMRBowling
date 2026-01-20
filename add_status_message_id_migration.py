"""
Migration script to add status_message_id column to sessions table.

This script adds a new column to track the Discord message ID for the status embed
that shows real-time submission progress.

Run this script once to update an existing database:
    python add_status_message_id_migration.py
"""
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Extract database path from SQLite URL
# Format: sqlite:///path/to/database.db
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
else:
    raise ValueError("This migration script only supports SQLite databases")

print(f"Connecting to database: {db_path}")

try:
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'status_message_id' in columns:
        print("Column 'status_message_id' already exists in sessions table. No migration needed.")
    else:
        print("Adding 'status_message_id' column to sessions table...")
        cursor.execute("""
            ALTER TABLE sessions 
            ADD COLUMN status_message_id VARCHAR(20)
        """)
        conn.commit()
        print("Successfully added 'status_message_id' column!")

    conn.close()
    print("Migration complete.")

except sqlite3.Error as e:
    print(f"Database error: {e}")
    raise
except Exception as e:
    print(f"Error: {e}")
    raise
