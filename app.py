import streamlit as st

# Define pages
create_page = st.Page("create_item.py", title="Create entry", icon=":material/add_circle:")
update_page = st.Page("update_item.py", title="Update entry", icon=":material/update:")
generate_page = st.Page("generate_invoice.py", title="Generate Invoice", icon=":material/description:")

pg = st.navigation([create_page, update_page,generate_page])
st.set_page_config(page_title="Data manager", page_icon=":material/edit:",layout='wide')

pg.run()
