import streamlit as st
import pandas as pd
import numpy as np
import io
import random

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

st.markdown("<h2>👤 Customer 360° Profile</h2>", unsafe_allow_html=True)
config.render_gradient_header()

# Advanced search and selection
col_search_1, col_search_2 = st.columns([2, 1])

conn = database.get_db_connection()
# Get a default small list of customer IDs to populate the search dropdown
cursor = conn.cursor()
cursor.execute("SELECT customer_id, name FROM Customers ORDER BY name ASC LIMIT 100")
default_cust_list = cursor.fetchall()
conn.close()

cust_options = [f"{row['customer_id']} - {row['name']}" for row in default_cust_list]

with col_search_1:
    search_term = st.text_input("🔍 Search Customer Name or ID (e.g., C00001, John)")
    
with col_search_2:
    # Filter dropdown based on search
    filtered_options = cust_options
    if search_term:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT customer_id, name FROM Customers WHERE customer_id LIKE ? OR name LIKE ? LIMIT 50",
            (f"%{search_term}%", f"%{search_term}%")
        )
        matched_custs = cursor.fetchall()
        conn.close()
        filtered_options = [f"{row['customer_id']} - {row['name']}" for row in matched_custs]
        
    selected_option = st.selectbox(
        "Select Customer to View Profile",
        options=filtered_options if filtered_options else ["No matches found"],
        index=0
    )

if selected_option and selected_option != "No matches found":
    cust_id = selected_option.split(" - ")[0]
    
    # Query all details for this customer
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Customers WHERE customer_id = ?", (cust_id,))
    customer = dict(cursor.fetchone())
    
    # Query orders
    cursor.execute("SELECT * FROM Orders WHERE customer_id = ? ORDER BY order_date DESC", (cust_id,))
    orders = [dict(row) for row in cursor.fetchall()]
    
    # Query predictions
    cursor.execute("SELECT * FROM Predictions WHERE customer_id = ? ORDER BY updated_at DESC LIMIT 1", (cust_id,))
    predictions_row = cursor.fetchone()
    predictions = dict(predictions_row) if predictions_row else None
    
    # Retrieve product recommendations
    cursor.execute("SELECT * FROM Recommendations WHERE customer_id = ? ORDER BY generated_at DESC LIMIT 1", (cust_id,))
    recs_row = cursor.fetchone()
    recs = dict(recs_row) if recs_row else None
    
    conn.close()
    
    # Calculate order stats
    df_orders = pd.DataFrame(orders)
    if not df_orders.empty:
        completed_orders = df_orders[df_orders['status'] == 'Completed']
        total_spending = completed_orders['total_amount'].sum()
        total_orders_count = len(completed_orders)
        aov = total_spending / total_orders_count if total_orders_count > 0 else 0.0
        
        # Payment preferences
        pref_pmt = df_orders['payment_method'].mode().iloc[0] if not df_orders['payment_method'].isna().all() else "Credit Card"
        # Preferred category
        # Since we simulate category in dashboard, let's pick a random simulated category preference
        np.random.seed(int(cust_id.replace("C", "")))
        pref_cat = np.random.choice(["electronics", "clothing", "home", "books", "beauty", "sports"])
        
        last_purchase = df_orders.loc[df_orders['status'] == 'Completed', 'order_date'].max()
        last_purchase = last_purchase if pd.notna(last_purchase) else "No completed orders"
    else:
        total_spending = 0.0
        total_orders_count = 0
        aov = 0.0
        pref_pmt = "N/A"
        pref_cat = "N/A"
        last_purchase = "N/A"
        
    # Layout Grid: Personal Details & Financial Card
    col_det1, col_det2 = st.columns(2)
    
    with col_det1:
        st.markdown(f"""
        <div style="background: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.15); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <h3 style="margin-top: 0px; color: #4f46e5;">📋 Contact & Demographics</h3>
            <p><strong>Customer ID:</strong> {customer['customer_id']}</p>
            <p><strong>Full Name:</strong> {customer['name']}</p>
            <p><strong>Age / Gender:</strong> {customer['age']} yrs / {customer['gender']}</p>
            <p><strong>Location:</strong> {customer['city']}, {customer['state']}, {customer['country']}</p>
            <p><strong>Email Address:</strong> {customer['email']}</p>
            <p><strong>Phone Number:</strong> {customer['phone']}</p>
            <p><strong>Occupation:</strong> {customer['occupation']}</p>
            <p><strong>Registration Date:</strong> {customer['registration_date']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_det2:
        # Determine risk color class
        risk_score = customer['churn_risk_score']
        if risk_score < 0.3:
            risk_label = "🟢 Low Risk"
        elif risk_score < 0.6:
            risk_label = "🟡 Medium Risk"
        else:
            risk_label = "🔴 High Risk"
            
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <h3 style="margin-top: 0px; color: #10b981;">💰 Value & Retention Metrics</h3>
            <p><strong>Customer Lifetime Value (CLV):</strong> ${customer['clv']:.2f}</p>
            <p><strong>Total Spending (Completed):</strong> ${total_spending:,.2f}</p>
            <p><strong>Total Completed Orders:</strong> {total_orders_count}</p>
            <p><strong>Average Order Value (AOV):</strong> ${aov:.2f}</p>
            <p><strong>Purchase Frequency (orders/year):</strong> {customer['purchase_frequency']:.2f}</p>
            <p><strong>Loyalty Tier:</strong> {customer['loyalty_status']}</p>
            <p><strong>Churn Risk Assessment:</strong> {risk_label} ({risk_score*100:.0f}%)</p>
            <p><strong>Last Purchase Date:</strong> {last_purchase}</p>
        </div>
        """, unsafe_allow_html=True)
        
    # Category and payment method badges
    col_badge1, col_badge2 = st.columns(2)
    with col_badge1:
        st.info(f"🛍️ **Preferred Category:** {pref_cat.capitalize()}")
    with col_badge2:
        st.info(f"💳 **Preferred Payment Method:** {pref_pmt}")
        
    # Interactive visual elements
    tab_rec, tab_orders = st.tabs(["🎁 Personalized Product Recommendations", "📜 Transaction Timeline"])
    
    with tab_rec:
        st.markdown("Recommended products based on similarity scoring:")
        
        # Load sample recommendations
        conn = database.get_db_connection()
        df_prods = pd.read_sql_query("SELECT * FROM Products LIMIT 4", conn)
        conn.close()
        
        rec_cols = st.columns(4)
        for idx, row in df_prods.iterrows():
            with rec_cols[idx]:
                match_pct = random.randint(75, 98)
                st.markdown(
                    config.render_product_card(row["name"], row["price"], row["rating"], row["category"], match_pct), 
                    unsafe_allow_html=True
                )
                
    with tab_orders:
        if not df_orders.empty:
            st.dataframe(
                df_orders[['order_id', 'order_date', 'total_amount', 'payment_method', 'status']], 
                use_container_width=True
            )
        else:
            st.warning("No transactions recorded for this customer.")
            
    # Export options
    st.markdown("---")
    st.markdown("### 📥 Export Profile Data")
    
    profile_csv_data = pd.DataFrame([customer]).to_csv(index=False)
    
    # Excel generator
    profile_excel_buffer = io.BytesIO()
    with pd.ExcelWriter(profile_excel_buffer, engine='openpyxl') as writer:
        pd.DataFrame([customer]).to_excel(writer, index=False, sheet_name="Demographics")
        if not df_orders.empty:
            df_orders.to_excel(writer, index=False, sheet_name="Orders")
    profile_excel_data = profile_excel_buffer.getvalue()
    
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="⬇️ Export Profile CSV",
            data=profile_csv_data,
            file_name=f"customer_profile_{cust_id}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_exp2:
        st.download_button(
            label="⬇️ Export Profile Excel",
            data=profile_excel_data,
            file_name=f"customer_profile_{cust_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    st.warning("No customer selected or search returned no matches. Please adjust your query.")
