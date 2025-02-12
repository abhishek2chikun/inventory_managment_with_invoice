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
from pages.add_items import add_items
from pages.manage_items import manage_items
from pages.invoice_generation import invoice_generation
from pages.reports import reports
from backup import after_login_logout

# Initialize SQLite database
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS products
             (id INTEGER PRIMARY KEY, company TEXT, category TEXT, item_name TEXT, 
             item_code TEXT, buying_price REAL, selling_price REAL, 
             quantity INTEGER, date_purchased TEXT,
             gst_percentage REAL,
             UNIQUE(company, category, item_name))''')

c.execute('''CREATE TABLE IF NOT EXISTS sellers
             (id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              address TEXT,
              phone TEXT,
              gstin TEXT,
              total_credit REAL DEFAULT 0,
              UNIQUE(name, phone))''')

c.execute('''CREATE TABLE IF NOT EXISTS seller_transactions
             (id INTEGER PRIMARY KEY,
              seller_id INTEGER,
              invoice_id INTEGER,
              amount REAL,
              transaction_type TEXT,
              date TEXT,
              notes TEXT,
              FOREIGN KEY(seller_id) REFERENCES sellers(id),
              FOREIGN KEY(invoice_id) REFERENCES invoices(id))''')

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
                  seller_id INTEGER,
                  payment_status TEXT DEFAULT 'paid',
                  invoice_number TEXT,
                  FOREIGN KEY(seller_id) REFERENCES sellers(id))''')
else:
    # If the table exists, check if all columns are present
    c.execute("PRAGMA table_info(invoices)")
    columns = [column[1] for column in c.fetchall()]
    required_columns = ['invoice_data', 'total_amount', 'date', 'pdf_path', 
                       'seller_id', 'payment_status', 'invoice_number']
    
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

def main():
    if not st.session_state.logged_in:
        st.title("Login")
        login()
        return

    # Create a sidebar menu
    with st.sidebar:
        st.title("Navigation")
        selected = option_menu(
            menu_title=None,
            options=["Add Items", "Manage Items", "Invoice Generation", "Reports", "Logout"],
            icons=["plus-circle", "pencil-square", "receipt", "bar-chart", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )
        
    # Load the appropriate page based on selection
    if selected == "Add Items":
        add_items()
    elif selected == "Manage Items":
        manage_items()
    elif selected == "Invoice Generation":
        invoice_generation()
    elif selected == "Reports":
        reports()
    elif selected == "Logout":
        logout()

if __name__ == "__main__":
    main()
