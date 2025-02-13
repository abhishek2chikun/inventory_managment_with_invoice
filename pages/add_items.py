import streamlit as st
import pandas as pd
import sqlite3
import pytesseract
from PIL import Image
import pdfplumber
from utils.logger import setup_logger
from utils.db_manager import get_db_connection
import time

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
        with st.form("product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                company = st.text_input("Company", key="company", placeholder="Enter company name")
                item_name = st.text_input("Item Name", key="item_name", placeholder="Enter item name")
                buying_price = st.number_input("Item Buying Price (excl. GST)", min_value=0.0, key="buying_price", help="Enter the buying price excluding GST")
                gst_percentage = st.number_input("GST in percentage", value=12.0, min_value=0.0, max_value=100.0, step=0.1, key="gst", help="Enter GST percentage")

            with col2:
                category = st.text_input("Category Name", key="category", placeholder="Enter category name")
                item_code = st.text_input("Item Code", key="item_code", placeholder="Enter unique item code")
                selling_price = st.number_input("Item Selling Price", min_value=0.0, key="selling_price", help="Enter the selling price")
                quantity = st.number_input("Quantity", min_value=0, step=1, key="quantity", help="Enter available quantity")
                date_purchased = st.date_input("Date Purchased", key="date", help="Select purchase date")
            
            # Display buying price with GST for reference
            if buying_price > 0:
                buying_price_with_gst = buying_price * (1 + gst_percentage/100)
                st.info(f"""
                    💰 Buying Price Details:
                    - Without GST: ₹{buying_price:.2f}
                    - GST Amount: ₹{(buying_price_with_gst - buying_price):.2f}
                    - With GST: ₹{buying_price_with_gst:.2f}
                """)
            
            # Add a blank space to separate the button
            st.write("")
            
            # Center-align the button with better styling
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submitted = st.form_submit_button(
                    "➕ Add Product",
                    use_container_width=True,
                    type="primary"
                )
        
        if submitted:
            # Enhanced validation with specific error messages
            validation_failed = False
            if not company:
                st.error("❌ Company name is required")
                validation_failed = True
            if not category:
                st.error("❌ Category name is required")
                validation_failed = True
            if not item_name:
                st.error("❌ Item name is required")
                validation_failed = True
            if not item_code:
                st.error("❌ Item code is required")
                validation_failed = True
            if buying_price <= 0:
                st.error("❌ Buying price must be greater than 0")
                validation_failed = True
            if selling_price <= 0:
                st.error("❌ Selling price must be greater than 0")
                validation_failed = True
            if quantity <= 0:
                st.error("❌ Quantity must be greater than 0")
                validation_failed = True
            
            if validation_failed:
                return False
            
            # Check if product already exists with improved error message
            existing_product = pd.read_sql_query("""
                SELECT * FROM products 
                WHERE company = ? AND category = ? AND item_name = ?
            """, conn, params=(company, category, item_name))
            
            if not existing_product.empty:
                st.error("❌ A product with this combination already exists. Please use the Manage Items page to update existing products.")
                return False
            
            with st.spinner("Adding product..."):
                success, message = add_single_product(
                    conn, company, category, item_name, item_code, 
                    buying_price, selling_price, quantity, 
                    date_purchased, gst_percentage
                )
                if success:
                    st.success(f"✅ {message}")
                    # Clear form values by triggering a rerun
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
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

def create_combined_items_table(field_type, company_value, category_value, num_rows):
    """Create an editable table for multiple items with same company/category"""
    empty_data = {
        'company': [company_value if field_type in ['company', 'both'] else ''] * num_rows,
        'category': [category_value if field_type in ['category', 'both'] else ''] * num_rows,
        'item_name': [''] * num_rows,
        'item_code': [''] * num_rows,
        'buying_price': [0.0] * num_rows,
        'selling_price': [0.0] * num_rows,
        'quantity': [0] * num_rows,
        'gst_percentage': [12.0] * num_rows
    }
    
    df = pd.DataFrame(empty_data)
    
    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        column_config={
            "company": st.column_config.TextColumn(
                "Company",
                disabled=field_type in ['company', 'both'],
                help="Company name"
            ),
            "category": st.column_config.TextColumn(
                "Category",
                disabled=field_type in ['category', 'both'],
                help="Category name"
            ),
            "item_name": st.column_config.TextColumn(
                "Item Name",
                help="Enter item name"
            ),
            "item_code": st.column_config.TextColumn(
                "Item Code",
                help="Enter unique item code"
            ),
            "buying_price": st.column_config.NumberColumn(
                "Buying Price (excl. GST)",
                min_value=0.0,
                format="%.2f",
                help="Enter buying price excluding GST"
            ),
            "selling_price": st.column_config.NumberColumn(
                "Selling Price",
                min_value=0.0,
                format="%.2f",
                help="Enter selling price"
            ),
            "quantity": st.column_config.NumberColumn(
                "Quantity",
                min_value=0,
                step=1,
                help="Enter available quantity"
            ),
            "gst_percentage": st.column_config.NumberColumn(
                "GST %",
                min_value=0.0,
                max_value=100.0,
                format="%.1f",
                help="Enter GST percentage"
            )
        },
        hide_index=True,
        key="combined_items_table"
    )
    
    return edited_df

def add_combined_items(conn, items_df):
    """Add multiple items to the database"""
    success_count = 0
    error_count = 0
    errors = []
    
    for _, item in items_df.iterrows():
        if not item['item_name'] or not item['item_code']:
            continue
            
        try:
            # Calculate buying price including GST
            buying_price_with_gst = item['buying_price'] * (1 + item['gst_percentage']/100)
            
            with conn:
                conn.execute('''
                    INSERT OR REPLACE INTO products 
                    (company, category, item_name, item_code, buying_price, 
                     selling_price, quantity, date_purchased, gst_percentage) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['company'], item['category'], item['item_name'],
                    item['item_code'], buying_price_with_gst, item['selling_price'],
                    item['quantity'], pd.Timestamp.now().strftime('%Y-%m-%d'),
                    item['gst_percentage']
                ))
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append(f"Error adding {item['item_name']}: {str(e)}")
    
    return success_count, error_count, errors

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
        
        # Tab selection with icons
        tab1, tab2, tab3 = st.tabs(["📝 Single Item", "📑 Bulk Upload", "🔄 Combine Items"])
        
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
        
        with tab3:
            st.subheader("Add Multiple Items with Same Company/Category")
            
            # Select field type
            field_type = st.radio(
                "Select field to combine",
                ["company", "category", "both"],
                horizontal=True,
                help="Choose whether to add multiple items with same company, category, or both"
            )
            
            # Input fields based on selection
            if field_type == "both":
                col1, col2, col3 = st.columns(3)
                with col1:
                    company_value = st.text_input(
                        "Enter Company Name",
                        help="All items will share this company name"
                    )
                with col2:
                    category_value = st.text_input(
                        "Enter Category Name",
                        help="All items will share this category name"
                    )
                with col3:
                    num_rows = st.number_input(
                        "Number of Items",
                        min_value=1,
                        max_value=50,
                        value=5,
                        help="How many items to add with this company/category"
                    )
                
                # Validate both fields
                if company_value and category_value:
                    # Create editable table
                    edited_df = create_combined_items_table(field_type, company_value, category_value, num_rows)
                elif company_value or category_value:
                    st.warning("Please enter both Company and Category names")
            else:
                # Original single field input
                col1, col2 = st.columns(2)
                with col1:
                    field_value = st.text_input(
                        f"Enter {field_type.title()} Name",
                        help=f"All items will share this {field_type}"
                    )
                    company_value = field_value if field_type == "company" else ""
                    category_value = field_value if field_type == "category" else ""
                
                with col2:
                    num_rows = st.number_input(
                        "Number of Items",
                        min_value=1,
                        max_value=50,
                        value=5,
                        help="How many items to add with this company/category"
                    )
                
                if field_value:
                    # Create editable table
                    edited_df = create_combined_items_table(field_type, company_value, category_value, num_rows)
            
            # Show save button only if we have a table
            if ((field_type == "both" and company_value and category_value) or 
                (field_type != "both" and field_value)):
                # Add button to save all items
                if st.button("💾 Save All Items", type="primary", use_container_width=True):
                    # Filter out empty rows
                    valid_df = edited_df[
                        (edited_df['item_name'] != '') & 
                        (edited_df['item_code'] != '')
                    ].copy()
                    
                    if valid_df.empty:
                        st.error("Please fill in at least one item's details")
                    else:
                        success_count, error_count, errors = add_combined_items(conn, valid_df)
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully added {success_count} items!")
                        
                        if error_count > 0:
                            st.error(f"❌ Failed to add {error_count} items")
                            for error in errors:
                                st.warning(error)
                        
                        if success_count > 0:
                            time.sleep(0.5)
                            st.rerun()

if __name__ == "__main__":
    add_items() 