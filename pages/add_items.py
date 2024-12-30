import streamlit as st
import pandas as pd
import sqlite3
import pytesseract
from PIL import Image
import pdfplumber
from utils.logger import setup_logger
from utils.db_manager import get_db_connection

logger = setup_logger()

def add_single_product(conn, company, category, item_name, item_code, buying_price, 
                      selling_price, quantity, date_purchased, gst_percentage):
    try:
        # Calculate buying price including GST
        buying_price_with_gst = buying_price * (1 + gst_percentage/100)
        
        with conn:
            conn.execute('''INSERT OR REPLACE INTO products 
                         (company, category, item_name, item_code, buying_price, 
                         selling_price, quantity, date_purchased, gst_percentage) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (company, category, item_name, item_code, buying_price_with_gst,
                       selling_price, quantity, str(date_purchased), gst_percentage))
        return True, "Product added successfully!"
    except sqlite3.IntegrityError:
        return False, "Error: A product with this combination already exists."

def single_product_form(conn):
    # Create a container for the form
    form_container = st.container()
    
    with form_container:
        with st.form("product_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                company = st.text_input("Company", key="company")
                item_name = st.text_input("Item Name", key="item_name")
                buying_price = st.number_input("Item Buying Price (excl. GST)", min_value=0.0, key="buying_price")
                gst_percentage = st.number_input("GST in percentage", value=12.0, min_value=0.0, max_value=100.0, step=0.1, key="gst")

            with col2:
                category = st.text_input("Category Name", key="category")
                item_code = st.text_input("Item Code", key="item_code")
                selling_price = st.number_input("Item Selling Price", min_value=0.0, key="selling_price")
                quantity = st.number_input("Quantity", min_value=0, step=1, key="quantity")
                date_purchased = st.date_input("Date Purchased", key="date")
            
            # Display buying price with GST for reference
            if buying_price > 0:
                buying_price_with_gst = buying_price * (1 + gst_percentage/100)
                st.info(f"""
                    Buying Price Details:
                    - Without GST: ₹{buying_price:.2f}
                    - GST Amount: ₹{(buying_price_with_gst - buying_price):.2f}
                    - With GST: ₹{buying_price_with_gst:.2f}
                """)
            
            # Add a blank space to separate the button
            st.write("")
            
            # Center-align the button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                submitted = st.form_submit_button(
                    "Add Product",
                    use_container_width=True,
                    type="primary"  # Makes the button more prominent
                )
        
        if submitted:
            # Enhanced validation including quantity check
            if not all([company, category, item_name, item_code]):
                st.error("Please fill in all required fields")
                return False
            
            if buying_price <= 0:
                st.error("Buying price must be greater than 0")
                return False
            
            if selling_price <= 0:
                st.error("Selling price must be greater than 0")
                return False
            
            if quantity <= 0:
                st.error("Quantity must be greater than 0")
                return False
            
            # Check if product already exists
            existing_product = pd.read_sql_query("""
                SELECT * FROM products 
                WHERE company = ? AND category = ? AND item_name = ?
            """, conn, params=(company, category, item_name))
            
            if not existing_product.empty:
                st.error("A product with this combination already exists. Please use the Manage Items page to update existing products.")
                return False
            
            success, message = add_single_product(
                conn, company, category, item_name, item_code, 
                buying_price, selling_price, quantity, 
                date_purchased, gst_percentage
            )
            if success:
                st.success(message)
            else:
                st.error(message)
            return success

    return False

def process_file(file, column_mapping=None):
    try:
        if file.type.startswith('image'):
            image = Image.open(file)
            text = pytesseract.image_to_string(image)
            # Convert OCR text to DataFrame
            lines = text.split('\n')
            data = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        data.append({
                            'raw_text': line,
                            'detected_values': parts
                        })
            df = pd.DataFrame(data)
            
        elif file.type == 'application/pdf':
            text = ""
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            # Convert PDF text to DataFrame (similar to image processing)
            lines = text.split('\n')
            data = []
            for line in lines:
                if line.strip():
                    data.append({'raw_text': line})
            df = pd.DataFrame(data)
            
        else:  # Excel/CSV
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            required_columns = ['company', 'category', 'item_name', 'item_code', 
                              'buying_price', 'selling_price', 'quantity', 'gst_percentage']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            
            return df[required_columns]
        
        return df
    
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return None

def add_items():
    st.title("Add Items to Inventory")
    
    # Initialize database
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     company TEXT,
                     category TEXT,
                     item_name TEXT,
                     item_code TEXT,
                     buying_price REAL,
                     selling_price REAL,
                     quantity INTEGER,
                     date_purchased TEXT,
                     gst_percentage REAL,
                     UNIQUE(company, category, item_name),
                     UNIQUE(item_code)
                     )''')
        
        # Tab selection
        tab1, tab2 = st.tabs(["Single Item Upload", "Bulk Upload"])
        
        with tab1:
            single_product_form(conn)
        
        with tab2:
            st.subheader("Bulk Upload Products")
            file = st.file_uploader("Choose a file", type=['csv', 'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'])
            
            if file:
                df = process_file(file)
                
                if df is not None:
                    st.subheader("Map Columns")
                    required_columns = ['company', 'category', 'item_name', 'item_code', 
                                      'buying_price', 'selling_price', 'quantity', 'gst_percentage']
                    
                    column_mapping = {}
                    for required_col in required_columns:
                        column_mapping[required_col] = st.selectbox(
                            f"Map {required_col} to:",
                            options=[''] + list(df.columns),
                            key=f"map_{required_col}"
                        )
                    
                    if st.button("Preview Mapped Data"):
                        mapped_df = process_file(file, column_mapping)
                        if mapped_df is not None:
                            st.subheader("Review and Edit Products")
                            edited_df = st.data_editor(
                                mapped_df,
                                num_rows="dynamic",
                                column_config={
                                    "company": st.column_config.TextColumn("Company"),
                                    "category": st.column_config.TextColumn("Category"),
                                    "item_name": st.column_config.TextColumn("Item Name"),
                                    "item_code": st.column_config.TextColumn("Item Code"),
                                    "buying_price": st.column_config.NumberColumn("Buying Price (excl. GST)", min_value=0.0),
                                    "selling_price": st.column_config.NumberColumn("Selling Price", min_value=0.0),
                                    "quantity": st.column_config.NumberColumn("Quantity", min_value=0),
                                    "gst_percentage": st.column_config.NumberColumn("GST %", min_value=0.0, max_value=100.0)
                                }
                            )
                            
                            if st.button("Upload to Database"):
                                success_count = 0
                                error_count = 0
                                
                                for _, row in edited_df.iterrows():
                                    try:
                                        # Validate quantity
                                        if row['quantity'] <= 0:
                                            st.warning(f"Skipping {row['item_name']}: Quantity must be greater than 0")
                                            error_count += 1
                                            continue
                                            
                                        # Calculate buying price with GST before adding
                                        buying_price_with_gst = row['buying_price'] * (1 + row['gst_percentage']/100)
                                        success, _ = add_single_product(
                                            conn, row['company'], row['category'], row['item_name'],
                                            row['item_code'], row['buying_price'], row['selling_price'],
                                            row['quantity'], pd.Timestamp.now(), row['gst_percentage']
                                        )
                                        if success:
                                            success_count += 1
                                        else:
                                            error_count += 1
                                    except Exception as e:
                                        error_count += 1
                                        logger.error(f"Error adding product: {e}")
                                
                                st.success(f"Successfully added {success_count} products!")
                                if error_count > 0:
                                    st.warning(f"{error_count} products failed to add")

if __name__ == "__main__":
    add_items() 