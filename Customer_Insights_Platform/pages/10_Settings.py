import streamlit as st
import pandas as pd
import os

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

st.markdown("<h2>⚙️ Platform Settings & Diagnostics</h2>", unsafe_allow_html=True)
config.render_gradient_header()

tab_acc, tab_diag = st.tabs(["👤 Profile & Account", "🩺 System Health & Diagnostics"])

# --- TAB 1: PROFILE ACCOUNT ---
with tab_acc:
    st.markdown("### 👤 Update Account Details")
    
    user = database.get_user(st.session_state["username"])
    st.write(f"Username: **{user['username']}**")
    st.write(f"Permission Access Role: {config.render_badge(user['role'])}", unsafe_allow_html=True)
    st.write(f"Registered Email: **{user['email']}**")
    
    st.markdown("#### 🔒 Reset password credentials")
    curr_pass = st.text_input("Current password", type="password", key="set_curr_pass")
    new_pass = st.text_input("New password", type="password", key="set_new_pass")
    confirm_pass = st.text_input("Confirm new password", type="password", key="set_confirm_pass")
    
    if st.button("Update Security Credentials", type="primary"):
        if not curr_pass or not new_pass or not confirm_pass:
            st.error("Please fill in all details.")
        elif new_pass != confirm_pass:
            st.error("New passwords do not match.")
        else:
            # Verify current password
            if authentication.verify_password(curr_pass, user["password_hash"]):
                new_hashed = authentication.hash_password(new_pass)
                success = database.update_password(st.session_state["username"], new_hashed)
                if success:
                    st.success("Security credentials updated successfully!")
                else:
                    st.error("Error updating credentials in SQLite.")
            else:
                st.error("Incorrect current password.")

# --- TAB 2: HEALTH DIAGNOSTICS ---
with tab_diag:
    st.markdown("### 🩺 Diagnostics Health Check")
    
    # Active Files Check
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "customer_insights.db")
    
    db_size = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0.0
    
    st.write(f"🗄️ **Database Status:** Connected")
    st.write(f"📁 **Database Size:** {db_size:.2f} MB")
    
    # Get table counts
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    counts = {}
    for table in ["Customers", "Orders", "Products", "Transactions", "Predictions", "Recommendations", "Users"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except Exception:
            counts[table] = 0
            
    conn.close()
    
    st.markdown("#### 📊 SQLite Database Row Volumes")
    df_counts = pd.DataFrame(counts.items(), columns=["Table Schema", "Active Rows Count"])
    st.table(df_counts)
    
    st.markdown("#### 🧠 Machine Learning Model Artifacts")
    models = ["churn_model.pkl", "clv_model.pkl", "segmentation_model.pkl", "recommendation_model.pkl"]
    model_rows = []
    
    for model in models:
        m_path = os.path.join(utils.MODEL_DIR, model)
        exists = os.path.exists(m_path)
        m_size = os.path.getsize(m_path) / 1024 if exists else 0.0
        model_rows.append({
            "Model Artifact": model,
            "Found": "🟢 Available" if exists else "🔴 Missing",
            "File Size": f"{m_size:.1f} KB" if exists else "N/A"
        })
        
    df_models = pd.DataFrame(model_rows)
    st.dataframe(df_models, use_container_width=True)
