import streamlit as st
import pandas as pd
from datetime import date
from db import Database


# Function to check if billing_from_name exists in the database
def billing_from_name_exists(billing_from_name):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM items WHERE billing_from_name=%s"
    cursor.execute(query, (billing_from_name,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0

# Function to fetch existing agencies from the database
def fetch_existing_agencies():
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT billing_from_name FROM items"
    cursor.execute(query)
    agencies = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return agencies

# Function to insert items into the database
def insert_items(items):
    print("insert items")
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = ("INSERT INTO items (billing_from_name, category_name, item_name, box, quantity, "
             "item_buying_price, item_selling_price, sgst, cgst, "
             "buying_price_after_tax_per_quantity, total_buying_price_after_tax, date_purchased) "
             "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    
    try:
        for item in items:
            print(item)
            cursor.execute(query, tuple(item))
        conn.commit()
        st.success('Items added successfully!')
    except Exception as e:
        conn.rollback()
        st.error(f'Error adding items: {e}')
    finally:
        cursor.close()


st.title('Create Items')
c1,c2,c3 = st.columns(3)
with c2:

    # Input fields for selecting or creating a new agency
    agency_option = st.radio('Select or Create Agency:', ('Select Existing Agency', 'Create New Agency'))
    if agency_option == 'Select Existing Agency':
        existing_agencies = fetch_existing_agencies()
        billing_from_name_input = st.selectbox('Select Agency:', existing_agencies)
        # Proceed if agency name is provided
        if billing_from_name_input:
            billing_from_name = billing_from_name_input.lower().replace(' ', '_')
    
    else:
        billing_from_name_input = st.text_input('Enter New Agency Name:')

        # Proceed if agency name is provided
        if billing_from_name_input:
            billing_from_name = billing_from_name_input.lower().replace(' ', '_')

            # Check if agency already exists
            if billing_from_name_exists(billing_from_name):
                st.error(f'The agency "{billing_from_name_input}" already exists.')
            
    st.subheader('Enter Items')

    date_purchased = st.date_input('Date Purchased', value=date.today(), key='date')

# Data entry for multiple items divided into two columns
col1, col2 = st.columns(2)
with col1:
    category_name_input = st.text_input('Category Name', key='category')
    box = st.number_input('Box', min_value=0, key='box')

    item_buying_price = st.number_input('Item Buying Price', min_value=0.0, format="%.2f",step=0.1, key='buying_price')
    sgst = st.number_input('SGST (%)',value=6.0,step=0.1, key='sgst')

with col2:
    item_name_input = st.text_input('Item Name', key='item')
    quantity = st.number_input('Quantity', min_value=0, key='quantity')
    item_selling_price = st.number_input('Item Selling Price', min_value=0.0, format="%.2f",step=0.1, key='selling_price')

    cgst = st.number_input('CGST (%)',value=6.0,step=0.1, key='cgst')

# Calculate derived fields
with col1:
    buying_price_after_tax_per_quantity = item_buying_price * (1 + (sgst + cgst) / 100)
with col2:
    total_buying_price_after_tax = quantity * box * buying_price_after_tax_per_quantity

if st.checkbox('Add Item'):

    # Add item to session state dictionary
    new_item = {
        'billing_from_name': billing_from_name,
        'category_name': category_name_input.lower().replace(' ', '_'),
        'item_name': item_name_input.lower().replace(' ', '_'),
        'box': box,
        'quantity': quantity,
        'item_buying_price': item_buying_price,
        'item_selling_price': item_selling_price,
        'sgst': sgst,
        'cgst': cgst,
        'buying_price_after_tax_per_quantity': buying_price_after_tax_per_quantity,
        'total_buying_price_after_tax': total_buying_price_after_tax,
        'date_purchased': date_purchased
    }


try:
    if new_item:
        df_items = pd.DataFrame([new_item])
        st.subheader('Items to be added:')

        edited_df = st.data_editor(df_items, num_rows="dynamic",hide_index=True)

        # Button to insert all items into the database
        if st.button('Upload Items'):
            print(edited_df.values)
            insert_items(edited_df.values)
except:
    pass

