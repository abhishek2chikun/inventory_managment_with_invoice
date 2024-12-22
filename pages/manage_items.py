import streamlit as st
import pandas as pd
from utils.db_manager import get_db_connection
from datetime import datetime

def filter_products(df, filters):
    filtered_df = df.copy()
    
    if filters.get('company'):
        filtered_df = filtered_df[filtered_df['company'].str.contains(filters['company'], case=False, na=False)]
    
    if filters.get('category'):
        filtered_df = filtered_df[filtered_df['category'].str.contains(filters['category'], case=False, na=False)]
    
    if filters.get('item_name'):
        filtered_df = filtered_df[filtered_df['item_name'].str.contains(filters['item_name'], case=False, na=False)]
    
    return filtered_df

def manage_items():
    st.title("Manage Inventory Items")
    
    with get_db_connection() as conn:
        # Load all products
        df = pd.read_sql_query("SELECT * FROM products", conn)
        
        # Convert string dates to datetime
        df['date_purchased'] = pd.to_datetime(df['date_purchased'])
        
        # Filters
        st.subheader("Filter Products")
        col1, col2, col3 = st.columns(3)
        
        filters = {}
        with col1:
            filters['company'] = st.text_input("Company Contains")
            
        with col2:
            filters['category'] = st.text_input("Category Contains")
            
        with col3:
            filters['item_name'] = st.text_input("Item Name Contains")
        
        # Apply filters
        filtered_df = filter_products(df, filters)
        
        # Display and edit products
        st.subheader("Product List")
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "id": None,  # Hide ID column
                "company": st.column_config.TextColumn("Company"),
                "category": st.column_config.TextColumn("Category"),
                "item_name": st.column_config.TextColumn("Item Name"),
                "item_code": st.column_config.TextColumn("Item Code"),
                "buying_price": st.column_config.NumberColumn("Buying Price (incl. GST)", min_value=0.1),
                "selling_price": st.column_config.NumberColumn("Selling Price", min_value=0.1),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=1),
                "date_purchased": st.column_config.DateColumn(
                    "Date Purchased",
                    format="YYYY-MM-DD",
                    step=1,
                ),
                "gst_percentage": st.column_config.NumberColumn("GST %", min_value=0.0, max_value=100.0)
            },
            hide_index=True,
            num_rows="dynamic"
        )
        
        if st.button("Save Changes"):
            try:
                # Validate quantities before saving
                if (edited_df['quantity'] <= 0).any():
                    st.error("Quantity must be greater than 0 for all products")
                    return
                    
                # Update changed rows
                for index, row in edited_df.iterrows():
                    date_str = row['date_purchased']
                    if isinstance(date_str, pd.Timestamp):
                        date_str = date_str.strftime('%Y-%m-%d')
                    elif isinstance(date_str, str):
                        # Ensure string dates are properly formatted
                        date_str = pd.to_datetime(date_str).strftime('%Y-%m-%d')
                    
                    conn.execute("""
                        UPDATE products 
                        SET company=?, category=?, item_name=?, item_code=?, 
                            buying_price=?, selling_price=?, quantity=?, 
                            date_purchased=?, gst_percentage=?
                        WHERE id=?
                    """, (
                        row['company'], row['category'], row['item_name'], row['item_code'],
                        row['buying_price'], row['selling_price'], row['quantity'],
                        date_str, row['gst_percentage'], row['id']
                    ))
                conn.commit()
                st.success("Changes saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving changes: {e}")
        
        # Delete products
        st.subheader("Delete Products")
        
        # Create a DataFrame with unique combinations of item_name and item_code
        delete_options = filtered_df[['item_name', 'item_code']].apply(
            lambda x: f"{x['item_name']} (Code: {x['item_code']})", axis=1
        ).tolist()
        
        products_to_delete = st.multiselect(
            "Select products to delete",
            delete_options
        )
        
        if products_to_delete and st.button("Delete Selected Products"):
            try:
                for product in products_to_delete:
                    # Extract item_name and item_code from the selected option
                    item_name = product.split(" (Code: ")[0]
                    item_code = product.split(" (Code: ")[1].rstrip(")")
                    
                    conn.execute("""
                        DELETE FROM products 
                        WHERE item_name = ? AND item_code = ?
                    """, (item_name, item_code))
                
                conn.commit()
                st.success(f"Successfully deleted {len(products_to_delete)} products!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting products: {e}")

if __name__ == "__main__":
    manage_items() 