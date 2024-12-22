import sqlite3
import shutil
import os
from datetime import datetime
import schedule
import time

def backup_database():
    # Source database file
    src_db = 'inventory.db'
    
    # Create a 'backups' directory if it doesn't exist
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    # Generate a timestamp for the backup file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Destination backup file
    dst_db = f'backups/inventory_backup_{timestamp}.db'
    
    try:
        # Check if the source database exists
        if not os.path.exists(src_db):
            print(f"Error: Source database '{src_db}' not found.")
            return False
        
        # Create a connection to the database
        conn = sqlite3.connect(src_db)
        
        # Close the connection to ensure all changes are written
        conn.close()
        
        # Copy the database file
        shutil.copy2(src_db, dst_db)
        
        print(f"Database backup created successfully: {dst_db}")
        
        # Add rotation of old backups
        MAX_BACKUPS = 10  # Keep last 30 backups
        
        # Remove old backups
        backup_files = sorted(os.listdir('backups'))
        if len(backup_files) > MAX_BACKUPS:
            for old_backup in backup_files[:-MAX_BACKUPS]:
                os.remove(os.path.join('backups', old_backup))
        
        return True
    except Exception as e:
        print(f"Error creating database backup: {str(e)}")
        return False

# def schedule_backup():
#     schedule.every().week.do(backup_database)
#     schedule.run_pending()

# Function to be called after login or logout
def after_login_logout():
    backup_database()
    # schedule_backup()
