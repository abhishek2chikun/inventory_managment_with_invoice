import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database with required schema"""
    try:
        # Read schema file
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        # Connect to database and execute schema
        with get_db_connection() as conn:
            conn.executescript(schema)
            conn.commit()
            logger.info("Database schema initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def ensure_company_details_exist():
    """Ensure company_details table exists and has at least one record"""
    try:
        with get_db_connection() as conn:
            # Check if table exists
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='company_details'
            """)
            if not cursor.fetchone():
                # Initialize database if table doesn't exist
                init_db()
            
            # Check if we have company details
            cursor.execute("SELECT COUNT(*) FROM company_details")
            if cursor.fetchone()[0] == 0:
                # Insert default company details
                cursor.execute("""
                    INSERT INTO company_details (
                        name, address, city, state, state_code, gstin, 
                        phone, email, bank_name, bank_account, bank_ifsc, 
                        bank_branch, jurisdiction
                    ) VALUES (
                        'GANANATH ENTERPRISES',
                        'New Colony',
                        'Rayagada',
                        'Odisha',
                        '21',
                        'XXX1933884',
                        '',
                        '',
                        'HDFC BANK',
                        '50200055243922',
                        'HDFC0000640',
                        'HDFC BANK NAYAPALLI BRANCH',
                        'BHUBANESWAR'
                    )
                """)
                conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error ensuring company details: {e}")
        return False 