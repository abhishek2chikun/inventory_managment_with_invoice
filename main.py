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
from pages.manage_sellers import manage_sellers
from pages.company_settings import company_settings
from backup import after_login_logout
from utils.db_manager import init_db
from utils.backup_manager import init_backup
import logging
from utils.logger import setup_logger

# Initialize SQLite database
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Enable foreign key support
c.execute("PRAGMA foreign_keys = ON")

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
                  invoice_number TEXT,  -- Format: INV0001, INV0002, etc.
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

# Create seller_transactions table after invoices table
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

conn.commit()

logger = setup_logger()

def main():
    st.set_page_config(
        page_title="Inventory Management System",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize database
    if not init_db():
        st.error("Failed to initialize database. Please check the logs.")
        return

    # Perform backup
    try:
        if init_backup():
            logger.info("Backup completed successfully")
        else:
            logger.warning("Backup failed or partially completed")
    except Exception as e:
        logger.error(f"Error during backup: {e}")

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

    if not st.session_state.logged_in:
        st.title("Login")
        login()
        return

    # Add custom CSS for the sidebar
    st.markdown("""
        <style>
        .nav-link {
            padding: 0.5rem 1rem !important;
            margin: 0.2rem 0 !important;
        }
        .nav-link:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
        .nav-link.active {
            background-color: #4c85e4 !important;
            border-radius: 5px !important;
        }
        .nav-link-div {
            display: flex !important;
            align-items: center !important;
        }
        .nav-link i {
            margin-right: 0.5rem !important;
            font-size: 1.1rem !important;
        }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create a sidebar menu with categories
    with st.sidebar:
        st.markdown("### 🏢 Business Operations")
        selected = option_menu(
            menu_title=None,
            options=[
                "Create Invoice",
                "Add New Items",
                "Inventory Management",
                "Customer Database",
                "Business Analytics",
                "Business Settings"
            ],
            icons=[
                '📄 receipt-cutoff',  # Create Invoice
                '➕ plus-circle',      # Add New Items
                '📦 box-seam',        # Inventory Management
                '👥 people',          # Customer Database
                '📊 graph-up',        # Business Analytics
                '⚙️ gear'             # Business Settings
            ],
            menu_icon=None,
            default_index=0,
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "transparent"
                },
                "icon": {
                    "font-size": "1rem",
                    "margin-right": "0.5rem"
                },
                "nav-link": {
                    "font-size": "0.9rem",
                    "text-align": "left",
                    "padding": "0.5rem",
                    "border-radius": "5px",
                    "--hover-color": "rgba(255, 255, 255, 0.1)"
                },
                "nav-link-selected": {
                    "background-color": "#4c85e4",
                    "font-weight": "normal"
                }
            }
        )
        
        # Add a divider
        st.markdown("---")
        
        # Add user section at the bottom
        st.markdown("### 👤 User")
        logout()
    
    # Route to the selected page with mapping to original function names
    page_mapping = {
        "Create Invoice": "Invoice Generation",
        "Add New Items": "Add Items",
        "Inventory Management": "Manage Items",
        "Customer Database": "Manage Sellers",
        "Business Analytics": "Reports",
        "Business Settings": "Company Settings"
    }
    
    # Route to the selected page
    if selected == "Create Invoice":
        invoice_generation()
    elif selected == "Add New Items":
        add_items()
    elif selected == "Inventory Management":
        manage_items()
    elif selected == "Customer Database":
        manage_sellers()
    elif selected == "Business Analytics":
        reports()
    elif selected == "Business Settings":
        company_settings()

if __name__ == "__main__":
    main()
