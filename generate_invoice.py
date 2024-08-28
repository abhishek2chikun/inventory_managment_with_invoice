import streamlit as st
import pandas as pd
from datetime import date
from db import Database
from invoice_template import generate_invoice_pdf



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
import streamlit as st
import pandas as pd
from datetime import date
from db import Database

# Function to fetch products based on agency name
def fetch_products_by_agency(agency_name):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT id, item_name, category_name, item_selling_price, quantity FROM items WHERE billing_from_name = %s"
    cursor.execute(query, (agency_name,))
    products = cursor.fetchall()
    cursor.close()
    return products

# Function to fetch products based on category name
def fetch_products_by_category(category_name):
    conn = Database.get_connection()
    cursor = conn.cursor()
    query = "SELECT id, item_name, billing_from_name, item_selling_price, quantity FROM items WHERE category_name = %s"
    cursor.execute(query, (category_name,))
    products = cursor.fetchall()
    cursor.close()
    return products

# Function to generate invoice data
def generate_invoice_data(selected_products):
    invoice_data = []
    total_amount = 0
    for product in selected_products:
        # Ensure keys match the column names fetched from the database
        amount = product['item_selling_price'] * product['quantity']
        total_amount += amount
        invoice_data.append({
            'Product Name': product['item_name'],
            'Category': product['category_name'],
            'Price': product['item_selling_price'],
            'Quantity': product['quantity'],
            'Amount': amount
        })
    return invoice_data, total_amount

# Streamlit UI
st.title('Generate Invoice')

# Option to choose filter by agency or category
filter_option = st.radio('Filter By:', ('Agency Name', 'Category'))

if filter_option == 'Agency Name':
    agencies = fetch_existing_agencies()
    agency_name_input = st.selectbox('Select Agency:', agencies)
    if agency_name_input:
        products = fetch_products_by_agency(agency_name_input)
else:
    categories = fetch_categories()
    category_name_input = st.selectbox('Select Category:', categories)
    if category_name_input:
        products = fetch_products_by_category(category_name_input)

# Display products in a DataFrame and allow selection
if products:
    df_products = pd.DataFrame(products, columns=['ID', 'Product Name', 'Category Name', 'Price', 'Available Quantity'])
    
    # Adding a multi-select box for products
    selected_product_ids = st.multiselect('Select Products:', df_products['ID'], format_func=lambda x: f"{df_products.loc[df_products['ID'] == x, 'Product Name'].values[0]} ({df_products.loc[df_products['ID'] == x, 'Category Name'].values[0]})")
    
    selected_products = df_products[df_products['ID'].isin(selected_product_ids)].to_dict('records')
    
    if selected_products:
        st.subheader('Selected Products:')
        st.write(pd.DataFrame(selected_products))
        
        # Button to generate invoice
        if st.button('Generate Invoice'):
            invoice_data, total_amount = generate_invoice_data(selected_products)
            st.session_state['invoice_data'] = invoice_data
            st.session_state['total_amount'] = total_amount
            st.success('Invoice generated successfully!')
            st.write(f"Total Amount: {total_amount}")
            st.write('Click the "Download Invoice" button to get the invoice PDF.')

            # Button to download invoice as PDF
            if st.button('Download Invoice'):
                invoice_pdf = generate_invoice_pdf(invoice_data, total_amount)
                st.download_button(
                    label="Download Invoice",
                    data=invoice_pdf,
                    file_name='invoice.pdf',
                    mime='application/pdf'
                )
else:
    st.warning('No products found for the selected criteria.')






# def test_generate_invoice():
    # Dummy data for testing
   