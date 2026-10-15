import streamlit as st
import os
import database
import authentication
import utils
import config

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "email" not in st.session_state:
    st.session_state["email"] = None

# Configure page layout and load custom styles
config.check_session_active()

# Initialize DB, generate data & train models on first launch
database.init_db()
if not database.is_db_seeded():
    with st.spinner("⚙️ Initializing database tables, generating 10,000 customers & training machine learning models... Please wait."):
        # Seeding relational tables
        utils.generate_and_seed_data()
        
        # Training baseline classifiers & regressors
        utils.train_ml_models()
        
        # Seed default credentials
        authentication.register_user("admin", "admin@platform.com", "adminpassword", "Admin")
        authentication.register_user("manager", "manager@platform.com", "managerpassword", "Manager")
        authentication.register_user("analyst", "analyst@platform.com", "analystpassword", "Analyst")
        
    st.toast("🎉 Database successfully seeded with 10k customers and models trained!", icon="🔥")

# If logged in, redirect automatically to Dashboard
if st.session_state["logged_in"]:
    st.switch_page("pages/1_Dashboard.py")

# Layout: Brand Presentation
st.markdown("<h1 style='text-align: center; color: #4f46e5;'>📊 Insights AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.15rem;'>AI-Powered Customer Insights Platform</p>", unsafe_allow_html=True)
config.render_gradient_header()

# Centered Login Card Layout
col1, col2, col3 = st.columns([1, 1.5, 1])

with col2:
    tab1, tab2, tab3 = st.tabs(["🔑 Sign In", "📝 Sign Up", "❓ Forgot Password"])
    
    # 1. SIGN IN TAB
    with tab1:
        st.markdown("<h3 style='margin-bottom: 20px;'>Welcome Back</h3>", unsafe_allow_html=True)
        login_user = st.text_input("Username", key="login_username")
        login_pass = st.text_input("Password", type="password", key="login_password")
        
        # Display Credentials Tips for Testing
        with st.expander("💡 Demo Logins & Access Credentials"):
            st.markdown("""
            *   **Admin Access:** `admin` / `adminpassword`
            *   **Manager Access:** `manager` / `managerpassword`
            *   **Analyst Access:** `analyst` / `analystpassword`
            """)
            
        if st.button("Login", type="primary", use_container_width=True):
            if not login_user or not login_pass:
                st.error("Please enter both username and password.")
            else:
                success = authentication.login_user(login_user, login_pass)
                if success:
                    st.success("Login successful! Redirecting...")
                    st.switch_page("pages/1_Dashboard.py")
                else:
                    st.error("Invalid username or password. Please try again.")
                    
    # 2. SIGN UP TAB
    with tab2:
        st.markdown("<h3 style='margin-bottom: 20px;'>Create Analyst Account</h3>", unsafe_allow_html=True)
        reg_user = st.text_input("Choose Username", key="reg_username")
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_pass = st.text_input("Choose Password", type="password", key="reg_password")
        reg_role = st.selectbox("Job Role / Permissions", ["Analyst", "Manager", "Admin"])
        
        if st.button("Register Account", use_container_width=True):
            if not reg_user or not reg_email or not reg_pass:
                st.error("Please fill in all the registration fields.")
            elif "@" not in reg_email or "." not in reg_email:
                st.error("Please enter a valid email address.")
            else:
                success, msg = authentication.register_user(reg_user, reg_email, reg_pass, reg_role)
                if success:
                    st.success(f"Registration successful! Please sign in using the 'Sign In' tab.")
                else:
                    st.error(msg)
                    
    # 3. FORGOT PASSWORD TAB
    with tab3:
        st.markdown("<h3 style='margin-bottom: 20px;'>Reset Password</h3>", unsafe_allow_html=True)
        forgot_user = st.text_input("Enter your Username", key="forgot_username")
        new_pass = st.text_input("Enter new Password", type="password", key="new_password")
        confirm_pass = st.text_input("Confirm new Password", type="password", key="confirm_password")
        
        if st.button("Reset Password", use_container_width=True):
            if not forgot_user or not new_pass or not confirm_pass:
                st.error("Please fill in all the fields.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                user = database.get_user(forgot_user)
                if user is None:
                    st.error("Username not found in system database.")
                else:
                    hashed = authentication.hash_password(new_pass)
                    success = database.update_password(forgot_user, hashed)
                    if success:
                        st.success("Password reset successfully! Please sign in with your new credentials.")
                    else:
                        st.error("An error occurred. Password could not be updated.")

# Decorative bottom details
st.markdown("<br><br><p style='text-align: center; color: #94a3b8; font-size: 0.8rem;'>Insights AI v1.0.0 © 2026. Made with Streamlit.</p>", unsafe_allow_html=True)
