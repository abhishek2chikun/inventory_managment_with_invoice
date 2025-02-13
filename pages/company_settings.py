import streamlit as st
import pandas as pd
from utils.db_manager import get_db_connection, ensure_company_details_exist
from utils.logger import setup_logger
import time

logger = setup_logger()

def update_company_details(conn, details):
    try:
        with conn:
            conn.execute("""
                UPDATE company_details 
                SET name = ?, address = ?, city = ?, state = ?, 
                    state_code = ?, gstin = ?, phone = ?, email = ?,
                    bank_name = ?, bank_account = ?, bank_ifsc = ?,
                    bank_branch = ?, jurisdiction = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (
                details['name'], details['address'], details['city'],
                details['state'], details['state_code'], details['gstin'],
                details['phone'], details['email'], details['bank_name'],
                details['bank_account'], details['bank_ifsc'],
                details['bank_branch'], details['jurisdiction']
            ))
            return True, "Company details updated successfully!"
    except Exception as e:
        logger.error(f"Error updating company details: {e}")
        return False, f"Error: {str(e)}"

def company_settings():
    st.title("Company Settings")
    
    # Ensure database is initialized
    if not ensure_company_details_exist():
        st.error("❌ Failed to initialize database. Please check the logs.")
        return
    
    # Get current company details
    with get_db_connection() as conn:
        company_df = pd.read_sql_query("""
            SELECT * FROM company_details 
            WHERE id = 1
        """, conn)
        
        if company_df.empty:
            st.error("❌ Company details not found in database!")
            return
        
        company_data = company_df.iloc[0]
    
    # Create form for company details
    with st.form("company_details_form"):
        st.subheader("🏢 Company Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Company Name*",
                value=company_data['name'],
                help="Legal name of the company"
            )
            address = st.text_area(
                "Address*",
                value=company_data['address'],
                help="Complete address"
            )
            city = st.text_input(
                "City*",
                value=company_data['city']
            )
            state = st.text_input(
                "State*",
                value=company_data['state']
            )
            state_code = st.text_input(
                "State Code*",
                value=company_data['state_code'],
                help="State code for GST"
            )
            gstin = st.text_input(
                "GSTIN*",
                value=company_data['gstin'],
                help="GST Identification Number"
            )
        
        with col2:
            phone = st.text_input(
                "Phone",
                value=company_data['phone']
            )
            email = st.text_input(
                "Email",
                value=company_data['email']
            )
            jurisdiction = st.text_input(
                "Jurisdiction*",
                value=company_data['jurisdiction'],
                help="Legal jurisdiction for invoices"
            )
        
        st.subheader("🏦 Bank Details")
        col1, col2 = st.columns(2)
        with col1:
            bank_name = st.text_input(
                "Bank Name*",
                value=company_data['bank_name']
            )
            bank_account = st.text_input(
                "Account Number*",
                value=company_data['bank_account']
            )
        
        with col2:
            bank_ifsc = st.text_input(
                "IFSC Code*",
                value=company_data['bank_ifsc']
            )
            bank_branch = st.text_input(
                "Branch Name*",
                value=company_data['bank_branch']
            )
        
        # Add preview of how it will look on invoice
        st.subheader("📄 Preview")
        st.markdown("""
        <style>
        .preview-box {
            border: 1px solid #ccc;
            padding: 15px;
            border-radius: 5px;
            background-color: #f8f9fa;
            font-family: monospace;
        }
        </style>
        """, unsafe_allow_html=True)
        
        preview = f"""
        <div class="preview-box">
        <b>{name}</b><br>
        {address}<br>
        {city}, {state} - {state_code}<br>
        GSTIN: {gstin}<br>
        Phone: {phone}<br>
        Email: {email}<br>
        <br>
        Bank Details:<br>
        Bank: {bank_name}<br>
        A/c: {bank_account}<br>
        IFSC: {bank_ifsc}<br>
        Branch: {bank_branch}
        </div>
        """
        st.markdown(preview, unsafe_allow_html=True)
        
        # Submit button
        submitted = st.form_submit_button(
            "💾 Save Company Details",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # Validate required fields
            required_fields = {
                'name': name,
                'address': address,
                'city': city,
                'state': state,
                'state_code': state_code,
                'gstin': gstin,
                'bank_name': bank_name,
                'bank_account': bank_account,
                'bank_ifsc': bank_ifsc,
                'bank_branch': bank_branch,
                'jurisdiction': jurisdiction
            }
            
            missing_fields = [k for k, v in required_fields.items() if not v]
            if missing_fields:
                st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
                return
            
            # Update company details
            with get_db_connection() as conn:
                with st.spinner("Updating company details..."):
                    success, message = update_company_details(conn, {
                        'name': name,
                        'address': address,
                        'city': city,
                        'state': state,
                        'state_code': state_code,
                        'gstin': gstin,
                        'phone': phone,
                        'email': email,
                        'bank_name': bank_name,
                        'bank_account': bank_account,
                        'bank_ifsc': bank_ifsc,
                        'bank_branch': bank_branch,
                        'jurisdiction': jurisdiction
                    })
                    
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

if __name__ == "__main__":
    company_settings() 