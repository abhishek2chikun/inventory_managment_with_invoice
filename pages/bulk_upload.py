import streamlit as st
import pandas as pd
import numpy as np
import pytesseract
from PIL import Image
import pdfplumber
import io
from utils.logger import setup_logger
from utils.db_manager import get_db_connection
import os

logger = setup_logger()

def extract_text_from_image(image_file):
    """Extract text from image using OCR"""
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logger.error(f"Error in OCR processing: {e}")
        return None

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF"""
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        logger.error(f"Error in PDF processing: {e}")
        return None

def parse_catalog_text(text):
    """Convert extracted text to structured data"""
    try:
        # This is a basic implementation - you might need to adjust based on your catalog format
        lines = text.split('\n')
        data = []
        
        for line in lines:
            if line.strip():
                # Attempt to parse line into product details
                parts = line.split()
                if len(parts) >= 3:  # Basic validation
                    data.append({
                        'company': parts[0],
                        'item_name': parts[1],
                        'category': 'Unknown',  # Default value
                        'item_code': '',
                        'buying_price': 0.0,
                        'selling_price': 0.0,
                        'unit_per_box': 0,
                        'quantity': 0,
                        'gst_percentage': 0.0
                    })
        
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error parsing catalog text: {e}")
        return pd.DataFrame()

def process_excel_file(file):
    """Process Excel/CSV file"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Ensure all required columns exist
        required_columns = ['company', 'category', 'item_name', 'item_code', 
                          'buying_price', 'selling_price', 'unit_per_box', 
                          'quantity', 'gst_percentage']
        
        # Create missing columns with default values
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
                
        return df[required_columns]  # Return only required columns
    except Exception as e:
        logger.error(f"Error processing Excel/CSV file: {e}")
        return pd.DataFrame()

def bulk_upload():
    st.title("Bulk Product Upload")
    
    # File upload section
    st.subheader("Upload Product Catalog")
    file = st.file_uploader("Choose a file", type=['csv', 'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'])
    
    if file is not None:
        try:
            # Process different file types
            if file.type.startswith('image'):
                text = extract_text_from_image(file)
                if text:
                    df = parse_catalog_text(text)
                else:
                    st.error("Could not extract text from image")
                    return
                    
            elif file.type == 'application/pdf':
                text = extract_text_from_pdf(file)
                if text:
                    df = parse_catalog_text(text)
                else:
                    st.error("Could not extract text from PDF")
                    return
                    
            else:  # Excel/CSV
                df = process_excel_file(file)
                
            if df.empty:
                st.error("No data could be extracted from the file")
                return
                
            # Data Editor
            st.subheader("Review and Edit Products")
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "company": st.column_config.TextColumn("Company"),
                    "category": st.column_config.TextColumn("Category"),
                    "item_name": st.column_config.TextColumn("Item Name"),
                    "item_code": st.column_config.TextColumn("Item Code"),
                    "buying_price": st.column_config.NumberColumn("Buying Price", min_value=0.0, format="%.2f"),
                    "selling_price": st.column_config.NumberColumn("Selling Price", min_value=0.0, format="%.2f"),
                    "unit_per_box": st.column_config.NumberColumn("Units per Box", min_value=0),
                    "quantity": st.column_config.NumberColumn("Quantity", min_value=0),
                    "gst_percentage": st.column_config.NumberColumn("GST %", min_value=0.0, max_value=100.0)
                },
                hide_index=True
            )
            
            # Validation before upload
            if st.button("Upload to Database"):
                # Validate required fields
                if edited_df[['company', 'item_name', 'category']].isna().any().any():
                    st.error("Company, Item Name, and Category are required fields")
                    return
                
                try:
                    with get_db_connection() as conn:
                        # Convert DataFrame to SQL-friendly format
                        records = edited_df.to_dict('records')
                        
                        success_count = 0
                        error_count = 0
                        
                        for record in records:
                            try:
                                conn.execute("""
                                    INSERT INTO products 
                                    (company, category, item_name, item_code, buying_price, 
                                     selling_price, unit_per_box, quantity, gst_percentage)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    record['company'], record['category'], record['item_name'],
                                    record['item_code'], record['buying_price'], record['selling_price'],
                                    record['unit_per_box'], record['quantity'], record['gst_percentage']
                                ))
                                success_count += 1
                            except sqlite3.IntegrityError:
                                error_count += 1
                                continue
                        
                        conn.commit()
                        
                        if success_count > 0:
                            st.success(f"Successfully uploaded {success_count} products!")
                        if error_count > 0:
                            st.warning(f"{error_count} products were skipped (possibly duplicates)")
                            
                except Exception as e:
                    logger.error(f"Database error: {e}")
                    st.error("Error uploading to database. Please check the logs for details.")
                    
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            st.error("Error processing file. Please check the file format and try again.") 