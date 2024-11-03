import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect('inventory.db')
        yield conn
    finally:
        if conn:
            conn.close() 