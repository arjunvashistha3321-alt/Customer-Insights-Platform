import streamlit as st
import pandas as pd
import io
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

st.markdown("<h2>📋 Report Export Center</h2>", unsafe_allow_html=True)
config.render_gradient_header()

st.write("Generate and download structured CSV, Excel sheets, or fully formatted PDF summary documents for key business cohorts.")

# Report Types Selection
report_type = st.selectbox(
    "Choose Report Subject",
    [
        "Customer Demographics & Metrics",
        "Revenue & Billing Transaction Logs",
        "Product Performance & Ratings",
        "Churn Cohort & Risk Factors",
        "Analytics Summary"
    ]
)

# Render configurations and download triggers
if st.button("🔧 Compile Report Files", type="primary", use_container_width=True):
    conn = database.get_db_connection()
    
    # Query data depending on selection
    if report_type == "Customer Demographics & Metrics":
        df_report = pd.read_sql_query("SELECT customer_id, name, age, gender, loyalty_status, clv, churn_risk_score FROM Customers LIMIT 500", conn)
        title = "Customer Demographics & Metrics Report"
        headers = ["ID", "Name", "Age", "Gender", "Loyalty", "CLV ($)", "Churn Risk"]
        rows = df_report.values.tolist()
        summary = "This report compiles demographical traits and customer value metrics for 500 sampled customers."
        
    elif report_type == "Revenue & Billing Transaction Logs":
        df_report = pd.read_sql_query("SELECT order_id, customer_id, order_date, total_amount, payment_method, status FROM Orders LIMIT 500", conn)
        title = "Revenue & Billing Transaction Logs"
        headers = ["Order ID", "Customer ID", "Date", "Amount ($)", "Method", "Status"]
        rows = df_report.values.tolist()
        summary = "This transaction log report outlines order billing status, totals, and method distributions."
        
    elif report_type == "Product Performance & Ratings":
        df_report = pd.read_sql_query("SELECT product_id, name, price, category, rating FROM Products", conn)
        title = "Product Performance & Ratings Report"
        headers = ["Prod ID", "Product Name", "Price ($)", "Category", "Rating"]
        rows = df_report.values.tolist()
        summary = "Comprehensive matrix containing items inventory pricing lists, categories, and average feedback ratings."
        
    elif report_type == "Churn Cohort & Risk Factors":
        df_report = pd.read_sql_query("SELECT customer_id, name, loyalty_status, clv, churn_risk_score FROM Customers WHERE churn_risk_score > 0.5 ORDER BY churn_risk_score DESC LIMIT 200", conn)
        title = "At-Risk Customer Cohort Report"
        headers = ["ID", "Customer Name", "Loyalty", "CLV ($)", "Churn Score"]
        rows = df_report.values.tolist()
        summary = "High churn risk audit list detailing customers with risk probability higher than 50% sorted by vulnerability."
        
    else: # Analytics Summary
        df_report = pd.read_sql_query("SELECT loyalty_status, AVG(clv) as avg_clv, AVG(churn_risk_score) as avg_churn FROM Customers GROUP BY loyalty_status", conn)
        title = "Analytics Segment Summary"
        headers = ["Loyalty Status", "Avg CLV ($)", "Avg Churn Risk"]
        # Formats
        df_report['avg_clv'] = df_report['avg_clv'].round(2)
        df_report['avg_churn'] = (df_report['avg_churn'] * 100).round(2).astype(str) + "%"
        rows = df_report.values.tolist()
        summary = "Consolidated analytics aggregation comparing loyalty level values and churn patterns."
        
    conn.close()
    
    st.session_state["report_ready"] = True
    st.session_state["report_df"] = df_report
    st.session_state["report_title"] = title
    st.session_state["report_headers"] = headers
    st.session_state["report_rows"] = rows
    st.session_state["report_summary"] = summary
    st.session_state["report_file_tag"] = report_type.lower().replace(" ", "_").replace("&", "and")

if st.session_state.get("report_ready"):
    df_report = st.session_state["report_df"]
    title = st.session_state["report_title"]
    headers = st.session_state["report_headers"]
    rows = st.session_state["report_rows"]
    summary = st.session_state["report_summary"]
    file_tag = st.session_state["report_file_tag"]
    
    st.success("✅ Report files compiled and ready!")
    st.dataframe(df_report.head(15), use_container_width=True)
    st.write(f"Previewing first 15 records. Total compiled: {len(df_report)}")
    
    # 1. Excel Generation
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_report.to_excel(writer, index=False, sheet_name="DataSheet")
    excel_data = excel_buffer.getvalue()
    
    # 2. CSV Generation
    csv_data = df_report.to_csv(index=False)
    
    # 3. PDF Generation
    pdf_filename = f"{file_tag}_report.pdf"
    with st.spinner("Rendering styled PDF report..."):
        pdf_path = utils.generate_pdf_report(pdf_filename, title, headers, rows, summary)
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
            
    # Record metadata of the generated report in SQLite Reports database
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Reports (name, type, created_by, file_path) VALUES (?, ?, ?, ?)",
        (title, "PDF", st.session_state["username"], pdf_path)
    )
    conn.commit()
    conn.close()
    
    # Display download options
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    
    with col_dl1:
        st.download_button(
            label="⬇️ Download Report (CSV)",
            data=csv_data,
            file_name=f"{file_tag}_report.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with col_dl2:
        st.download_button(
            label="⬇️ Download Report (Excel)",
            data=excel_data,
            file_name=f"{file_tag}_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_dl3:
        st.download_button(
            label="⬇️ Download Report (PDF)",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True
        )
