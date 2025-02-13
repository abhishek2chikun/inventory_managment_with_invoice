import streamlit as st
import pandas as pd
import sqlite3
import ast
import re
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def preprocess_invoice_data(invoice_data):
    return re.sub(r'\bnan\b', 'None', invoice_data)

def calculate_growth(current, previous):
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def reports():
    st.title("Business Analytics Dashboard")
    
    # Initialize database connection
    conn = sqlite3.connect('inventory.db')

    # Fetch all required data
    df_invoices = pd.read_sql_query("""
        SELECT 
            i.*,
            s.name as customer_name,
            s.total_credit as current_credit
        FROM invoices i
        LEFT JOIN sellers s ON i.seller_id = s.id
        ORDER BY i.date DESC
    """, conn)
    df_invoices['date'] = pd.to_datetime(df_invoices['date'])

    # Process invoice items
    all_items = []
    for invoice_data in df_invoices['invoice_data']:
        try:
            preprocessed_data = preprocess_invoice_data(invoice_data)
            items_df = pd.read_json(preprocessed_data)
            all_items.extend(items_df.to_dict('records'))
        except (ValueError, SyntaxError) as e:
            continue

    df_items = pd.DataFrame(all_items) if all_items else pd.DataFrame()

    # Time period selection
    st.sidebar.header("📅 Time Period")
    date_filter = st.sidebar.selectbox(
        "Select Period",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 365 Days", "All Time"],
        index=1
    )

    end_date = datetime.now()
    if date_filter == "Last 7 Days":
        start_date = end_date - timedelta(days=7)
    elif date_filter == "Last 30 Days":
        start_date = end_date - timedelta(days=30)
    elif date_filter == "Last 90 Days":
        start_date = end_date - timedelta(days=90)
    elif date_filter == "Last 365 Days":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = df_invoices['date'].min()

    filtered_invoices = df_invoices[
        (df_invoices['date'] >= start_date) & 
        (df_invoices['date'] <= end_date)
    ]

    # 1. Executive Summary
    st.header("📊 Executive Summary")
    
    # Calculate metrics
    current_period_revenue = filtered_invoices['total_amount'].sum()
    current_period_orders = len(filtered_invoices)
    current_period_avg_order = current_period_revenue / current_period_orders if current_period_orders > 0 else 0
    
    # Calculate previous period metrics for comparison
    previous_start = start_date - (end_date - start_date)
    previous_invoices = df_invoices[
        (df_invoices['date'] >= previous_start) & 
        (df_invoices['date'] < start_date)
    ]
    previous_revenue = previous_invoices['total_amount'].sum()
    previous_orders = len(previous_invoices)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        revenue_growth = calculate_growth(current_period_revenue, previous_revenue)
        st.metric(
            "Total Revenue",
            f"₹{current_period_revenue:,.2f}",
            f"{revenue_growth:+.1f}%",
            help="Total revenue and growth compared to previous period"
        )

    with col2:
        orders_growth = calculate_growth(current_period_orders, previous_orders)
        st.metric(
            "Total Orders",
            current_period_orders,
            f"{orders_growth:+.1f}%",
            help="Number of orders and growth compared to previous period"
        )

    with col3:
        credit_sales = filtered_invoices[filtered_invoices['payment_status'] == 'credit']['total_amount'].sum()
        credit_percentage = (credit_sales / current_period_revenue * 100) if current_period_revenue > 0 else 0
        st.metric(
            "Credit Sales",
            f"₹{credit_sales:,.2f}",
            f"{credit_percentage:.1f}% of total",
            help="Total credit sales and percentage of total sales"
        )

    with col4:
        total_credit = filtered_invoices['current_credit'].sum()
        st.metric(
            "Outstanding Credit",
            f"₹{total_credit:,.2f}",
            help="Total outstanding credit amount"
        )

    # 2. Sales Analysis
    st.header("📈 Sales Analysis")
    
    tab1, tab2 = st.tabs(["Daily Trends", "Product Performance"])
    
    with tab1:
        # Daily sales trend with moving average
        daily_sales = filtered_invoices.groupby(filtered_invoices['date'].dt.date).agg({
            'total_amount': 'sum',
            'id': 'count'
        }).reset_index()
        
        # Calculate 7-day moving averages
        daily_sales['revenue_ma'] = daily_sales['total_amount'].rolling(7).mean()
        daily_sales['orders_ma'] = daily_sales['id'].rolling(7).mean()
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Scatter(
                x=daily_sales['date'],
                y=daily_sales['total_amount'],
                name="Daily Revenue",
                line=dict(color='blue', width=1)
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_sales['date'],
                y=daily_sales['revenue_ma'],
                name="7-day Moving Avg (Revenue)",
                line=dict(color='blue', width=2, dash='dash')
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_sales['date'],
                y=daily_sales['id'],
                name="Daily Orders",
                line=dict(color='green', width=1)
            ),
            secondary_y=True
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_sales['date'],
                y=daily_sales['orders_ma'],
                name="7-day Moving Avg (Orders)",
                line=dict(color='green', width=2, dash='dash')
            ),
            secondary_y=True
        )
        
        fig.update_layout(
            title="Daily Sales Trends with Moving Averages",
            xaxis_title="Date",
            yaxis_title="Revenue (₹)",
            yaxis2_title="Number of Orders",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if not df_items.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Top products by revenue
                product_revenue = df_items.groupby('item_name').agg({
                    'total_amount': 'sum',
                    'quantity': 'sum'
                }).reset_index()
                
                product_revenue = product_revenue.sort_values('total_amount', ascending=True).tail(10)
                
                fig = go.Figure(go.Bar(
                    x=product_revenue['total_amount'],
                    y=product_revenue['item_name'],
                    orientation='h',
                    text=product_revenue['total_amount'].apply(lambda x: f'₹{x:,.2f}'),
                    textposition='auto',
                ))
                
                fig.update_layout(
                    title="Top 10 Products by Revenue",
                    xaxis_title="Revenue (₹)",
                    yaxis_title="Product",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Top products by quantity
                product_quantity = df_items.groupby('item_name').agg({
                    'quantity': 'sum',
                    'total_amount': 'sum'
                }).reset_index()
                
                product_quantity = product_quantity.sort_values('quantity', ascending=True).tail(10)
                
                fig = go.Figure(go.Bar(
                    x=product_quantity['quantity'],
                    y=product_quantity['item_name'],
                    orientation='h',
                    text=product_quantity['quantity'].apply(lambda x: f'{int(x):,}'),
                    textposition='auto',
                ))
                
                fig.update_layout(
                    title="Top 10 Products by Quantity Sold",
                    xaxis_title="Units Sold",
                    yaxis_title="Product",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)

    # 3. Customer Analysis
    st.header("👥 Customer Analysis")
    
    # RFM Analysis
    if not filtered_invoices.empty and len(filtered_invoices['customer_name'].unique()) >= 2:
        st.subheader("Customer Segmentation (RFM Analysis)")
        
        # Calculate RFM metrics
        current_date = datetime.now()
        rfm = filtered_invoices.groupby('customer_name').agg({
            'date': lambda x: (current_date - x.max()).days,  # Recency
            'id': 'count',  # Frequency
            'total_amount': 'sum'  # Monetary
        }).reset_index()
        
        rfm.columns = ['customer_name', 'recency', 'frequency', 'monetary']
        
        # Function to create scores handling duplicates
        def create_scores(series, reverse=False):
            if len(series.unique()) < 5:
                # If we have less than 5 unique values, use quantile-based scoring
                if len(series.unique()) == 1:
                    # If all values are the same, assign middle score
                    return pd.Series([3] * len(series))
                else:
                    # Use as many quantiles as unique values
                    labels = range(1, len(series.unique()) + 1)
                    if reverse:
                        labels = list(reversed(labels))
                    return pd.qcut(series, q=len(series.unique()), labels=labels, duplicates='drop')
            else:
                # If we have 5 or more unique values, proceed with quintiles
                labels = range(1, 6)
                if reverse:
                    labels = list(reversed(labels))
                return pd.qcut(series, q=5, labels=labels, duplicates='drop')
        
        # Score RFM metrics
        try:
            rfm['r_score'] = create_scores(rfm['recency'], reverse=True)  # Higher score for lower recency
            rfm['f_score'] = create_scores(rfm['frequency'])  # Higher score for higher frequency
            rfm['m_score'] = create_scores(rfm['monetary'])   # Higher score for higher monetary value
            
            # Calculate RFM Score
            rfm['r_score'] = rfm['r_score'].astype(int)
            rfm['f_score'] = rfm['f_score'].astype(int)
            rfm['m_score'] = rfm['m_score'].astype(int)
            
            # Segment customers with adjusted logic
            def segment_customers(row):
                avg_score = (row['r_score'] + row['f_score'] + row['m_score']) / 3
                if avg_score >= 4:
                    return 'Champions'
                elif avg_score >= 3:
                    return 'Loyal Customers'
                elif avg_score >= 2:
                    return 'Regular Customers'
                else:
                    return 'New/Inactive Customers'
            
            rfm['customer_segment'] = rfm.apply(segment_customers, axis=1)
            
            # Display segments
            segment_counts = rfm['customer_segment'].value_counts()
            
            col1, col2 = st.columns(2)
        
            with col1:
                fig = px.pie(
                    values=segment_counts.values,
                    names=segment_counts.index,
                    title="Customer Segments Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, use_container_width=True)
        
            with col2:
                segment_metrics = rfm.groupby('customer_segment').agg({
                    'monetary': 'sum',
                    'frequency': 'mean',
                    'recency': 'mean'
                }).round(2)
                
                segment_metrics['monetary'] = segment_metrics['monetary'].apply(lambda x: f"₹{x:,.2f}")
                segment_metrics['frequency'] = segment_metrics['frequency'].apply(lambda x: f"{x:.1f}")
                segment_metrics['recency'] = segment_metrics['recency'].apply(lambda x: f"{x:.0f} days")
                
                st.dataframe(
                    segment_metrics,
                    column_config={
                        "monetary": "Total Revenue",
                        "frequency": "Avg Orders",
                        "recency": "Avg Recency"
                    },
                    height=300
                )
                
                # Add segment descriptions
                st.markdown("""
                **Customer Segments:**
                - **Champions**: Most valuable customers with high spending and frequent purchases
                - **Loyal Customers**: Regular customers with consistent purchasing patterns
                - **Regular Customers**: Customers with moderate purchase frequency and spending
                - **New/Inactive Customers**: New customers or those who haven't purchased recently
                """)
        except Exception as e:
            st.warning("Not enough variation in customer data for detailed segmentation. Please check back when more data is available.")
            st.error(f"Technical details: {str(e)}")
    else:
        st.info("Not enough customer data for segmentation analysis. Please check back when more data is available.")

    # 4. Credit Analysis
    st.header("💳 Credit Analysis")
    
    credit_data = filtered_invoices[filtered_invoices['payment_status'] == 'credit']
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Credit sales trend
        daily_credit = credit_data.groupby(credit_data['date'].dt.date).agg({
            'total_amount': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_credit['date'],
            y=daily_credit['total_amount'],
            mode='lines',
            name='Credit Sales'
        ))
        
        fig.update_layout(
            title="Daily Credit Sales Trend",
            xaxis_title="Date",
            yaxis_title="Amount (₹)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top customers by credit
        top_credit_customers = filtered_invoices.groupby('customer_name').agg({
            'current_credit': 'max'
        }).reset_index()
        
        top_credit_customers = top_credit_customers.sort_values('current_credit', ascending=True).tail(10)
        
        fig = go.Figure(go.Bar(
            x=top_credit_customers['current_credit'],
            y=top_credit_customers['customer_name'],
            orientation='h',
            text=top_credit_customers['current_credit'].apply(lambda x: f'₹{x:,.2f}'),
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Top 10 Customers by Outstanding Credit",
            xaxis_title="Outstanding Credit (₹)",
            yaxis_title="Customer"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # 5. Inventory Insights
    st.header("📦 Inventory Insights")
    
    # Fetch current inventory
    inventory_df = pd.read_sql_query("""
        SELECT * FROM products
        WHERE quantity > 0
    """, conn)
    
    if not inventory_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Stock value by category
            inventory_df['stock_value'] = inventory_df['buying_price'] * inventory_df['quantity']
            category_stock = inventory_df.groupby('category')['stock_value'].sum().sort_values(ascending=True)
            
            fig = go.Figure(go.Bar(
                x=category_stock.values,
                y=category_stock.index,
                orientation='h',
                text=category_stock.values.round(2),
                textposition='auto'
            ))
            
            fig.update_layout(
                title="Inventory Value by Category",
                xaxis_title="Value (₹)",
                yaxis_title="Category"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Low stock alerts
            low_stock_threshold = 5  # Can be made configurable
            low_stock_items = inventory_df[inventory_df['quantity'] <= low_stock_threshold]
            
            if not low_stock_items.empty:
                st.warning(f"⚠️ {len(low_stock_items)} items are running low on stock!")
                
                st.dataframe(
                    low_stock_items[['item_name', 'quantity', 'category']],
                    column_config={
                        "item_name": "Item",
                        "quantity": "Current Stock",
                        "category": "Category"
                    },
                    hide_index=True
                )
            else:
                st.success("✅ All items are well-stocked!")

    conn.close()

if __name__ == "__main__":
    reports()
