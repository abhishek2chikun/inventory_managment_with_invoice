import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db_manager import get_db_connection
from utils.logger import setup_logger

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

def add_transaction(conn, seller_id, amount, transaction_type, notes, invoice_id=None):
    try:
        with conn:
            # Add transaction record
            conn.execute('''
                INSERT INTO seller_transactions 
                (seller_id, invoice_id, amount, transaction_type, date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (seller_id, invoice_id, amount, transaction_type, 
                 datetime.now().strftime('%Y-%m-%d'), notes))
            
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

def manage_sellers():
    st.title("Manage Sellers")
    
    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["Add/Edit Sellers", "View Sellers", "Manage Credits"])
    
    with tab1:
        st.subheader("Add/Edit Seller")
        
        # Get existing seller for editing if selected
        with get_db_connection() as conn:
            sellers_df = pd.read_sql_query("SELECT * FROM sellers", conn)
        
        edit_mode = st.checkbox("Edit Existing Seller")
        
        if edit_mode and not sellers_df.empty:
            selected_seller = st.selectbox(
                "Select Seller to Edit",
                sellers_df['name'].tolist()
            )
            seller_data = sellers_df[sellers_df['name'] == selected_seller].iloc[0]
        else:
            seller_data = pd.Series({'name': '', 'address': '', 'phone': '', 'gstin': ''})
        
        with st.form("seller_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name", value=seller_data['name'])
                phone = st.text_input("Phone", value=seller_data['phone'])
            
            with col2:
                address = st.text_area("Address", value=seller_data['address'])
                gstin = st.text_input("GSTIN", value=seller_data['gstin'])
            
            submitted = st.form_submit_button("Save Seller")
            
            if submitted:
                with get_db_connection() as conn:
                    if edit_mode:
                        success, message = update_seller(
                            conn, seller_data['id'], name, address, phone, gstin
                        )
                    else:
                        success, message = add_seller(conn, name, address, phone, gstin)
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    with tab2:
        st.subheader("View Sellers")
        
        with get_db_connection() as conn:
            # Get sellers with their total credits
            sellers_df = pd.read_sql_query("""
                SELECT s.*, 
                       COUNT(DISTINCT i.id) as total_invoices,
                       COALESCE(SUM(CASE WHEN i.payment_status = 'credit' THEN i.total_amount ELSE 0 END), 0) as total_credit_amount
                FROM sellers s
                LEFT JOIN invoices i ON s.id = i.seller_id
                GROUP BY s.id
            """, conn)
            
            if not sellers_df.empty:
                st.dataframe(
                    sellers_df,
                    column_config={
                        "name": "Name",
                        "address": "Address",
                        "phone": "Phone",
                        "gstin": "GSTIN",
                        "total_credit": st.column_config.NumberColumn(
                            "Total Credit",
                            format="₹%.2f"
                        ),
                        "total_invoices": "Total Invoices",
                        "total_credit_amount": st.column_config.NumberColumn(
                            "Credit Amount",
                            format="₹%.2f"
                        )
                    },
                    hide_index=True
                )
            else:
                st.info("No sellers found. Add sellers using the Add/Edit Sellers tab.")
    
    with tab3:
        st.subheader("Manage Credits")
        
        with get_db_connection() as conn:
            sellers_df = pd.read_sql_query("SELECT * FROM sellers", conn)
            
            if not sellers_df.empty:
                selected_seller = st.selectbox(
                    "Select Seller",
                    sellers_df['name'].tolist(),
                    key="credit_seller_select"
                )
                
                seller_data = sellers_df[sellers_df['name'] == selected_seller].iloc[0]
                
                # Show seller's credit information
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Credit", f"₹{seller_data['total_credit']:.2f}")
                
                # Get seller's transactions
                transactions_df = pd.read_sql_query("""
                    SELECT t.*, i.invoice_number
                    FROM seller_transactions t
                    LEFT JOIN invoices i ON t.invoice_id = i.id
                    WHERE t.seller_id = ?
                    ORDER BY t.date DESC
                """, conn, params=(seller_data['id'],))
                
                # Add payment form
                with st.form("payment_form"):
                    amount = st.number_input("Payment Amount", min_value=0.0, step=0.01)
                    notes = st.text_area("Notes")
                    
                    submitted = st.form_submit_button("Record Payment")
                    
                    if submitted and amount > 0:
                        success, message = add_transaction(
                            conn, seller_data['id'], amount, 'payment', notes
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                # Show transaction history
                if not transactions_df.empty:
                    st.subheader("Transaction History")
                    st.dataframe(
                        transactions_df,
                        column_config={
                            "date": "Date",
                            "amount": st.column_config.NumberColumn(
                                "Amount",
                                format="₹%.2f"
                            ),
                            "transaction_type": "Type",
                            "invoice_number": "Invoice",
                            "notes": "Notes"
                        },
                        hide_index=True
                    )
            else:
                st.info("No sellers found. Add sellers using the Add/Edit Sellers tab.")

if __name__ == "__main__":
    manage_sellers() 