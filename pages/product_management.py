import streamlit as st
import pandas as pd
import sqlite3

def add_product(conn, company, category, item_name, item_code, buying_price, selling_price, unit_per_box, quantity, date_purchased, gst_percentage):
    try:
        with conn:
            conn.execute('''INSERT OR REPLACE INTO products 
                         (company, category, item_name, item_code, buying_price, 
                         selling_price, unit_per_box, quantity, date_purchased, gst_percentage) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (company, category, item_name, item_code, buying_price,
                       selling_price, unit_per_box, quantity, str(date_purchased), gst_percentage))
        return True, "Product added/updated successfully!"
    except sqlite3.IntegrityError:
        return False, "Error: A product with this combination of Company, Category, and Item Name already exists."

def product_form(conn):
    with st.form("product_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company = st.text_input("Company")
            item_name = st.text_input("Item Name")
            buying_price = st.number_input("Item Buying Price", min_value=0.0)
            gst_percentage = st.number_input("GST in percentage", value=12.0, min_value=0.0, max_value=100.0, step=0.1)
            unit_per_box = st.number_input("Box (unit per box)", min_value=1, step=1)

        with col2:
            category = st.text_input("Category Name")
            item_code = st.text_input("Item Code")
            selling_price = st.number_input("Item Selling Price", min_value=0.0)
            quantity = st.number_input("Quantity", min_value=0, step=1)
            date_purchased = st.date_input("Date Purchased")
        
        submitted = st.form_submit_button("Add/Update Product")
        
        if submitted:
            if company == category == item_name:
                st.warning("Warning: Company, Category, and Item Name are all the same.")
            
            success, message = add_product(conn, company, category, item_name, item_code, buying_price,
                                           selling_price, unit_per_box, quantity, date_purchased, gst_percentage)
            if success:
                st.success(message)
            else:
                st.error(message)
            return success

    return False

def product_management(conn=None):
    if conn is None:
        conn = sqlite3.connect('inventory.db')
    
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         company TEXT,
                         category TEXT,
                         item_name TEXT,
                         item_code TEXT,
                         buying_price REAL,
                         selling_price REAL,
                         unit_per_box INTEGER,
                         quantity INTEGER,
                         date_purchased TEXT,
                         gst_percentage REAL,
                         UNIQUE(company, category, item_name))''')
    
    product_form(conn)
    
    st.subheader("Product List")
    df = pd.read_sql_query("SELECT * FROM products", conn)
    st.dataframe(df)
    
    col1, col2 = st.columns(2)
    with col1:
        product_to_delete = st.selectbox("Select product to delete", df['item_name'].tolist())
    with col2:
        if st.button("Delete Product"):
            with conn:
                conn.execute("DELETE FROM products WHERE item_name = ?", (product_to_delete,))
            st.success(f"Product '{product_to_delete}' deleted successfully!")

if __name__ == "__main__":
    product_management()

