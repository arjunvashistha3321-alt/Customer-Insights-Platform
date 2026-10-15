import streamlit as st
import pandas as pd
import os

import database
import authentication
import utils
import config

# Route Guard: Check Login & Role Permissions
if not authentication.check_login():
    st.stop()

if st.session_state.get("role") != "Admin":
    st.error("🚫 Access Denied. The Admin Panel is restricted to System Administrators only.")
    if st.button("Return to Dashboard"):
        st.switch_page("pages/1_Dashboard.py")
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

st.markdown("<h2>🛡️ System Administration</h2>", unsafe_allow_html=True)
config.render_gradient_header()

tab_users, tab_db_ops, tab_audit = st.tabs([
    "👥 User Management", 
    "💾 Database Operations", 
    "📜 Activity Audit Logs"
])

# --- TAB 1: USER MANAGEMENT ---
with tab_users:
    st.markdown("### 👥 Manage User Accounts & Permissions")
    
    users = database.get_all_users()
    df_users = pd.DataFrame(users)
    st.dataframe(df_users, use_container_width=True)
    
    col_add, col_edit = st.columns(2)
    
    with col_add:
        st.markdown("#### ➕ Add New User Account")
        new_username = st.text_input("Username", key="admin_add_username")
        new_email = st.text_input("Email", key="admin_add_email")
        new_password = st.text_input("Password", type="password", key="admin_add_password")
        new_role = st.selectbox("Role Permission", ["Analyst", "Manager", "Admin"], key="admin_add_role")
        
        if st.button("Create User Account", use_container_width=True):
            if not new_username or not new_email or not new_password:
                st.error("Please fill in all details.")
            else:
                success, msg = authentication.register_user(new_username, new_email, new_password, new_role)
                if success:
                    st.success("User account created successfully!")
                    st.rerun()
                else:
                    st.error(msg)
                    
    with col_edit:
        st.markdown("#### ✏️ Edit or Delete User")
        edit_user = st.selectbox("Select User", [u["username"] for u in users if u["username"] != st.session_state["username"]])
        edit_role = st.selectbox("New Role Permission", ["Analyst", "Manager", "Admin"], key="admin_edit_role")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Update Role", use_container_width=True):
                if edit_user:
                    database.update_user_role(edit_user, edit_role, st.session_state["username"])
                    st.success(f"Updated role of {edit_user} to {edit_role}!")
                    st.rerun()
        with col_btn2:
            if st.button("Delete User Account", type="primary", use_container_width=True):
                if edit_user:
                    database.delete_user(edit_user, st.session_state["username"])
                    st.success(f"Deleted user account: {edit_user}!")
                    st.rerun()

# --- TAB 2: DATABASE OPERATIONS ---
with tab_db_ops:
    st.markdown("### 💾 Database Maintenance Operations")
    
    db_col1, db_col2 = st.columns(2)
    
    with db_col1:
        st.markdown("#### 📦 Create Database Backup")
        st.write("Save a copies of your active sqlite database file to local storage directory backups/.")
        if st.button("Backup sqlite Database", type="primary", use_container_width=True):
            path, err = database.backup_database()
            if err:
                st.error(f"Backup failed: {err}")
            else:
                st.success(f"Backup created successfully at: {path}")
                database.log_activity(st.session_state["username"], f"Database backed up to {os.path.basename(path)}.")
                
    with db_col2:
        st.markdown("#### ⚠️ Reset and Seed Database")
        st.write("WARNING: This will drop and re-seed the SQLite database with 10k customers and 50k orders. Models will be re-trained.")
        
        confirm_reset = st.checkbox("Confirm database reset")
        if st.button("Reset Database", disabled=(not confirm_reset), use_container_width=True):
            with st.spinner("Deleting tables and generating new mock datasets..."):
                # Clean and rebuild
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS Customers")
                cursor.execute("DROP TABLE IF EXISTS Orders")
                cursor.execute("DROP TABLE IF EXISTS Products")
                cursor.execute("DROP TABLE IF EXISTS Transactions")
                cursor.execute("DROP TABLE IF EXISTS Predictions")
                cursor.execute("DROP TABLE IF EXISTS Recommendations")
                cursor.execute("DROP TABLE IF EXISTS Reports")
                conn.commit()
                conn.close()
                
                database.init_db()
                utils.generate_and_seed_data()
                utils.train_ml_models()
                
            st.success("Database successfully reset and re-seeded!")
            database.log_activity(st.session_state["username"], "Database wiped and re-seeded.")
            st.rerun()

# --- TAB 3: AUDIT TRAILS ---
with tab_audit:
    st.markdown("### 📜 System Activity Audit Trail Logs")
    logs = database.get_activity_logs(100)
    df_logs = pd.DataFrame(logs)
    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No activity logs recorded.")
