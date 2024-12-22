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
import base64
from utils.db_manager import get_db_connection
import time

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
    data = [['Item Name', 'Item Code', 'Qty', 'Price', 'Total']]
    for item in invoice_items.to_dict('records'):
        data.append([
            item['item_name'],
            item['item_code'],
            item['quantity'],
            f"{item['price']:.2f}",
            f"{item['total_amount']:.2f}"
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
    elements.append(Paragraph(f"Subtotal: {total_amount:.2f}", summary_style))
    elements.append(Paragraph(f"GST Rate: {gst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"IGST Rate: {igst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"Total Tax Rate: {gst_rate + igst_rate:.2f}%", summary_style))
    elements.append(Paragraph(f"GST Amount: {total_amount * (gst_rate / 100):.2f}", summary_style))
    elements.append(Paragraph(f"IGST Amount: {total_amount * (igst_rate / 100):.2f}", summary_style))
    elements.append(Paragraph(f"Total Tax Amount: {total_amount * ((gst_rate + igst_rate) / 100):.2f}", summary_style))
    elements.append(Paragraph(f"Final Amount: {final_amount:.2f}", summary_style))

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

def get_customer_history():
    """Fetch unique customer details from previous invoices"""
    try:
        conn = sqlite3.connect('inventory.db')
        df = pd.read_sql_query("""
            SELECT DISTINCT 
                customer_name,
                customer_address,
                customer_phone,
                COUNT(*) as order_count,
                MAX(date) as last_order_date
            FROM invoices 
            GROUP BY customer_name, customer_address, customer_phone
            ORDER BY last_order_date DESC
        """, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching customer history: {e}")
        return pd.DataFrame()

def customer_details_section():
    """Customer details section with history support"""
    with st.container():
        st.subheader("Customer Details")
        
        # Get customer history
        customer_history = get_customer_history()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not customer_history.empty:
                # Create a selectbox with previous customers
                selected_customer = st.selectbox(
                    "Select Previous Customer",
                    ["New Customer"] + customer_history['customer_name'].tolist(),
                    help="Select from previous customers or choose 'New Customer' to enter new details"
                )
                
                if selected_customer != "New Customer":
                    # Auto-fill customer details
                    customer_data = customer_history[
                        customer_history['customer_name'] == selected_customer
                    ].iloc[0]
                    
                    st.info(f"""
                        Last Order: {customer_data['last_order_date']}
                        Total Orders: {customer_data['order_count']}
                    """)
                    
                    customer_name = st.text_input("Customer Name", value=customer_data['customer_name'])
                    customer_address = st.text_area("Address", value=customer_data['customer_address'])
                    customer_phone = st.text_input("Phone", value=customer_data['customer_phone'])
                else:
                    customer_name = st.text_input("Customer Name")
                    customer_address = st.text_area("Address")
                    customer_phone = st.text_input("Phone")
            else:
                customer_name = st.text_input("Customer Name")
                customer_address = st.text_area("Address")
                customer_phone = st.text_input("Phone")
        
        with col2:
            invoice_date = st.date_input("Invoice Date", datetime.now())
        
        return {
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_phone": customer_phone,
            "invoice_date": invoice_date
        }

def filter_products(df, filters):
    filtered_df = df.copy()
    
    if filters.get('company'):
        filtered_df = filtered_df[filtered_df['company'].str.contains(filters['company'], case=False, na=False)]
    
    if filters.get('category'):
        filtered_df = filtered_df[filtered_df['category'].str.contains(filters['category'], case=False, na=False)]
    
    if filters.get('item_name'):
        filtered_df = filtered_df[filtered_df['item_name'].str.contains(filters['item_name'], case=False, na=False)]
    
    return filtered_df

def invoice_generation():
    st.title("Generate Invoice")
    
    # Get customer details with history support
    customer_details = customer_details_section()
    
    # Create tabs for item selection and invoice preview
    tab1, tab2 = st.tabs(["Select Items", "Preview Invoice"])
    
    # Initialize session state for invoice items if not exists
    if 'invoice_items' not in st.session_state:
        st.session_state.invoice_items = pd.DataFrame(
            columns=['item_name', 'item_code', 'quantity', 'price', 
                    'discount_percentage', 'discount_amount',
                    'gst_percentage', 'gst_amount', 'total_amount']
        )
    
    with tab1:
        # Load available products
        with get_db_connection() as conn:
            products_df = pd.read_sql_query("SELECT * FROM products", conn)
        
        # Add filters
        st.subheader("Filter Products")
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        filters = {}
        with filter_col1:
            filters['company'] = st.text_input("Company Contains")
        with filter_col2:
            filters['category'] = st.text_input("Category Contains")
        with filter_col3:
            filters['item_name'] = st.text_input("Item Name Contains")
        
        # Apply filters
        filtered_df = filter_products(products_df, filters)
        
        # Item selection
        selected_item = st.selectbox(
            "Select Item",
            filtered_df['item_name'].tolist(),
            key="item_select"
        )
        
        # Get and display item details
        if selected_item:
            item_details = filtered_df[filtered_df['item_name'] == selected_item].iloc[0]
            
            # Display current item details
            st.write("Current Item Details:")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Available Quantity: {item_details['quantity']}")
                st.write(f"Current Price: ₹{item_details['selling_price']:.2f}")
            with col2:
                st.write(f"Item Code: {item_details['item_code']}")
                st.write(f"Category: {item_details['category']}")
            
            st.divider()
            
            # Add item form
            with st.form("add_item_form"):
                form_col1, form_col2 = st.columns(2)
                
                with form_col1:
                    quantity = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=int(item_details['quantity']),
                        value=1
                    )
                    
                    new_price = st.number_input(
                        "Selling Price",
                        min_value=0.1,
                        value=float(item_details['selling_price']),
                        step=0.01
                    )
                    
                    gst_percentage = st.number_input(
                        "GST %",
                        min_value=0.0,
                        max_value=100.0,
                        value=12.0,
                        step=0.1
                    )
                    
                    discount_percentage = st.number_input(
                        "Discount %",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.0,
                        step=0.1
                    )
                
                with form_col2:
                    # Calculate and show totals
                    subtotal = quantity * new_price
                    discount_amount = subtotal * (discount_percentage / 100)
                    amount_after_discount = subtotal - discount_amount
                    gst_amount = amount_after_discount * (gst_percentage / 100)
                    final_amount = amount_after_discount + gst_amount
                    
                    st.write("Order Summary:")
                    st.write(f"Subtotal: ₹{subtotal:.2f}")
                    if discount_percentage > 0:
                        st.write(f"Discount ({discount_percentage}%): -₹{discount_amount:.2f}")
                        st.write(f"After Discount: ₹{amount_after_discount:.2f}")
                    st.write(f"GST ({gst_percentage}%): ₹{gst_amount:.2f}")
                    st.write(f"Final Amount: ₹{final_amount:.2f}")
                
                submitted = st.form_submit_button("Add to Invoice")
                
                if submitted:
                    # Add item to invoice
                    new_item = pd.DataFrame([{
                        'item_name': selected_item,
                        'item_code': item_details['item_code'],
                        'quantity': quantity,
                        'price': new_price,
                        'discount_percentage': discount_percentage,
                        'discount_amount': discount_amount,
                        'gst_percentage': gst_percentage,
                        'gst_amount': gst_amount,
                        'total_amount': final_amount
                    }])
                    
                    st.session_state.invoice_items = pd.concat(
                        [st.session_state.invoice_items, new_item],
                        ignore_index=True
                    )
                    st.success(f"Added {quantity} {selected_item} to invoice")
                    time.sleep(0.5)
                    st.rerun()

        # Display current invoice items
        if not st.session_state.invoice_items.empty:
            st.subheader("Current Invoice Items")
            
            edited_df = st.data_editor(
                st.session_state.invoice_items,
                column_config={
                    "item_name": st.column_config.TextColumn("Item Name", disabled=True),
                    "item_code": st.column_config.TextColumn("Item Code", disabled=True),
                    "quantity": st.column_config.NumberColumn("Quantity", min_value=1),
                    "price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                    "discount_percentage": st.column_config.NumberColumn("Discount %", format="%.1f%%"),
                    "discount_amount": st.column_config.NumberColumn("Discount", format="₹%.2f", disabled=True),
                    "gst_percentage": st.column_config.NumberColumn("GST %", format="%.1f%%"),
                    "gst_amount": st.column_config.NumberColumn("GST Amount", format="₹%.2f", disabled=True),
                    "total_amount": st.column_config.NumberColumn("Total", disabled=True, format="₹%.2f")
                },
                hide_index=True,
            )
            
            # Add Save Changes button
            if st.button("Save Changes", type="primary"):
                try:
                    # Update calculations
                    if not edited_df.empty:
                        edited_df['discount_amount'] = edited_df['price'] * edited_df['quantity'] * edited_df['discount_percentage'] / 100
                        edited_df['gst_amount'] = (edited_df['price'] * edited_df['quantity'] - edited_df['discount_amount']) * edited_df['gst_percentage'] / 100
                        edited_df['total_amount'] = (
                            edited_df['price'] * edited_df['quantity'] * 
                            (1 - edited_df['discount_percentage']/100) * 
                            (1 + edited_df['gst_percentage']/100)
                        )
                        st.session_state.invoice_items = edited_df
                        st.success("Changes saved successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error saving changes: {e}")
            
            # Calculate totals
            subtotal = edited_df['total_amount'].sum()
            total_gst = edited_df['gst_amount'].sum()
            final_amount = subtotal
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Subtotal", f"₹{subtotal:.2f}")
            with col2:
                st.metric("GST Amount", f"₹{total_gst:.2f}")
            with col3:
                st.metric("Final Amount", f"₹{final_amount:.2f}")
    
    with tab2:
        if st.session_state.invoice_items.empty:
            st.info("Add items to the invoice to see preview")
        else:
            # Generate invoice preview
            with get_db_connection() as conn:
                invoice_number = get_next_invoice_number(conn)
            
            seller_details = {
                'name': customer_details['customer_name'],
                'address': customer_details['customer_address'],
                'phone': customer_details['customer_phone'],
                'gstin': 'N/A'
            }
            
            # Calculate GST
            total_amount = st.session_state.invoice_items['total_amount'].sum()
            total_gst = (st.session_state.invoice_items['total_amount'] * 
                        st.session_state.invoice_items['gst_percentage'] / 100).sum()
            final_amount = total_amount + total_gst
            
            # Generate PDF preview
            pdf_buffer = generate_pdf(
                st.session_state.invoice_items,
                total_amount,
                total_gst,
                0,  # IGST rate
                final_amount,
                seller_details,
                invoice_number,
                preview=True
            )
            
            # Display PDF preview
            pdf_bytes = pdf_buffer.getvalue()
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate and Save Invoice", type="primary"):
                    try:
                        if not customer_details['customer_name'] or not customer_details['customer_address']:
                            st.error("Please fill in customer details")
                            return
                            
                        with get_db_connection() as conn:
                            # Save invoice to database
                            conn.execute("""
                                INSERT INTO invoices (
                                    invoice_data, total_amount, date, customer_name,
                                    customer_address, customer_phone, invoice_number
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                st.session_state.invoice_items.to_json(),
                                final_amount,
                                datetime.now().strftime('%Y-%m-%d'),
                                customer_details['customer_name'],
                                customer_details['customer_address'],
                                customer_details['customer_phone'],
                                invoice_number
                            ))
                            
                            # Update product quantities
                            for _, item in st.session_state.invoice_items.iterrows():
                                conn.execute("""
                                    UPDATE products 
                                    SET quantity = quantity - ? 
                                    WHERE item_name = ? AND item_code = ?
                                """, (
                                    item['quantity'],
                                    item['item_name'],
                                    item['item_code']
                                ))
                            
                            conn.commit()
                            
                            # Clear the invoice items
                            st.session_state.invoice_items = pd.DataFrame(
                                columns=['item_name', 'item_code', 'quantity', 'price', 
                                        'discount_percentage', 'discount_amount',
                                        'gst_percentage', 'gst_amount', 'total_amount']
                            )
                            
                            st.success("Invoice generated and saved successfully!")
                            time.sleep(1)  # Give time for the success message to be seen
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error saving invoice: {e}")
            
            with col2:
                if st.button("Clear Invoice"):
                    st.session_state.invoice_items = pd.DataFrame(
                        columns=['item_name', 'item_code', 'quantity', 'price', 
                                'discount_percentage', 'discount_amount',
                                'gst_percentage', 'gst_amount', 'total_amount']
                    )
                    st.rerun()

if __name__ == "__main__":
    invoice_generation()