import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db_manager import get_db_connection
from utils.logger import setup_logger
import json
import time

logger = setup_logger()

def add_seller(conn, name, address, phone, gstin):
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sellers (name, address, phone, gstin)
                VALUES (?, ?, ?, ?)
            ''', (name, address, phone, gstin))
            return True, "Seller added successfully!"
    except Exception as e:
        logger.error(f"Error adding seller: {e}")
        return False, f"Error: {str(e)}"

def update_seller(conn, seller_id, name, address, phone, gstin):
    try:
        with conn:
            conn.execute('''
                UPDATE sellers 
                SET name = ?, address = ?, phone = ?, gstin = ?
                WHERE id = ?
            ''', (name, address, phone, gstin, seller_id))
            return True, "Seller updated successfully!"
    except Exception as e:
        logger.error(f"Error updating seller: {e}")
        return False, f"Error: {str(e)}"

def add_transaction(conn, seller_id, amount, transaction_type, notes, invoice_id=None, payment_date=None):
    try:
        with conn:
            # Add transaction record
            conn.execute('''
                INSERT INTO seller_transactions 
                (seller_id, invoice_id, amount, transaction_type, date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (seller_id, invoice_id, amount, transaction_type, 
                 payment_date.strftime('%Y-%m-%d') if payment_date else datetime.now().strftime('%Y-%m-%d'),
                 notes))
            
            # Update seller's total credit
            if transaction_type == 'credit':
                conn.execute('''
                    UPDATE sellers 
                    SET total_credit = total_credit + ?
                    WHERE id = ?
                ''', (amount, seller_id))
            else:  # payment
                conn.execute('''
                    UPDATE sellers 
                    SET total_credit = total_credit - ?
                    WHERE id = ?
                ''', (amount, seller_id))
            
            return True, "Transaction recorded successfully!"
    except Exception as e:
        logger.error(f"Error recording transaction: {e}")
        return False, f"Error: {str(e)}"

def get_seller_history():
    """Fetch unique seller details from previous invoices"""
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query("""
                SELECT 
                    s.*,
                    COALESCE(SUM(CASE WHEN i.payment_status = 'credit' THEN i.total_amount ELSE 0 END), 0) as total_credit_amount,
                    COALESCE(SUM(CASE WHEN i.payment_status = 'paid' THEN i.total_amount ELSE 0 END), 0) as total_paid_amount,
                    COUNT(DISTINCT i.id) as total_invoices,
                    MAX(i.date) as last_order_date
                FROM sellers s
                LEFT JOIN invoices i ON s.id = i.seller_id
                GROUP BY s.id
                ORDER BY last_order_date DESC NULLS LAST, s.name ASC
            """, conn)
            
            logger.info(f"Found {len(df)} sellers in history")
            if not df.empty:
                logger.info(f"Sample seller data: {df.iloc[0].to_dict()}")
            return df
    except Exception as e:
        logger.error(f"Error fetching seller history: {e}")
        return pd.DataFrame()

def manage_sellers():
    st.title("Manage Sellers")
    
    # Create tabs for different operations with icons
    tab1, tab2, tab3 = st.tabs(["👤 Add/Edit Sellers", "📋 View Sellers", "💰 Manage Credits"])
    
    with tab1:
        st.subheader("Add/Edit Seller")
        
        # Get existing seller for editing if selected
        with get_db_connection() as conn:
            sellers_df = pd.read_sql_query("""
                SELECT s.* 
                FROM sellers s 
                ORDER BY s.name
            """, conn)
        
        edit_mode = st.toggle("✏️ Edit Existing Seller")
        
        if edit_mode and not sellers_df.empty:
            # Add phone number to distinguish duplicates
            selected_seller = st.selectbox(
                "Select Seller to Edit",
                sellers_df.itertuples(index=False),
                format_func=lambda x: f"{x.name} ({x.phone})",  # Show phone for clarity
                help="Choose a seller to edit their details"
            )
            seller_data = sellers_df[sellers_df['id'] == selected_seller.id].iloc[0]
            st.info("ℹ️ Editing existing seller details")
        else:
            seller_data = pd.Series({'name': '', 'address': '', 'phone': '', 'gstin': ''})
            if edit_mode:
                st.warning("⚠️ No existing sellers found. Please add a new seller.")
        
        with st.form("seller_form", clear_on_submit=not edit_mode):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "👤 Name*", 
                    value=seller_data['name'],
                    placeholder="Enter seller name",
                    help="Required field"
                )
                phone = st.text_input(
                    "📱 Phone", 
                    value=seller_data['phone'],
                    placeholder="Enter phone number"
                )
            
            with col2:
                address = st.text_area(
                    "📍 Address*", 
                    value=seller_data['address'],
                    placeholder="Enter complete address",
                    help="Required field"
                )
                gstin = st.text_input(
                    "🏢 GSTIN", 
                    value=seller_data['gstin'],
                    placeholder="Enter GSTIN if applicable"
                )
            
            # Center-align the submit button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submitted = st.form_submit_button(
                    "💾 Save Seller" if edit_mode else "➕ Add Seller",
                    use_container_width=True,
                    type="primary"
                )
            
            if submitted:
                if not name or not address:
                    st.error("❌ Name and Address are required fields!")
                    return
                
                with get_db_connection() as conn:
                    if edit_mode:
                        with st.spinner("Updating seller details..."):
                            success, message = update_seller(
                                conn, seller_data['id'], name, address, phone, gstin
                            )
                    else:
                        with st.spinner("Adding new seller..."):
                            success, message = add_seller(conn, name, address, phone, gstin)
                    
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    with tab2:
        st.subheader("📊 View Sellers")
        
        with get_db_connection() as conn:
            sellers_df = pd.read_sql_query("""
                SELECT 
                    s.*,
                    COUNT(i.id) as total_invoices,
                    COALESCE(SUM(i.total_amount), 0) as total_sales,
                    MAX(i.date) as last_invoice_date,
                    COALESCE(SUM(st.amount), 0) as total_payments
                FROM sellers s
                LEFT JOIN invoices i ON s.id = i.seller_id
                LEFT JOIN seller_transactions st 
                    ON s.id = st.seller_id 
                    AND st.transaction_type = 'payment'
                GROUP BY s.id
                ORDER BY s.name
            """, conn)
            
            if not sellers_df.empty:
                # Convert NaN to 0 for numeric columns
                numeric_columns = ['total_invoices', 'total_sales', 'total_payments']
                sellers_df[numeric_columns] = sellers_df[numeric_columns].fillna(0)
                
                # Ensure remaining credit is not negative
                sellers_df['remaining_credit'] = sellers_df['total_credit'] - sellers_df['total_payments']
                sellers_df['remaining_credit'] = sellers_df['remaining_credit'].apply(lambda x: max(0, x))
                
                # Add search functionality
                search = st.text_input("🔍 Search Sellers", placeholder="Type to search by name, phone, or GSTIN...")
                
                if search:
                    mask = (
                        sellers_df['name'].str.contains(search, case=False, na=False) |
                        sellers_df['phone'].str.contains(search, case=False, na=False) |
                        sellers_df['gstin'].str.contains(search, case=False, na=False)
                    )
                    filtered_df = sellers_df[mask]
                else:
                    filtered_df = sellers_df
                
                if filtered_df.empty:
                    st.info("ℹ️ No sellers match your search criteria.")
                else:
                    st.dataframe(
                        filtered_df,
                        column_config={
                            "id": None,  # Hide ID column
                            "name": st.column_config.TextColumn(
                                "Name",
                                width="medium",
                                help="Seller's name"
                            ),
                            "address": st.column_config.TextColumn(
                                "Address",
                                width="large",
                                help="Seller's address"
                            ),
                            "phone": st.column_config.TextColumn(
                                "Phone",
                                width="medium",
                                help="Contact number"
                            ),
                            "gstin": "GSTIN",
                            "total_invoices": st.column_config.NumberColumn(
                                "Total Invoices",
                                help="Total number of invoices",
                                format="%d"
                            ),
                            "total_sales": st.column_config.NumberColumn(
                                "Total Sales",
                                format="₹%.2f",
                                help="Total amount from all sales"
                            ),
                            "total_payments": st.column_config.NumberColumn(
                                "Total Payments",
                                format="₹%.2f",
                                help="Total payments received"
                            ),
                            "remaining_credit": st.column_config.NumberColumn(
                                "Remaining Credit",
                                format="₹%.2f",
                                help="Current outstanding credit"
                            ),
                            "last_invoice_date": st.column_config.DateColumn(
                                "Last Invoice",
                                format="DD-MM-YYYY",
                                help="Date of last invoice"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Add summary metrics
                    st.markdown("### 📈 Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "Total Sellers",
                            len(filtered_df),
                            help="Number of sellers"
                        )
                    with col2:
                        st.metric(
                            "Total Sales",
                            f"₹{filtered_df['total_sales'].sum():,.2f}",
                            help="Sum of all sales"
                        )
                    with col3:
                        st.metric(
                            "Total Payments",
                            f"₹{filtered_df['total_payments'].sum():,.2f}",
                            help="Sum of all payments"
                        )
                    with col4:
                        st.metric(
                            "Total Outstanding",
                            f"₹{filtered_df['remaining_credit'].sum():,.2f}",
                            help="Total pending credits"
                        )
            else:
                st.info("ℹ️ No sellers found. Add sellers using the Add/Edit Sellers tab.")
    
    with tab3:
        st.subheader("💰 Manage Credits")
        
        with get_db_connection() as conn:
            # Get seller list
            sellers_df = pd.read_sql_query("""
                SELECT id, name, phone 
                FROM sellers 
                ORDER BY name
            """, conn)
            
            if not sellers_df.empty:
                # Create seller selection dropdown
                seller_options = list(zip(
                    sellers_df['id'],
                    sellers_df['name'],
                    sellers_df['phone']
                ))
                
                selected_seller_index = st.selectbox(
                    "Select Seller",
                    range(len(seller_options)),
                    format_func=lambda i: f"{seller_options[i][1]} ({seller_options[i][2]})"
                )
                
                selected_seller_id = seller_options[selected_seller_index][0]
                
                # Get seller summary
                summary_query = """
                    WITH invoice_summary AS (
                        SELECT 
                            seller_id,
                            COUNT(id) as total_invoices,
                            SUM(total_amount) as total_sales,
                            SUM(CASE WHEN payment_status = 'credit' THEN total_amount ELSE 0 END) as total_credit_sales,
                            SUM(CASE WHEN payment_status = 'paid' THEN total_amount ELSE 0 END) as total_paid_sales
                        FROM invoices
                        GROUP BY seller_id
                    ),
                    payment_summary AS (
                        SELECT 
                            seller_id,
                            SUM(CASE WHEN transaction_type = 'payment' THEN amount ELSE 0 END) as total_payments
                        FROM seller_transactions
                        GROUP BY seller_id
                    )
                    SELECT 
                        s.*,
                        COALESCE(i.total_invoices, 0) as total_invoices,
                        COALESCE(i.total_sales, 0) as total_sales,
                        COALESCE(i.total_credit_sales, 0) as total_credit_sales,
                        COALESCE(i.total_paid_sales, 0) as total_paid_sales,
                        COALESCE(p.total_payments, 0) as total_payments,
                        COALESCE(i.total_credit_sales, 0) - COALESCE(p.total_payments, 0) as pending_amount
                    FROM sellers s
                    LEFT JOIN invoice_summary i ON s.id = i.seller_id
                    LEFT JOIN payment_summary p ON s.id = p.seller_id
                    WHERE s.id = ?
                    GROUP BY s.id
                """
                seller_summary = pd.read_sql_query(summary_query, conn, params=(selected_seller_id,))
                
                if not seller_summary.empty:
                    # Display seller info
                    st.write("### Seller Information")
                    st.write(f"**Name:** {seller_summary['name'].iloc[0]}")
                    st.write(f"**Phone:** {seller_summary['phone'].iloc[0]}")
                    
                    # Display credit metrics in two rows
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Total Sales", 
                            f"₹{float(seller_summary['total_sales'].iloc[0]):.2f}",
                            help="Total amount of all invoices (credit + paid)"
                        )
                    with col2:
                        st.metric(
                            "Total Credit Sales", 
                            f"₹{float(seller_summary['total_credit_sales'].iloc[0]):.2f}",
                            help="Total amount of credit invoices"
                        )
                    with col3:
                        st.metric(
                            "Total Paid Sales", 
                            f"₹{float(seller_summary['total_paid_sales'].iloc[0]):.2f}",
                            help="Total amount of paid invoices"
                        )
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Total Payments", 
                            f"₹{float(seller_summary['total_payments'].iloc[0]):.2f}",
                            help="Total payments received against credit invoices"
                        )
                    with col2:
                        st.metric(
                            "Pending Amount", 
                            f"₹{float(seller_summary['pending_amount'].iloc[0]):.2f}",
                            help="Total amount pending to be paid"
                        )
                    with col3:
                        st.metric(
                            "Total Invoices", 
                            int(seller_summary['total_invoices'].iloc[0]),
                            help="Total number of invoices"
                        )
                    
                    # Payment form
                    with st.form("payment_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            pending_amount = float(seller_summary['pending_amount'].iloc[0])
                            amount = st.number_input(
                                "Payment Amount", 
                                min_value=0.0, 
                                max_value=float(pending_amount),
                                step=0.01,
                                value=0.0,
                                format="%.2f",
                                help=f"Maximum payment amount: ₹{pending_amount:.2f}"
                            )
                            payment_date = st.date_input(
                                "Payment Date",
                                value=datetime.now().date(),
                                max_value=datetime.now().date()
                            )
                        with col2:
                            notes = st.text_area("Notes")
                        
                        submitted = st.form_submit_button("Record Payment")
                        
                        if submitted:
                            if amount <= 0:
                                st.error("Payment amount must be greater than 0")
                            elif amount > pending_amount:
                                st.error(f"Payment amount cannot exceed pending amount (₹{pending_amount:.2f})")
                            else:
                                success, message = add_transaction(
                                    conn, 
                                    selected_seller_id, 
                                    amount, 
                                    'payment', 
                                    notes,
                                    payment_date=payment_date
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                    
                    # Show transactions history
                    st.write("### Payment History")
                    transactions_df = pd.read_sql_query("""
                        SELECT 
                            t.date,
                            t.amount,
                            t.transaction_type,
                            t.notes,
                            i.invoice_number,
                            i.total_amount as invoice_amount
                        FROM seller_transactions t
                        LEFT JOIN invoices i ON t.invoice_id = i.id
                        WHERE t.seller_id = ?
                        ORDER BY t.date DESC, t.id DESC
                    """, conn, params=(selected_seller_id,))
                    
                    if not transactions_df.empty:
                        st.dataframe(
                            transactions_df,
                            column_config={
                                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                                "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                                "transaction_type": "Type",
                                "notes": "Notes",
                                "invoice_number": "Invoice #",
                                "invoice_amount": st.column_config.NumberColumn("Invoice Amount", format="₹%.2f")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No transaction history found")
                    
                    # Show invoices
                    st.write("### Invoices")
                    invoices_df = pd.read_sql_query("""
                        SELECT 
                            i.invoice_number,
                            i.total_amount,
                            i.payment_status,
                            i.date,
                            COALESCE((
                                SELECT SUM(amount) 
                                FROM seller_transactions 
                                WHERE invoice_id = i.id 
                                AND transaction_type = 'payment'
                            ), 0) as paid_amount
                        FROM invoices i
                        WHERE i.seller_id = ?
                        ORDER BY i.date DESC, i.id DESC
                    """, conn, params=(selected_seller_id,))
                    
                    if not invoices_df.empty:
                        # Calculate balance
                        invoices_df['balance'] = invoices_df['total_amount'] - invoices_df['paid_amount']
                        st.dataframe(
                            invoices_df,
                            column_config={
                                "invoice_number": "Invoice #",
                                "total_amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                                "payment_status": "Status",
                                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                                "paid_amount": st.column_config.NumberColumn("Paid Amount", format="₹%.2f"),
                                "balance": st.column_config.NumberColumn("Balance", format="₹%.2f")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No invoices found")
                    
                    # Add invoice search
                    st.write("### Search Invoice")
                    invoice_number = st.text_input(
                        "Enter Invoice Number",
                        placeholder="e.g. INV0003",
                        help="Enter the invoice number to view details"
                    )
                    
                    if invoice_number:
                        invoice_details = pd.read_sql_query("""
                            SELECT 
                                i.*,
                                COALESCE((
                                    SELECT SUM(amount) 
                                    FROM seller_transactions 
                                    WHERE invoice_id = i.id 
                                    AND transaction_type = 'payment'
                                ), 0) as paid_amount,
                                json_extract(i.invoice_data, '$') as items_data
                            FROM invoices i
                            WHERE i.invoice_number = ? AND i.seller_id = ?
                        """, conn, params=(invoice_number, selected_seller_id))
                        
                        if not invoice_details.empty:
                            invoice = invoice_details.iloc[0]
                            
                            # Display invoice header
                            st.write("#### Invoice Details")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Invoice Number:** {invoice['invoice_number']}")
                                st.write(f"**Date:** {pd.to_datetime(invoice['date']).strftime('%d-%m-%Y')}")
                                st.write(f"**Status:** {invoice['payment_status']}")
                            
                            with col2:
                                st.write(f"**Total Amount:** ₹{float(invoice['total_amount']):.2f}")
                                st.write(f"**Paid Amount:** ₹{float(invoice['paid_amount']):.2f}")
                                balance = float(invoice['total_amount']) - float(invoice['paid_amount'])
                                st.write(f"**Balance:** ₹{balance:.2f}")
                            
                            # Display invoice items
                            if invoice['items_data']:
                                st.write("#### Items")
                                try:
                                    items_df = pd.read_json(invoice['items_data'])
                                    st.dataframe(
                                        items_df,
                                        column_config={
                                            "item_name": "Item Name",
                                            "item_code": "Item Code",
                                            "quantity": "Quantity",
                                            "price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                                            "discount_percentage": st.column_config.NumberColumn("Discount %", format="%.1f%%"),
                                            "discount_amount": st.column_config.NumberColumn("Discount", format="₹%.2f"),
                                            "gst_percentage": st.column_config.NumberColumn("GST %", format="%.1f%%"),
                                            "gst_amount": st.column_config.NumberColumn("GST", format="₹%.2f"),
                                            "total_amount": st.column_config.NumberColumn("Total", format="₹%.2f")
                                        },
                                        hide_index=True
                                    )
                                except Exception as e:
                                    st.error("Error displaying invoice items")
                            
                            # Show related transactions
                            transactions = pd.read_sql_query("""
                                SELECT 
                                    t.date,
                                    t.amount,
                                    t.transaction_type,
                                    t.notes
                                FROM seller_transactions t
                                WHERE t.invoice_id = ?
                                ORDER BY t.date DESC
                            """, conn, params=(invoice['id'],))
                            
                            if not transactions.empty:
                                st.write("#### Related Transactions")
                                st.dataframe(
                                    transactions,
                                    column_config={
                                        "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                                        "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                                        "transaction_type": "Type",
                                        "notes": "Notes"
                                    },
                                    hide_index=True
                                )
                        else:
                            st.warning("Invoice not found")
            else:
                st.info("No sellers found. Add sellers using the Add/Edit Sellers tab.")

if __name__ == "__main__":
    manage_sellers() 