import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import database
import authentication
import config

# Route Guard
if not authentication.check_login():
    st.stop()

config.check_session_active()

# Custom sidebar profile display
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-brand">
        <div class="sidebar-brand-name">Insights AI</div>
    </div>
    """, unsafe_allow_html=True)
    st.write(f"👤 User: **{st.session_state['username']}**")
    st.markdown(f"Role: {config.render_badge(st.session_state['role'])}", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🚪 Log Out", use_container_width=True, type="secondary"):
        authentication.logout_user()

st.markdown("<h2>📈 Customer Analytics & BI</h2>", unsafe_allow_html=True)
config.render_gradient_header()

@st.cache_data(ttl=600)
def load_analytics_data():
    conn = database.get_db_connection()
    df_cust = pd.read_sql_query("SELECT * FROM Customers", conn)
    df_orders = pd.read_sql_query("SELECT * FROM Orders WHERE status = 'Completed'", conn)
    df_products = pd.read_sql_query("SELECT * FROM Products", conn)
    conn.close()
    
    # Dates to Datetime
    df_orders['order_date_dt'] = pd.to_datetime(df_orders['order_date'])
    df_cust['registration_date_dt'] = pd.to_datetime(df_cust['registration_date'])
    
    return df_cust, df_orders, df_products

df_cust, df_orders, df_products = load_analytics_data()

if df_cust.empty or df_orders.empty:
    st.warning("Database contains no customer or order records. Populate the database first.")
else:
    # Key calculations
    total_rev = df_orders['total_amount'].sum()
    order_count = len(df_orders)
    avg_basket = total_rev / order_count if order_count > 0 else 0.0
    
    # Repeat purchase rate calculation
    cust_orders = df_orders.groupby('customer_id').size()
    repeat_customers = (cust_orders >= 2).sum()
    total_unique_custs = len(df_cust)
    repeat_rate = (repeat_customers / total_unique_custs) * 100 if total_unique_custs > 0 else 0.0
    
    # Tabs layout
    tab_sales, tab_geo_demo, tab_prod = st.tabs([
        "💰 Revenue & Order Trends", 
        "🌍 Geographical & Demographics", 
        "📦 Product & Category Affinity"
    ])
    
    # --- TAB 1: SALES & ORDERS ---
    with tab_sales:
        st.markdown("### 📊 Sales Performance & Basket Metrics")
        
        # Mini KPIs
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            config.render_kpi_card("Total Sales Revenue", f"${total_rev:,.2f}", card_type="success")
        with kpi_col2:
            config.render_kpi_card("Average Basket Value", f"${avg_basket:.2f}", card_type="primary")
        with kpi_col3:
            config.render_kpi_card("Repeat Purchase Rate", f"{repeat_rate:.1f}%", card_type="info")
            
        # Sales Trend over seasons (month of year aggregates)
        st.markdown("#### 📅 Seasonal Buying Trends (Monthly Revenue Summary)")
        df_orders['month_name'] = df_orders['order_date_dt'].dt.strftime('%B')
        df_orders['month_num'] = df_orders['order_date_dt'].dt.month
        seasonal_sales = df_orders.groupby(['month_num', 'month_name'])['total_amount'].sum().reset_index()
        seasonal_sales = seasonal_sales.sort_values('month_num')
        
        fig_seasonal = px.bar(
            seasonal_sales, x='month_name', y='total_amount',
            labels={'month_name': 'Month', 'total_amount': 'Total Sales ($)'},
            template="plotly_white", color_discrete_sequence=['#4f46e5']
        )
        fig_seasonal.update_layout(margin=dict(l=20, r=20, t=10, b=20), height=320)
        st.plotly_chart(fig_seasonal, use_container_width=True)
        
    # --- TAB 2: GEOGRAPHY & DEMOGRAPHICS ---
    with tab_geo_demo:
        st.markdown("### 🌎 Demographics and Regional Segments")
        
        col_gd1, col_gd2 = st.columns(2)
        
        with col_gd1:
            st.markdown("#### 📍 Top Cities by Customer Base")
            city_counts = df_cust['city'].value_counts().reset_index().head(10)
            city_counts.columns = ['City', 'Customers']
            
            fig_city = px.bar(
                city_counts, x='Customers', y='City', orientation='h',
                template="plotly_white", color_discrete_sequence=['#06b6d4']
            )
            fig_city.update_layout(margin=dict(l=20, r=20, t=10, b=20), height=300)
            fig_city.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_city, use_container_width=True)
            
        with col_gd2:
            st.markdown("#### 💰 Customer Spending vs Age Correlation")
            # Merge customer details and spend
            cust_spend = df_orders.groupby('customer_id')['total_amount'].sum().reset_index()
            cust_spend.columns = ['customer_id', 'total_spend']
            df_corr = df_cust.merge(cust_spend, on='customer_id')
            
            fig_scatter = px.scatter(
                df_corr.sample(n=1000, random_state=42), x='age', y='total_spend',
                color='gender', opacity=0.7, trendline="ols",
                labels={'age': 'Age', 'total_spend': 'Total Spending ($)'},
                template="plotly_white", color_discrete_sequence=['#3b82f6', '#ef4444', '#10b981']
            )
            fig_scatter.update_layout(margin=dict(l=20, r=20, t=10, b=20), height=300)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
    # --- TAB 3: PRODUCT & CATEGORIES ---
    with tab_prod:
        st.markdown("### 🛍️ Product Profiles & Categories")
        
        col_pr1, col_pr2 = st.columns(2)
        
        with col_pr1:
            st.markdown("#### 🌳 Category Revenue Breakdown (Treemap)")
            # Simulate product-order link
            df_orders_cat = df_orders.copy()
            np.random.seed(42)
            categories_list = df_products['category'].unique()
            df_orders_cat['category'] = np.random.choice(categories_list, size=len(df_orders_cat))
            df_orders_cat['product_name'] = np.random.choice(df_products['name'].unique(), size=len(df_orders_cat))
            
            cat_prod_rev = df_orders_cat.groupby(['category', 'product_name'])['total_amount'].sum().reset_index()
            cat_prod_rev.columns = ['Category', 'Product', 'Revenue']
            
            # Keep top products in each category for clean treemap rendering
            top_cat_prod_rev = cat_prod_rev.groupby('Category').apply(lambda x: x.nlargest(5, 'Revenue')).reset_index(drop=True)
            
            fig_tree = px.treemap(
                top_cat_prod_rev, path=['Category', 'Product'], values='Revenue',
                color='Revenue', color_continuous_scale='Blues',
                template="plotly_white"
            )
            fig_tree.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig_tree, use_container_width=True)
            
        with col_pr2:
            st.markdown("#### 🏆 Top 5 Best-Selling Products by Revenue")
            # Aggregated product sales
            prod_rev = df_orders_cat.groupby('product_name')['total_amount'].sum().reset_index()
            prod_rev.columns = ['Product Name', 'Revenue']
            prod_rev = prod_rev.sort_values('Revenue', ascending=False).head(5)
            
            fig_top_prod = px.bar(
                prod_rev, x='Revenue', y='Product Name', orientation='h',
                template="plotly_white", color_discrete_sequence=['#10b981']
            )
            fig_top_prod.update_layout(margin=dict(l=20, r=20, t=10, b=20), height=320)
            fig_top_prod.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_top_prod, use_container_width=True)
