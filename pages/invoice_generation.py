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
from utils.db_manager import get_db_connection, ensure_company_details_exist
import time
import logging
from num2words import num2words

logger = logging.getLogger(__name__)

def generate_pdf(invoice_items, total_amount, gst_rate, igst_rate, final_amount, seller_details, invoice_number, preview=False):
    buffer = io.BytesIO()
    
    # Ensure database is initialized
    if not ensure_company_details_exist():
        raise Exception("Failed to initialize database. Please check the logs.")
    
    # Get company details
    with get_db_connection() as conn:
        company_df = pd.read_sql_query("SELECT * FROM company_details WHERE id = 1", conn)
        if company_df.empty:
            raise Exception("Company details not found!")
        company_details = company_df.iloc[0]
    
    # Use letter size for better layout
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=30,  # Increased margins
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
        showBoundary=1
    )

    elements = []
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name='CompanyHeader',
        parent=styles['Normal'],
        fontSize=11,  # Slightly reduced font size
        spaceAfter=2,
        leading=13,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='CompanyDetails',
        parent=styles['Normal'],
        fontSize=8,  # Reduced font size
        spaceAfter=1,
        leading=10
    ))
    
    # Create the title "TAX INVOICE" centered
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=6,
        spaceBefore=6,
        alignment=1
    )
    elements.append(Paragraph("TAX INVOICE", title_style))
    elements.append(Spacer(1, 5))
    
    # Create header table with seller and company info
    seller_info = [
        [Paragraph("Bill To:", styles['CompanyHeader'])],
        [Paragraph(f"M/S {seller_details['name']}", styles['CompanyDetails'])],
        [Paragraph(seller_details['address'], styles['CompanyDetails'])],
        [Paragraph(f"GSTIN/UIN: {seller_details['gstin']}", styles['CompanyDetails'])],
        [Paragraph(f"Contact: {seller_details['phone']}", styles['CompanyDetails'])],
        [Paragraph(f"State Name: {company_details['state']}, Code: {company_details['state_code']}", styles['CompanyDetails'])]
    ]
    
    company_info = [
        [Paragraph(company_details['name'], styles['CompanyHeader'])],
        [Paragraph(company_details['address'], styles['CompanyDetails'])],
        [Paragraph(f"{company_details['city']}, {company_details['state']} - {company_details['state_code']}", styles['CompanyDetails'])],
        [Paragraph(f"GSTIN: {company_details['gstin']}", styles['CompanyDetails'])],
        [Paragraph(f"Phone: {company_details['phone']}", styles['CompanyDetails'])],
        [Paragraph(f"Email: {company_details['email']}", styles['CompanyDetails'])]
    ]
    
    # Calculate available width for tables
    available_width = 535  # Total width minus margins
    col_width = available_width / 2  # Equal width for two columns
    
    # Create a table for the header section
    header_data = [
        [Table(seller_info, colWidths=[col_width]), Table(company_info, colWidths=[col_width])],
        [
            Table([
                [Paragraph("Invoice Details:", styles['CompanyHeader'])],
                [Paragraph(f"Invoice No: {invoice_number}", styles['CompanyDetails'])],
                [Paragraph(f"Date: {datetime.now().strftime('%d-%b-%y')}", styles['CompanyDetails'])],
                [Paragraph(f"Mode/Terms of Payment: {seller_details['payment_status'].upper()}", styles['CompanyDetails'])]
            ], colWidths=[col_width]),
            Table([
                [Paragraph("Shipping Details:", styles['CompanyHeader'])],
                [Paragraph("Delivery Note: ", styles['CompanyDetails'])],
                [Paragraph("Dispatch Doc No: ", styles['CompanyDetails'])],
                [Paragraph("Dispatched through: ", styles['CompanyDetails'])]
            ], colWidths=[col_width])
        ]
    ]
    
    header_table = Table(header_data, colWidths=[col_width, col_width])
    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    
    # Create items table with borders (removed Part No. column)
    items_data = [
        ['Sl\nNo.', 'Description of Goods', 'HSN/SAC', 'GST\nRate', 'Quantity', 'Rate\n(incl. of Tax)', 'Rate', 'per', 'Disc. %', 'Amount']
    ]
    
    # Add items with rounded amounts
    for idx, item in enumerate(invoice_items.itertuples(), 1):
        items_data.append([
            str(idx),
            item.item_name,
            "84701000",  # Example HSN code
            f"{item.gst_percentage}%",
            str(item.quantity),
            f"{item.price:.0f}",
            f"{(item.price/(1 + item.gst_percentage/100)):.0f}",
            "Nos",
            f"{item.discount_percentage}%",
            f"{item.total_amount:.0f}"
        ])
    
    # Add totals row with rounded amount
    total_qty = invoice_items['quantity'].sum()
    items_data.append(['', 'Total', '', '', str(total_qty), '', '', '', '', f"{total_amount:.0f}"])
    
    # Adjust items table column widths to fit within available width
    col_widths = [25, 175, 45, 35, 45, 55, 55, 30, 35, 35]  # Total should equal available_width
    
    items_table = Table(items_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Description column left aligned
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(items_table)
    
    # Add spacer to push bottom section to the end
    elements.append(Spacer(1, 50))
    
    # Update bottom section widths
    bottom_data = [
        [
            # Left side - Bank Details
            Table([
                [Paragraph("Company's Bank Details", styles['CompanyHeader'])],
                [Paragraph(f"Bank Name: {company_details['bank_name']}", styles['CompanyDetails'])],
                [Paragraph(f"A/c No.: {company_details['bank_account']}", styles['CompanyDetails'])],
                [Paragraph(f"Branch: {company_details['bank_branch']}", styles['CompanyDetails'])],
                [Paragraph(f"IFSC Code: {company_details['bank_ifsc']}", styles['CompanyDetails'])]
            ], colWidths=[col_width]),
            
            # Right side - Amount Details
            Table([
                [Paragraph("Amount Details", styles['CompanyHeader'])],
                [Paragraph(f"Subtotal: INR {total_amount:.0f}", styles['CompanyDetails'])],
                [Paragraph(f"GST ({gst_rate}%): INR {total_amount * (gst_rate/100):.0f}", styles['CompanyDetails'])],
                [Paragraph(f"Total Amount: INR {final_amount:.0f}", styles['CompanyDetails'])],
                [Paragraph(f"Amount in Words: {num2words(int(final_amount)).title()} Only", 
                          ParagraphStyle('AmountWords', parent=styles['CompanyDetails'], fontSize=8, leading=10))]
            ], colWidths=[col_width])
        ]
    ]
    
    bottom_table = Table(bottom_data, colWidths=[col_width, col_width])
    bottom_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(bottom_table)
    
    # Update footer width
    footer_data = [
        [Paragraph("Declaration: We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.", 
                  ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, alignment=0, leading=8))],
        [Paragraph(f"SUBJECT TO {company_details['jurisdiction']} JURISDICTION | This is a Computer Generated Invoice", 
                  ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, alignment=1, leading=8))]
    ]
    
    footer_table = Table(footer_data, colWidths=[available_width])
    footer_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(footer_table)

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
    
    # Format the invoice number (e.g., INV0001)
    return f"INV{next_number:04d}"

def get_seller_history():
    """Fetch unique seller details from previous invoices"""
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query("""
                SELECT s.*, 
                       COUNT(DISTINCT i.id) as order_count,
                       MAX(i.date) as last_order_date,
                       s.total_credit as current_credit
                FROM sellers s
                LEFT JOIN invoices i ON s.id = i.seller_id
                GROUP BY s.id
                ORDER BY last_order_date DESC
            """, conn)
            return df
    except Exception as e:
        st.error(f"Error fetching seller history: {e}")
        return pd.DataFrame()

def seller_details_section():
    """Seller details section with history support"""
    with st.container():
        st.subheader("Seller Details")
        
        # Get seller history
        seller_history = get_seller_history()
        
        # Clear seller_id from session state if "New Seller" is selected
        if 'current_seller_id' in st.session_state and st.session_state.get('new_seller_selected', False):
            del st.session_state.current_seller_id
            st.session_state.new_seller_selected = False
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not seller_history.empty:
                # Create a selectbox with previous sellers
                selected_seller = st.selectbox(
                    "Select Seller",
                    ["Select a Seller", "New Seller"] + seller_history['name'].tolist(),
                    help="Select from existing sellers or choose 'New Seller' to enter new details"
                )
                
                if selected_seller == "Select a Seller":
                    st.warning("Please select a seller or create a new one")
                    if 'current_seller_id' in st.session_state:
                        del st.session_state.current_seller_id
                    return {
                        "name": "",
                        "address": "",
                        "phone": "",
                        "gstin": "",
                        "invoice_date": datetime.now(),
                        "payment_status": "paid"
                    }
                elif selected_seller == "New Seller":
                    st.session_state.new_seller_selected = True
                    if 'current_seller_id' in st.session_state:
                        del st.session_state.current_seller_id
                    # New seller form
                    seller_name = st.text_input("Seller Name")
                    seller_address = st.text_area("Address")
                    seller_phone = st.text_input("Phone")
                    seller_gstin = st.text_input("GSTIN")
                else:
                    # Auto-fill seller details
                    seller_data = seller_history[
                        seller_history['name'] == selected_seller
                    ].iloc[0]
                    
                    st.info(f"""
                        Last Order: {seller_data['last_order_date']}
                        Total Orders: {seller_data['order_count']}
                        Current Credit: ₹{seller_data['current_credit']:.2f}
                    """)
                    
                    # Store seller_id in session state
                    st.session_state.current_seller_id = int(seller_data['id'])
                    logger.info(f"Set current_seller_id in session: {st.session_state.current_seller_id}")
                    
                    # Display seller details in read-only format
                    st.write("**Seller Name:**", seller_data['name'])
                    st.write("**Address:**", seller_data['address'])
                    st.write("**Phone:**", seller_data['phone'])
                    st.write("**GSTIN:**", seller_data['gstin'])
                    
                    # Store seller details in return value
                    seller_name = seller_data['name']
                    seller_address = seller_data['address']
                    seller_phone = seller_data['phone']
                    seller_gstin = seller_data['gstin']
            else:
                # New seller form when no history
                seller_name = st.text_input("Seller Name")
                seller_address = st.text_area("Address")
                seller_phone = st.text_input("Phone")
                seller_gstin = st.text_input("GSTIN")
        
        with col2:
            invoice_date = st.date_input("Invoice Date", datetime.now())
            payment_status = st.selectbox(
                "Payment Status",
                ["paid", "credit"],
                help="Select 'credit' if this is a credit sale"
            )
        
        return {
            "name": seller_name if 'seller_name' in locals() else "",
            "address": seller_address if 'seller_address' in locals() else "",
            "phone": seller_phone if 'seller_phone' in locals() else "",
            "gstin": seller_gstin if 'seller_gstin' in locals() else "",
            "invoice_date": invoice_date,
            "payment_status": payment_status
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
    
    # Ensure database is initialized
    if not ensure_company_details_exist():
        st.error("❌ Failed to initialize database. Please check the logs.")
        return
    
    # Get seller details with history support
    seller_details = seller_details_section()
    
    # Create tabs for item selection and invoice preview with icons
    tab1, tab2 = st.tabs(["🛍️ Select Items", "📋 Preview Invoice"])
    
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
            products_df = pd.read_sql_query("SELECT * FROM products WHERE quantity > 0", conn)
        
        if products_df.empty:
            st.warning("⚠️ No products available in inventory. Please add products first.")
            return
        
        # Add filters with better styling
        st.subheader("🔍 Filter Products")
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        filters = {}
        with filter_col1:
            filters['company'] = st.text_input("🏢 Company Contains", placeholder="Search by company...")
        with filter_col2:
            filters['category'] = st.text_input("📁 Category Contains", placeholder="Search by category...")
        with filter_col3:
            filters['item_name'] = st.text_input("📦 Item Name Contains", placeholder="Search by item name...")
        
        # Apply filters
        filtered_df = filter_products(products_df, filters)
        
        if filtered_df.empty:
            st.info("ℹ️ No products match your search criteria.")
            return
        
        # Item selection with better styling
        st.subheader("📝 Select Item")
        selected_item = st.selectbox(
            "Choose an item to add",
            filtered_df['item_name'].tolist(),
            key="item_select",
            help="Select an item from the available products"
        )
        
        # Get and display item details
        if selected_item:
            item_details = filtered_df[filtered_df['item_name'] == selected_item].iloc[0]
            
            # Display current item details in a card-like container
            st.markdown("### 📊 Item Details")
            details_container = st.container()
            with details_container:
                st.markdown("""
                    <style>
                        .item-details {
                            background-color: #f0f2f6;
                            padding: 1rem;
                            border-radius: 0.5rem;
                            margin: 1rem 0;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Category", item_details['category'])
            
            with col2:
                st.metric("Current Price", f"₹{item_details['selling_price']:.2f}")
            
            with col3:
                st.metric("Available Quantity", f"{item_details['quantity']}")
            
            st.divider()
            
            # Add item form with improved styling
            with st.form("add_item_form", clear_on_submit=True):
                form_col1, form_col2 = st.columns(2)
                
                with form_col1:
                    quantity = st.number_input(
                        "📦 Quantity",
                        min_value=1,
                        max_value=int(item_details['quantity']),
                        value=1,
                        step=1,
                        help=f"Maximum available: {item_details['quantity']}"
                    )
                    
                    new_price = st.number_input(
                        "💰 Selling Price",
                        min_value=0.1,
                        value=float(item_details['selling_price']),
                        step=0.01,
                        help="Enter the selling price for this item"
                    )
                    
                with form_col2:
                    gst_percentage = st.number_input(
                        "📊 GST %",
                        min_value=0.0,
                        max_value=100.0,
                        value=12.0,
                        step=0.1,
                        help="Enter GST percentage"
                    )
                    
                    discount_percentage = st.number_input(
                        "🏷️ Discount %",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.0,
                        step=0.1,
                        help="Enter discount percentage if applicable"
                    )
                
                # Calculate and show totals with better formatting
                subtotal = quantity * new_price
                discount_amount = subtotal * (discount_percentage / 100)
                amount_after_discount = subtotal - discount_amount
                gst_amount = amount_after_discount * (gst_percentage / 100)
                final_amount = amount_after_discount + gst_amount
                
                st.markdown("### 💳 Order Summary")
                summary_col1, summary_col2 = st.columns(2)
                with summary_col1:
                    st.write(f"**Subtotal:** ₹{subtotal:.2f}")
                if discount_percentage > 0:
                        st.write(f"**Discount ({discount_percentage}%):** -₹{discount_amount:.2f}")
                        st.write(f"**After Discount:** ₹{amount_after_discount:.2f}")
                with summary_col2:
                    st.write(f"**GST ({gst_percentage}%):** ₹{gst_amount:.2f}")
                    st.write(f"**Final Amount:** ₹{final_amount:.2f}")
                
                # Add form submit button with better styling
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    submitted = st.form_submit_button(
                        "➕ Add to Invoice",
                        use_container_width=True,
                        type="primary"
                    )
                
                if submitted:
                    # Validate quantity again
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT quantity FROM products
                            WHERE item_name = ? AND item_code = ?
                        """, (selected_item, item_details['item_code']))
                        current_qty = cursor.fetchone()[0]
                        
                        if current_qty < quantity:
                            st.error(f"""
                                Cannot add item: Insufficient quantity for {selected_item}
                                Available: {current_qty}
                                Requested: {quantity}
                                
                                Please go to Manage Items to update the quantity.
                            """)
                            return
                        
                        # Check total quantity in current invoice
                        if not st.session_state.invoice_items.empty:
                            existing_qty = st.session_state.invoice_items[
                                st.session_state.invoice_items['item_name'] == selected_item
                            ]['quantity'].sum()
                            
                            if existing_qty + quantity > current_qty:
                                st.error(f"""
                                    Cannot add item: Total quantity would exceed available stock
                                    Available: {current_qty}
                                    Already in invoice: {existing_qty}
                                    Additional requested: {quantity}
                                    Total needed: {existing_qty + quantity}
                                    
                                    Please adjust quantities or update stock in Manage Items.
                                """)
                                return
                    
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
            
            # Make the dataframe editable
            edited_df = st.data_editor(
                st.session_state.invoice_items,
                column_config={
                    "item_name": st.column_config.TextColumn("Item Name"),
                    "item_code": st.column_config.TextColumn("Item Code"),
                    "quantity": st.column_config.NumberColumn("Quantity", min_value=1),
                    "price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                    "discount_percentage": st.column_config.NumberColumn("Discount %", format="%.1f%%"),
                    "discount_amount": st.column_config.NumberColumn("Discount", format="₹%.2f"),
                    "gst_percentage": st.column_config.NumberColumn("GST %", format="%.1f%%"),
                    "gst_amount": st.column_config.NumberColumn("GST Amount", format="₹%.2f"),
                    "total_amount": st.column_config.NumberColumn("Total", format="₹%.2f")
                },
                hide_index=True,
                num_rows="dynamic"
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
            
            seller_info = {
                'name': seller_details['name'],
                'address': seller_details['address'],
                'phone': seller_details['phone'],
                'gstin': seller_details['gstin'],
                'payment_status': seller_details['payment_status']
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
                seller_info,
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
                        # Validate seller details first
                        if not hasattr(st.session_state, 'current_seller_id') and (
                            not seller_details['name'] or 
                            seller_details['name'] == "Select a Seller" or 
                            seller_details['name'] == "New Seller"
                        ):
                            st.error("Please select an existing seller or create a new one")
                            return
                            
                        with get_db_connection() as conn:
                            # Get or create seller_id
                            if hasattr(st.session_state, 'current_seller_id'):
                                seller_id = st.session_state.current_seller_id
                                logger.info(f"Using existing seller_id from session: {seller_id}")
                            else:
                                # Validate new seller details
                                if not seller_details['name'] or not seller_details['address']:
                                    st.error("Please fill in all required seller details (Name and Address)")
                                    return
                                
                                # Check if seller already exists
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT id FROM sellers 
                                    WHERE name = ? AND phone = ?
                                ''', (seller_details['name'], seller_details['phone']))
                                existing_seller = cursor.fetchone()
                                
                                if existing_seller:
                                    seller_id = existing_seller[0]
                                    logger.info(f"Found existing seller: {seller_id}")
                                else:
                                    # Insert new seller
                                    cursor.execute('''
                                        INSERT INTO sellers (name, address, phone, gstin)
                                        VALUES (?, ?, ?, ?)
                                    ''', (
                                        seller_details['name'],
                                        seller_details['address'],
                                        seller_details['phone'],
                                        seller_details['gstin']
                                    ))
                                    conn.commit()  # Commit the seller creation
                                    seller_id = cursor.lastrowid
                                    logger.info(f"Created new seller with ID: {seller_id}")
                            
                            if not seller_id:
                                st.error("Failed to get or create seller ID")
                                return
                            
                            logger.info(f"Final seller_id before transaction: {seller_id}")
                            
                            # Save invoice to database with validated seller_id
                            cursor = conn.cursor()
                            
                            # Start transaction
                            try:
                                # Double check seller exists
                                cursor.execute("""
                                    SELECT id, name 
                                    FROM sellers 
                                    WHERE id = ?
                                """, (seller_id,))
                                seller_record = cursor.fetchone()
                                logger.info(f"Seller verification query result: {seller_record}")
                                
                                if not seller_record:
                                    # Try to debug the issue
                                    cursor.execute("SELECT * FROM sellers")
                                    all_sellers = cursor.fetchall()
                                    logger.error(f"All sellers in database: {all_sellers}")
                                    raise Exception(f"Seller ID {seller_id} not found in database")
                                
                                logger.info(f"Verified seller exists: ID={seller_id}, Name={seller_record[1]}")
                                
                                # Begin transaction after verification
                                conn.execute("BEGIN TRANSACTION")
                                
                                # Insert invoice with verified seller_id
                                cursor.execute('''
                                    INSERT INTO invoices (
                                        invoice_data, total_amount, date, seller_id,
                                        payment_status, invoice_number
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    st.session_state.invoice_items.to_json(),
                                    final_amount,
                                    datetime.now().strftime('%Y-%m-%d'),
                                    seller_id,
                                    seller_details['payment_status'],
                                    invoice_number
                                ))
                                invoice_id = cursor.lastrowid
                                logger.info(f"Created invoice: ID={invoice_id}, Number={invoice_number}")
                                
                                # If credit sale, add to seller_transactions
                                if seller_details['payment_status'] == 'credit':
                                    cursor.execute('''
                                        INSERT INTO seller_transactions 
                                        (seller_id, invoice_id, amount, transaction_type, date, notes)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (
                                        seller_id,
                                        invoice_id,
                                        final_amount,
                                        'credit',
                                        datetime.now().strftime('%Y-%m-%d'),
                                        f'Credit sale - Invoice #{invoice_number}'
                                    ))
                                    
                                    # Update seller's total credit
                                    cursor.execute('''
                                        UPDATE sellers 
                                        SET total_credit = total_credit + ?
                                        WHERE id = ?
                                    ''', (final_amount, seller_id))
                                    logger.info(f"Updated credit for seller {seller_id}: +₹{final_amount:.2f}")
                                
                                # Update product quantities
                                for _, item in st.session_state.invoice_items.iterrows():
                                    # Verify current quantity first
                                    cursor.execute("""
                                        SELECT quantity 
                                        FROM products 
                                        WHERE item_name = ? AND item_code = ?
                                    """, (item['item_name'], item['item_code']))
                                    current_qty = cursor.fetchone()
                                    if not current_qty or current_qty[0] < item['quantity']:
                                        raise Exception(f"Insufficient quantity for {item['item_name']}")
                                    
                                    # Update quantity
                                    cursor.execute("""
                                        UPDATE products 
                                        SET quantity = quantity - ? 
                                        WHERE item_name = ? AND item_code = ?
                                    """, (
                                        item['quantity'],
                                        item['item_name'],
                                        item['item_code']
                                    ))
                                    logger.info(f"Updated quantity for {item['item_name']}: -{item['quantity']}")
                                
                                # Commit all changes
                                conn.commit()
                                logger.info("Transaction committed successfully")
                                
                                # Clear the invoice items
                                st.session_state.invoice_items = pd.DataFrame(
                                    columns=['item_name', 'item_code', 'quantity', 'price', 
                                            'discount_percentage', 'discount_amount',
                                            'gst_percentage', 'gst_amount', 'total_amount']
                                )
                                
                                st.success("Invoice generated and saved successfully!")
                                time.sleep(1)
                                st.rerun()
                                
                            except Exception as e:
                                # Rollback on any error
                                try:
                                    conn.rollback()
                                except:
                                    pass
                                st.error(f"Error saving invoice: {str(e)}")
                                logger.error(f"Error saving invoice: {str(e)}")
                                return
                            
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