import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
import base64
from pages.product_management import product_management
from pages.invoice_generation import invoice_generation
from pages.reports import reports
from pages.bulk_upload import bulk_upload

from backup import after_login_logout




# Initialize SQLite database
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS products
             (id INTEGER PRIMARY KEY, company TEXT, category TEXT, item_name TEXT, 
             item_code TEXT, buying_price REAL, selling_price REAL, 
             unit_per_box INTEGER, quantity INTEGER, date_purchased TEXT,
             gst_percentage REAL,
             UNIQUE(company, category, item_name))''')

# Check if the invoices table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
if c.fetchone() is None:
    # If the table doesn't exist, create it with all columns
    c.execute('''CREATE TABLE invoices
                 (id INTEGER PRIMARY KEY,
                  invoice_data TEXT,
                  total_amount REAL,
                  date TEXT,
                  pdf_path TEXT,
                  customer_name TEXT,
                  customer_address TEXT,
                  customer_phone TEXT,
                  invoice_number TEXT)''')
else:
    # If the table exists, check if all columns are present
    c.execute("PRAGMA table_info(invoices)")
    columns = [column[1] for column in c.fetchall()]
    required_columns = ['invoice_data', 'total_amount', 'date', 'pdf_path', 
                        'customer_name', 'customer_address', 'customer_phone', 'invoice_number']
    
    for column in required_columns:
        if column not in columns:
            # If a required column doesn't exist, add it
            c.execute(f"ALTER TABLE invoices ADD COLUMN {column} TEXT")

conn.commit()

st.set_page_config(page_title="Inventory Management System", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    if st.button("Log in"):
        st.session_state.logged_in = True
        after_login_logout()
        st.rerun()

def logout():
    if st.button("Log out"):
        st.session_state.logged_in = False
        after_login_logout()
        st.rerun()

login_page = st.Page(login, title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")

product_management_page = st.Page(product_management, title="Product Management", icon=":material/box:", default=True)
invoice_generation_page = st.Page(invoice_generation, title="Invoice Generation", icon=":material/receipt:")
reports_page = st.Page(reports, title="Reports", icon=":material/bar_chart:")
bulk_upload_page = st.Page(bulk_upload, title="Bulk Upload", icon=":material/upload:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Account": [logout_page],
            "Inventory": [
                product_management_page, 
                invoice_generation_page, 
                bulk_upload_page,
                reports_page
            ],
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()
