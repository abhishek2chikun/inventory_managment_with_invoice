import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    try:
        yield conn
    finally:
        conn.close() 