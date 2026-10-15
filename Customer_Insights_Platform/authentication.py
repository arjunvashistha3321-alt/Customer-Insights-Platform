import bcrypt
import streamlit as st
import database

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def login_user(username, password):
    """Attempts to log in a user and set session state."""
    user = database.get_user(username)
    if user and verify_password(password, user["password_hash"]):
        st.session_state["logged_in"] = True
        st.session_state["username"] = user["username"]
        st.session_state["role"] = user["role"]
        st.session_state["email"] = user["email"]
        database.log_activity(username, "User logged in.")
        return True
    return False

def register_user(username, email, password, role):
    """Registers a new user into the database."""
    hashed = hash_password(password)
    # Check if user already exists
    if database.get_user(username) is not None:
        return False, "Username already exists."
    success = database.add_user(username, email, hashed, role)
    if success:
        return True, "User registered successfully."
    else:
        return False, "Failed to create user account."

def logout_user():
    """Logs out the user and clears session state."""
    if "username" in st.session_state:
        database.log_activity(st.session_state["username"], "User logged out.")
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["email"] = None
    # Force rerun to update views
    st.rerun()

def check_login():
    """
    Checks if a user is logged in. 
    If not, displays a message and halts execution.
    Can be used at the top of any subpage.
    """
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("🔒 Access Denied. Please log in first.")
        # Render a simple button to go back to the home/login page
        if st.button("Go to Login Page"):
            st.switch_page("app.py")
        st.stop()
        return False
    return True
