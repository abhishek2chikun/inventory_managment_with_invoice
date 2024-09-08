import streamlit as st
import pandas as pd
import sqlite3
import ast
import re
from datetime import datetime, timedelta
import plotly.express as px

def preprocess_invoice_data(invoice_data):
    return re.sub(r'\bnan\b', 'None', invoice_data)

def reports():
    conn = sqlite3.connect('inventory.db')

    # Fetch products
    df_products = pd.read_sql_query("SELECT * FROM products", conn)

    # Fetch invoices
    df_invoices = pd.read_sql_query("SELECT * FROM invoices ORDER BY date DESC", conn)
    df_invoices['date'] = pd.to_datetime(df_invoices['date'])

    st.subheader("Products Table")
    st.dataframe(df_products)

    st.subheader("Invoices Table (Most Recent First)")
    st.dataframe(df_invoices)

    st.subheader("Analytics")

    # Process invoice data
    all_items = []
    for invoice_data in df_invoices['invoice_data']:
        try:
            preprocessed_data = preprocess_invoice_data(invoice_data)
            items = ast.literal_eval(preprocessed_data)
            all_items.extend(items)
        except (ValueError, SyntaxError) as e:
            st.warning(f"Couldn't parse invoice data: {invoice_data}\nError: {str(e)}")

    df_items = pd.DataFrame(all_items)

    # Top selling products
    # st.subheader("Top 10 Selling Products")

    if not df_items.empty:
        top_products = df_items.groupby('item_name')['quantity'].sum().nlargest(20)
        fig = px.bar(top_products, x=top_products.index, y='quantity', title="Top 10 Selling Products")
        st.plotly_chart(fig)
    else:
        st.write("No item data available")

    # Revenue breakdown
    # st.subheader("Revenue Breakdown")

    # Last 30 days revenue
    # st.caption("Revenue for Last 30 Days")

    last_30_days = datetime.now() - timedelta(days=30)
    df_last_30_days = df_invoices[df_invoices['date'] >= last_30_days]
    if not df_last_30_days.empty:
        daily_revenue = df_last_30_days.groupby(df_last_30_days['date'].dt.date)['total_amount'].sum().reset_index()
        daily_revenue.columns = ['date', 'revenue']
        fig = px.bar(daily_revenue, x='date', y='revenue', title="Daily Revenue (Last 30 Days)")
        st.plotly_chart(fig)
    else:
        st.write("No revenue data available for the last 30 days")

    # Monthly revenue
    # st.caption("Monthly Revenue")
    if not df_invoices.empty:
        monthly_revenue = df_invoices.groupby(df_invoices['date'].dt.to_period('M'))['total_amount'].sum().reset_index()
        monthly_revenue['date'] = monthly_revenue['date'].astype(str)
        monthly_revenue.columns = ['month', 'revenue']
        fig = px.bar(monthly_revenue, x='month', y='revenue', title="Monthly Revenue")
        st.plotly_chart(fig)
    else:
        st.write("No revenue data available")

    conn.close()
