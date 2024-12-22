import streamlit as st
import pandas as pd
import sqlite3
import ast
import re
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

def preprocess_invoice_data(invoice_data):
    return re.sub(r'\bnan\b', 'None', invoice_data)

def reports():
    st.title("Sales Analytics Dashboard")
    conn = sqlite3.connect('inventory.db')

    # Fetch invoices
    df_invoices = pd.read_sql_query("SELECT * FROM invoices ORDER BY date DESC", conn)
    df_invoices['date'] = pd.to_datetime(df_invoices['date'])

    # Process invoice data
    all_items = []
    for invoice_data in df_invoices['invoice_data']:
        try:
            preprocessed_data = preprocess_invoice_data(invoice_data)
            items_df = pd.read_json(preprocessed_data)
            all_items.extend(items_df.to_dict('records'))
        except (ValueError, SyntaxError) as e:
            st.warning(f"Couldn't parse invoice data: {str(e)}")
            continue

    df_items = pd.DataFrame(all_items) if all_items else pd.DataFrame(
        columns=['item_name', 'item_code', 'quantity', 'price', 'total_amount', 'gst_percentage']
    )

    # Calculate time periods
    today = datetime.now()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Total Revenue
        total_revenue = df_invoices['total_amount'].sum()
        st.metric(
            "Total Revenue",
            f"₹{total_revenue:,.2f}",
            help="Total revenue from all sales"
        )

    with col2:
        # Last 30 Days Revenue
        last_30_revenue = df_invoices[df_invoices['date'] >= last_30_days]['total_amount'].sum()
        last_60_30_revenue = df_invoices[
            (df_invoices['date'] >= last_30_days - timedelta(days=30)) & 
            (df_invoices['date'] < last_30_days)
        ]['total_amount'].sum()
        revenue_change = ((last_30_revenue - last_60_30_revenue) / last_60_30_revenue * 100) if last_60_30_revenue != 0 else 0
        
        st.metric(
            "Last 30 Days Revenue",
            f"₹{last_30_revenue:,.2f}",
            f"{revenue_change:+.1f}%",
            help="Revenue from the last 30 days compared to previous 30 days"
        )

    with col3:
        # Average Order Value
        avg_order = df_invoices['total_amount'].mean()
        st.metric(
            "Average Order Value",
            f"₹{avg_order:,.2f}",
            help="Average value per order"
        )

    with col4:
        # Total Orders
        total_orders = len(df_invoices)
        recent_orders = len(df_invoices[df_invoices['date'] >= last_30_days])
        st.metric(
            "Total Orders",
            f"{total_orders}",
            f"{recent_orders} in last 30 days",
            help="Total number of orders"
        )

    # Sales Trends
    st.subheader("Sales Trends")
    tab1, tab2 = st.tabs(["Daily Trends", "Monthly Trends"])
    
    with tab1:
        # Daily Revenue Trend
        if not df_invoices.empty:
            daily_revenue = df_invoices.groupby(df_invoices['date'].dt.date)['total_amount'].agg([
                ('revenue', 'sum'),
                ('orders', 'count')
            ]).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_revenue['date'],
                y=daily_revenue['revenue'],
                name='Revenue',
                line=dict(color='blue')
            ))
            fig.add_trace(go.Scatter(
                x=daily_revenue['date'],
                y=daily_revenue['orders'] * daily_revenue['revenue'].mean() / daily_revenue['orders'].mean(),
                name='Orders',
                line=dict(color='green', dash='dash'),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title='Daily Revenue and Orders',
                yaxis=dict(title='Revenue (₹)'),
                yaxis2=dict(title='Orders', overlaying='y', side='right'),
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Monthly Trends
        if not df_invoices.empty:
            monthly_data = df_invoices.groupby(df_invoices['date'].dt.to_period('M')).agg({
                'total_amount': 'sum',
                'id': 'count'
            }).reset_index()
            monthly_data['date'] = monthly_data['date'].astype(str)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly_data['date'],
                y=monthly_data['total_amount'],
                name='Revenue'
            ))
            fig.add_trace(go.Scatter(
                x=monthly_data['date'],
                y=monthly_data['id'],
                name='Orders',
                yaxis='y2'
            ))
            
            fig.update_layout(
                title='Monthly Revenue and Orders',
                yaxis=dict(title='Revenue (₹)'),
                yaxis2=dict(title='Number of Orders', overlaying='y', side='right'),
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

    # Product Performance
    st.subheader("Product Performance")
    if not df_items.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Top Selling Products by Quantity
            top_products_qty = df_items.groupby('item_name')['quantity'].sum().nlargest(10)
            fig = px.bar(
                top_products_qty,
                title="Top 10 Products by Quantity Sold",
                labels={'value': 'Units Sold', 'item_name': 'Product'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top Products by Revenue
            df_items['revenue'] = df_items['quantity'] * df_items['price']
            top_products_revenue = df_items.groupby('item_name')['revenue'].sum().nlargest(10)
            fig = px.bar(
                top_products_revenue,
                title="Top 10 Products by Revenue",
                labels={'value': 'Revenue (₹)', 'item_name': 'Product'}
            )
            st.plotly_chart(fig, use_container_width=True)

    # Customer Analysis
    st.subheader("Customer Analysis")
    if not df_invoices.empty:
        # Customer purchase frequency
        customer_freq = df_invoices.groupby('customer_name').agg({
            'id': 'count',
            'total_amount': 'sum'
        }).reset_index()
        customer_freq.columns = ['Customer', 'Purchase Frequency', 'Total Spent']
        
        fig = px.scatter(
            customer_freq,
            x='Purchase Frequency',
            y='Total Spent',
            text='Customer',
            title='Customer Purchase Behavior',
            labels={
                'Purchase Frequency': 'Number of Orders',
                'Total Spent': 'Total Amount Spent (₹)'
            }
        )
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

    # Customer History
    st.subheader("Customer History")
    if not df_invoices.empty:
        # Get detailed customer history
        customer_history = df_invoices.groupby('customer_name').agg({
            'id': 'count',
            'total_amount': ['sum', 'mean'],
            'date': ['min', 'max']
        }).reset_index()
        
        customer_history.columns = [
            'Customer', 'Total Orders', 'Total Spent', 
            'Average Order Value', 'First Order', 'Last Order'
        ]
        
        # Calculate customer lifetime
        customer_history['Customer Lifetime (Days)'] = (
            pd.to_datetime(customer_history['Last Order']) - 
            pd.to_datetime(customer_history['First Order'])
        ).dt.days
        
        # Calculate average order frequency
        customer_history['Avg Days Between Orders'] = (
            customer_history['Customer Lifetime (Days)'] / 
            customer_history['Total Orders']
        ).round(1)
        
        # Format currency columns
        customer_history['Total Spent'] = customer_history['Total Spent'].apply(
            lambda x: f"₹{x:,.2f}"
        )
        customer_history['Average Order Value'] = customer_history['Average Order Value'].apply(
            lambda x: f"₹{x:,.2f}"
        )
        
        # Display customer history table
        st.dataframe(
            customer_history.sort_values('Last Order', ascending=False),
            column_config={
                "Customer": st.column_config.TextColumn("Customer Name"),
                "Total Orders": st.column_config.NumberColumn("Total Orders"),
                "Total Spent": st.column_config.TextColumn("Total Spent"),
                "Average Order Value": st.column_config.TextColumn("Avg Order Value"),
                "First Order": st.column_config.DateColumn("First Order"),
                "Last Order": st.column_config.DateColumn("Last Order"),
                "Customer Lifetime (Days)": st.column_config.NumberColumn("Customer Lifetime"),
                "Avg Days Between Orders": st.column_config.NumberColumn("Avg Days Between Orders")
            },
            hide_index=True
        )
        
        # Customer Retention Analysis
        st.subheader("Customer Retention Analysis")
        
        # Calculate repeat customer rate
        total_customers = customer_history['Customer'].nunique()
        repeat_customers = customer_history[customer_history['Total Orders'] > 1]['Customer'].nunique()
        repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Customers",
                total_customers,
                help="Total number of unique customers"
            )
        
        with col2:
            st.metric(
                "Repeat Customers",
                repeat_customers,
                help="Number of customers with more than one order"
            )
        
        with col3:
            st.metric(
                "Repeat Customer Rate",
                f"{repeat_rate:.1f}%",
                help="Percentage of customers who made repeat purchases"
            )

    conn.close()

if __name__ == "__main__":
    reports()
