import streamlit as st
import pandas as pd
import sqlite3
import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A5
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pages.product_management import product_form
import base64

def generate_pdf(invoice_items, total_amount, gst_rate, igst_rate, final_amount, seller_details, invoice_number, preview=False):
    buffer = io.BytesIO()
    
    # Determine the page size based on the number of items
    if len(invoice_items) <= 5:
        page_size = A5
        doc = SimpleDocTemplate(buffer, pagesize=page_size, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        font_size = 8
    else:
        page_size = letter
        doc = SimpleDocTemplate(buffer, pagesize=page_size)
        font_size = 10

    elements = []

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Left', alignment=0))
    styles.add(ParagraphStyle(name='Right', alignment=2))

    # Add company details (top left)
    company_details = [
        Paragraph("Gananath Enterprises", styles['Left']),
        Paragraph("New Colony, Rayagada,", styles['Left']),
        Paragraph("Odisha, 765001", styles['Left']),
        Paragraph("GSTIN: XXX1933884", styles['Left'])
    ]

    # Add seller details (top right)
    seller_details = [
        Paragraph(f"Customer: {seller_details['name']}", styles['Right']),
        Paragraph(f"{seller_details['address']}", styles['Right']),
        Paragraph(f"Phone: {seller_details['phone']}", styles['Right']),
        Paragraph(f"GSTIN: {seller_details['gstin']}", styles['Right'])
    ]

    # Add date and time
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_time = Paragraph(f"Date: {current_datetime}", styles['Right'])

    # Add invoice number
    invoice_num = Paragraph(f"Invoice Number: {invoice_number}", styles['Left'])

    # Create a table for the header
    header_data = [[company_details, seller_details]]
    header_table = Table(header_data, colWidths=[doc.width/2.0]*2)
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(header_table)
    elements.append(date_time)
    elements.append(invoice_num)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Invoice", styles['Title']))
    elements.append(Spacer(1, 12))

    # Add invoice items table
    data = [['Item Name', 'Item Code', 'Qty', 'Box', 'Price', 'Total']]
    for item in invoice_items.to_dict('records'):
        data.append([
            item['item_name'],
            item['item_code'],
            item['quantity'],
            item['box'],
            f"₹{item['price']:.2f}",
            f"₹{item['total_amount']:.2f}"
        ])
    
    # Adjust column widths to give more space for Item Name
    col_widths = [doc.width*0.35, doc.width*0.15, doc.width*0.1, doc.width*0.1, doc.width*0.15, doc.width*0.15]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Add summary
    summary_style = ParagraphStyle('summary', fontSize=font_size, alignment=2)  # Right-aligned
    elements.append(Paragraph(f"Subtotal: ₹{total_amount:.2f}", summary_style))
    elements.append(Paragraph(f"GST Rate: {gst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"IGST Rate: {igst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"Total Tax Rate: {gst_rate + igst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"GST Amount: ₹{total_amount * (gst_rate / 100):.2f}", summary_style))
    elements.append(Paragraph(f"IGST Amount: ₹{total_amount * (igst_rate / 100):.2f}", summary_style))
    elements.append(Paragraph(f"Total Tax Amount: ₹{total_amount * ((gst_rate + igst_rate) / 100):.2f}", summary_style))
    elements.append(Paragraph(f"Final Amount: ₹{final_amount:.2f}", summary_style))

    doc.build(elements)
    
    if preview:
        return buffer
    else:
        return buffer.getvalue()

def get_next_invoice_number(conn):
    c = conn.cursor()
    
    # Get the total number of rows in the invoices table
    c.execute("SELECT COUNT(*) FROM invoices")
    total_invoices = c.fetchone()[0]
    
    # The next invoice number is the total number of invoices plus one
    next_number = total_invoices + 1
    
    # Format the invoice number (e.g., INV-0001)
    return f"INV-{next_number:04d}"

def invoice_generation():
    conn = sqlite3.connect('inventory.db')
    
    # Fetch all products
    df_products = pd.read_sql_query("SELECT * FROM products", conn)
    
    product_options = df_products.apply(lambda row: f"{row['item_name']} and {row['company']} ({row['category']})", axis=1).tolist()
    
    st.subheader("Seller Details")
    
    # Create two columns for input
    col1, col2 = st.columns(2)

    with col1:
        seller_name = st.text_input("Seller Name")
        seller_address = st.text_area("Seller Address")

    with col2:
        seller_phone = st.text_input("Seller Phone", value="NA")
        seller_gstin = st.text_input("Seller GSTIN", value="NA")

    # Generate and display the next invoice number
    next_invoice_number = get_next_invoice_number(conn)
    st.text_input("Invoice Number", value=next_invoice_number, disabled=True)

    # Product selection
    selected_product = st.selectbox("Select a product", product_options + ["Add new product"])
    
    # Initialize session state for invoice items if it doesn't exist
    if 'invoice_items' not in st.session_state:
        st.session_state.invoice_items = pd.DataFrame(columns=['display_name', 'item_name', 'item_code', 'quantity', 'box', 'price', 'total_amount'])
    
    # Add new product
    if selected_product == "Add new product":
        st.subheader("Add New Product")
        product_added = product_form(conn)
        if product_added:
            st.experimental_rerun()
    
    # Add selected product to invoice items
    if st.button("Add to Invoice"):
        selected_index = product_options.index(selected_product)
        product_data = df_products.iloc[selected_index]
        display_name = f"{product_data['company']}_{product_data['item_name']}"
        new_item = pd.DataFrame({
            'display_name': [display_name],
            'item_name': [product_data['item_name']],
            'item_code': [product_data['item_code']],
            'quantity': [1],
            'box': [product_data['unit_per_box']],
            'price': [product_data['selling_price']],
            'total_amount': [product_data['selling_price']]
        })
        
        st.session_state.invoice_items = pd.concat([st.session_state.invoice_items, new_item], ignore_index=True)
    
    # Display and edit invoice items
    if not st.session_state.invoice_items.empty:
        st.subheader("Invoice Items")
        edited_df = st.data_editor(
            st.session_state.invoice_items,
            num_rows="dynamic",
            column_config={
                "display_name": st.column_config.TextColumn("Item Name"),
                "item_code": st.column_config.TextColumn("Item Code"),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
                "box": st.column_config.NumberColumn("Box", min_value=0, step=1),
                "price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "total_amount": st.column_config.NumberColumn("Total Amount", format="₹%.2f")
            },
            hide_index=True,
            key="invoice_items_editor"
        )
        
        # Update total amounts based on quantity, box, and price
        edited_df['total_amount'] = edited_df.apply(lambda row: 
            row['price'] * row['quantity'] if row['box'] == 0 or pd.isna(row['box']) 
            else row['price'] * row['quantity'] * row['box'], axis=1)
        st.session_state.invoice_items = edited_df
    
    # Calculate total amount
    total_amount = st.session_state.invoice_items['total_amount'].sum()
    
    # Tax rate inputs
    col1, col2 = st.columns(2)
    with col1:
        gst_rate = st.number_input("GST Rate (%)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with col2:
        igst_rate = st.number_input("IGST Rate (%)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    
    # Calculate total tax rate and amount
    total_tax_rate = gst_rate + igst_rate
    tax_amount = total_amount * (total_tax_rate / 100)
    
    # Calculate final amount
    final_amount = total_amount + tax_amount
    
    # Display tax breakdown and final amount
    st.write(f"GST Amount: ₹{total_amount * (gst_rate / 100):.2f}")
    st.write(f"IGST Amount: ₹{total_amount * (igst_rate / 100):.2f}")
    st.write(f"Total Tax Amount: ₹{tax_amount:.2f}")
    st.write(f"Final Amount: ₹{final_amount:.2f}")

    # Seller details dictionary
    seller_details = {
        "name": seller_name,
        "address": seller_address,
        "phone": seller_phone,
        "gstin": seller_gstin
    }

    # Preview button
    if st.button("Preview Invoice"):
        pdf_invoice_items = st.session_state.invoice_items.copy()
        pdf_invoice_items['item_name'] = pdf_invoice_items['display_name']
        pdf_buffer = generate_pdf(pdf_invoice_items, total_amount, gst_rate, igst_rate, final_amount, seller_details, next_invoice_number, preview=True)
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    
    if st.button("Generate Invoice"):
        pdf_invoice_items = st.session_state.invoice_items.copy()
        pdf_invoice_items['item_name'] = pdf_invoice_items['display_name']
        
        # Generate PDF
        pdf_bytes = generate_pdf(pdf_invoice_items, total_amount, gst_rate, igst_rate, final_amount, seller_details, next_invoice_number)
        
        # Save PDF locally
        if not os.path.exists('invoices'):
            os.makedirs('invoices')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"invoice_{next_invoice_number}_{timestamp}.pdf"
        pdf_path = os.path.join('invoices', pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Store invoice in database
        invoice_data = st.session_state.invoice_items[['item_name', 'item_code', 'quantity', 'box', 'price', 'total_amount']].to_dict('records')
        with conn:
            conn.execute("""
                INSERT INTO invoices (invoice_data, total_amount, date, pdf_path, customer_name, customer_address, customer_phone, invoice_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(invoice_data), final_amount, str(pd.Timestamp.now()), pdf_path, seller_name, seller_address, seller_phone, next_invoice_number))
        
        # Display success message and provide download link
        st.success(f"Invoice {next_invoice_number} generated and stored in database! PDF saved as {pdf_filename}")
        
        # Create a download button for the PDF
        st.download_button(
            label="Download Invoice PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf"
        )
    
    # Close the database connection
    conn.close()