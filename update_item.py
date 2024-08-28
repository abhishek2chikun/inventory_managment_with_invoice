import streamlit as st
import pandas as pd
from db import Database

# Function to fetch categories from the database
def fetch_categories():
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT category_name FROM items"
    cursor.execute(query)
    categories = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return categories

# Function to fetch existing agencies from the database
def fetch_existing_agencies():
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT billing_from_name FROM items"
    cursor.execute(query)
    agencies = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return agencies

# Function to fetch items based on billing_from_name
def fetch_items_by_agency(agency_name):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM items WHERE billing_from_name = %s"
    cursor.execute(query, (agency_name,))
    items = cursor.fetchall()
    cursor.close()
    return items

# Function to fetch items based on category_name
def fetch_items_by_category(category_name):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM items WHERE category_name = %s"
    cursor.execute(query, (category_name,))
    items = cursor.fetchall()
    cursor.close()
    return items

# Function to update items in the database
def update_item_in_db(item_id, updated_item):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = ("UPDATE items SET billing_from_name = %s, category_name = %s, item_name = %s, box = %s, "
             "quantity = %s, item_buying_price = %s, item_selling_price = %s, sgst = %s, cgst = %s, "
             "buying_price_after_tax_per_quantity = %s, total_buying_price_after_tax = %s, date_purchased = %s "
             "WHERE id = %s")
    cursor.execute(query, (
        updated_item['billing_from_name'],
        updated_item['category_name'],
        updated_item['item_name'],
        updated_item['box'],
        updated_item['quantity'],
        updated_item['item_buying_price'],
        updated_item['item_selling_price'],
        updated_item['sgst'],
        updated_item['cgst'],
        updated_item['buying_price_after_tax_per_quantity'],
        updated_item['total_buying_price_after_tax'],
        updated_item['date_purchased'],
        item_id
    ))
    conn.commit()
    cursor.close()

# Streamlit UI
st.title('Update Items')

# Option to choose filter by agency or category
filter_option = st.radio('Filter By:', ('Agency Name', 'Category'))

if filter_option == 'Agency Name':
    agencies = fetch_existing_agencies()
    agency_name_input = st.selectbox('Select Agency:', agencies)
    if agency_name_input:
        items = fetch_items_by_agency(agency_name_input)
else:
    categories = fetch_categories()
    category_name_input = st.selectbox('Select Category:', categories)
    if category_name_input:
        items = fetch_items_by_category(category_name_input)

# Display items in a DataFrame
if items:
    df_items = pd.DataFrame(items, columns=[
        'ID', 'Billing From Name', 'Category Name', 'Item Name', 'Box', 
        'Quantity', 'Item Buying Price', 'Item Selling Price', 'SGST', 'CGST', 
        'Buying Price After Tax Per Quantity', 'Total Buying Price After Tax', 'Date Purchased'
    ])
    
    # Editable DataFrame
    edited_df = st.data_editor(df_items, num_rows="dynamic", hide_index=True)

    # Button to update items in the database
    if st.button('Update Items'):
        for index, row in edited_df.iterrows():
            item_id = row['ID']
            updated_item = {
                'billing_from_name': row['Billing From Name'].lower().replace(' ', '_'),
                'category_name': row['Category Name'].lower().replace(' ', '_'),
                'item_name': row['Item Name'].lower().replace(' ', '_'),
                'box': row['Box'],
                'quantity': row['Quantity'],
                'item_buying_price': row['Item Buying Price'],
                'item_selling_price': row['Item Selling Price'],
                'sgst': row['SGST'],
                'cgst': row['CGST'],
                'buying_price_after_tax_per_quantity': row['Buying Price After Tax Per Quantity'],
                'total_buying_price_after_tax': row['Total Buying Price After Tax'],
                'date_purchased': row['Date Purchased']
            }
            try:
                update_item_in_db(item_id, updated_item)
                st.success('Items updated successfully!')
            except Exception as e:
                st.error(f'Error updating items: {e}')
else:
    st.warning('No items found for the selected criteria.')
