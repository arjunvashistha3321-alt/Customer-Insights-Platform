import os
import streamlit as st

# Color Palette Config
COLORS = {
    "primary": "#4f46e5",
    "primary_gradient": "linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#06b6d4",
    "dark_bg": "#0f172a",
    "light_bg": "#f8fafc",
}

def get_css_path():
    """Returns the absolute path to the CSS style sheet."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "assets", "css", "style.css")

def inject_custom_css():
    """Injects custom CSS styling into the Streamlit app page."""
    css_path = get_css_path()
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS style file not found.")

def render_gradient_header():
    """Renders the top decorative colored banner gradient."""
    st.markdown('<div class="gradient-header"></div>', unsafe_allow_html=True)

def render_kpi_card(label, value, trend=None, is_up=True, card_type="primary"):
    """
    Renders a premium stylized KPI card.
    card_type: 'primary', 'success', 'warning', 'danger', 'info'
    """
    trend_html = ""
    if trend is not None:
        trend_class = "trend-up" if is_up else "trend-down"
        arrow = "▲" if is_up else "▼"
        trend_html = f'<div class="kpi-trend {trend_class}">{arrow} {trend}</div>'
        
    card_html = f"""
    <div class="kpi-card kpi-{card_type}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {trend_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_badge(text, role_type="analyst"):
    """Renders a customized pill badge for user roles."""
    role_type = role_type.lower()
    if role_type == "admin":
        badge_class = "badge-admin"
    elif role_type == "manager":
        badge_class = "badge-manager"
    else:
        badge_class = "badge-analyst"
        
    return f'<span class="badge {badge_class}">{text}</span>'

def render_product_card(name, price, rating, category, match_score=None):
    """Renders a single recommended product card."""
    match_html = ""
    if match_score is not None:
        match_html = f'<div class="rec-footer"><span>Match Score:</span> <strong>{match_score}%</strong></div>'
        
    stars = "★" * int(round(rating)) + "☆" * (5 - int(round(rating)))
    
    # Simple icons representing categories
    icons = {
        "electronics": "🔌",
        "clothing": "👕",
        "home": "🏠",
        "books": "📚",
        "beauty": "💄",
        "sports": "⚽"
    }
    cat_icon = icons.get(category.lower(), "📦")
    
    card_html = f"""
    <div class="rec-card">
        <div class="rec-img-placeholder">{cat_icon}</div>
        <div class="rec-details">
            <div class="rec-title" title="{name}">{name}</div>
            <div class="rec-price">${price:.2f}</div>
            <div class="rec-footer" style="margin-bottom: 6px;">
                <span style="color: #f59e0b;">{stars}</span>
                <span style="text-transform: capitalize;">{category}</span>
            </div>
            {match_html}
        </div>
    </div>
    """
    return card_html

def check_session_active():
    """Initializes basic Streamlit states and checks user session state."""
    # Setup page configurations
    st.set_page_config(
        page_title="AI-Powered Customer Insights Platform",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_custom_css()
