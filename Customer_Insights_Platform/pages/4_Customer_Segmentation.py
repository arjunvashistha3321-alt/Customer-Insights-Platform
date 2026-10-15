import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import joblib
from datetime import datetime

import database
import authentication
import utils
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

st.markdown("<h2>🎯 Customer Segmentation Analysis</h2>", unsafe_allow_html=True)
config.render_gradient_header()

st.write("Automatically classify customers based on their Recency, Frequency, and Monetary (RFM) profiles using Machine Learning and business rule heuristics.")

@st.cache_data(ttl=600)
def get_segmentation_data():
    conn = database.get_db_connection()
    df_cust = pd.read_sql_query("SELECT * FROM Customers", conn)
    df_orders = pd.read_sql_query("SELECT * FROM Orders WHERE status = 'Completed'", conn)
    conn.close()
    
    if len(df_cust) == 0 or len(df_orders) == 0:
        return pd.DataFrame(), pd.DataFrame()
        
    # Aggregate spending & counts
    cust_spend = df_orders.groupby('customer_id')['total_amount'].agg(['sum', 'count']).reset_index()
    cust_spend.columns = ['customer_id', 'total_spend', 'order_count']
    
    # Recency
    last_purch = df_orders.groupby('customer_id')['order_date'].max().reset_index()
    last_purch['last_purchase_date'] = pd.to_datetime(last_purch['order_date'])
    ref_date = datetime(2026, 6, 27)
    
    # Merge
    df_rfm = df_cust.merge(cust_spend, on='customer_id', how='left').merge(last_purch, on='customer_id', how='left')
    df_rfm['total_spend'] = df_rfm['total_spend'].fillna(0.0)
    df_rfm['order_count'] = df_rfm['order_count'].fillna(0)
    
    # Tenure
    df_rfm['reg_date_dt'] = pd.to_datetime(df_rfm['registration_date'])
    df_rfm['tenure_days'] = (ref_date - df_rfm['reg_date_dt']).dt.days
    
    # Recency Days
    df_rfm['recency_days'] = (ref_date - df_rfm['last_purchase_date']).dt.days
    df_rfm['recency_days'] = df_rfm['recency_days'].fillna(df_rfm['tenure_days'])
    
    return df_rfm

df_rfm = get_segmentation_data()

if df_rfm.empty:
    st.warning("Database contains no customer or transaction records. Populate the database in App.py first.")
else:
    # 1. Apply rule-based business segments
    # Define thresholds
    spend_90 = df_rfm['total_spend'].quantile(0.9)
    spend_75 = df_rfm['total_spend'].quantile(0.75)
    order_median = df_rfm['order_count'].median()
    
    def assign_business_segment(row):
        spend = row['total_spend']
        orders = row['order_count']
        recency = row['recency_days']
        tenure = row['tenure_days']
        
        if spend >= spend_90 and orders >= order_median and recency < 90:
            return "Premium Customers"
        elif orders >= 8 and recency < 120:
            return "Loyal Customers"
        elif spend >= spend_75 and orders < 5:
            return "High Spenders"
        elif tenure <= 90 and orders >= 1:
            return "New Customers"
        elif recency <= 60 and orders >= 3:
            return "Regular Customers"
        elif recency > 180 and orders >= 5:
            return "At-Risk Customers"
        elif recency > 180 and orders < 3:
            return "Inactive Customers"
        else:
            return "Occasional Buyers"
            
    df_rfm['business_segment'] = df_rfm.apply(assign_business_segment, axis=1)
    
    # 2. Run K-Means cluster assignment
    model_path = os.path.join(utils.MODEL_DIR, "segmentation_model.pkl")
    if os.path.exists(model_path):
        seg_pack = joblib.load(model_path)
        scaler = seg_pack["scaler"]
        kmeans = seg_pack["kmeans"]
        cluster_names = seg_pack["cluster_names"]
        
        # Scale & Predict
        features_to_scale = df_rfm[['recency_days', 'order_count', 'total_spend']]
        scaled_feats = scaler.transform(features_to_scale)
        clusters = kmeans.predict(scaled_feats)
        df_rfm['cluster_id'] = clusters
        df_rfm['ml_cluster'] = df_rfm['cluster_id'].map(cluster_names)
    else:
        df_rfm['ml_cluster'] = "Standard Segment"
        
    # Toggle view modes
    seg_type = st.radio("Choose Segmentation System", ["Business Rule Segmentation", "ML K-Means Clustering"], horizontal=True)
    
    segment_col = 'business_segment' if seg_type == "Business Rule Segmentation" else 'ml_cluster'
    
    # Visualizations
    col_chart_1, col_chart_2 = st.columns(2)
    
    with col_chart_1:
        st.markdown(f"#### 🍰 Segment Distribution ({seg_type})")
        segment_counts = df_rfm[segment_col].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Volume']
        
        fig_pie = px.pie(
            segment_counts, values='Volume', names='Segment', hole=0.4,
            template="plotly_white", color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart_2:
        st.markdown("#### 💰 Average Monetary ($) Value per Segment")
        avg_spend = df_rfm.groupby(segment_col)['total_spend'].mean().reset_index()
        avg_spend.columns = ['Segment', 'Avg Spend']
        avg_spend = avg_spend.sort_values(by='Avg Spend', ascending=False)
        
        fig_bar = px.bar(
            avg_spend, x='Segment', y='Avg Spend', color='Segment',
            template="plotly_white", color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    # Extra 3D scatter chart for ML K-Means
    if seg_type == "ML K-Means Clustering" and os.path.exists(model_path):
        st.markdown("#### 🌌 3D RFM Clusters Visualization")
        fig_3d = px.scatter_3d(
            df_rfm.sample(n=1000, random_state=42), # sample to keep loading extremely fast
            x='recency_days', y='order_count', z='total_spend',
            color='ml_cluster', opacity=0.8,
            title="RFM Customer Clusters",
            labels={'recency_days': 'Recency (Days)', 'order_count': 'Order Count', 'total_spend': 'Total Spending ($)'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_3d.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=450)
        st.plotly_chart(fig_3d, use_container_width=True)
        
    # Table details
    st.markdown("### 📋 Segmented Customers Database")
    
    # Filter table by segment
    all_segments = sorted(df_rfm[segment_col].unique())
    selected_table_seg = st.selectbox("Filter table by Segment", ["All Segments"] + all_segments)
    
    table_df = df_rfm[['customer_id', 'name', 'city', 'loyalty_status', 'clv', 'recency_days', 'order_count', 'total_spend', segment_col]]
    if selected_table_seg != "All Segments":
        table_df = table_df[table_df[segment_col] == selected_table_seg]
        
    st.dataframe(table_df.head(100), use_container_width=True)
    st.write(f"Showing up to 100 rows. Total rows matched: {len(table_df)}")
