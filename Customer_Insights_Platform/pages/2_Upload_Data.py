import streamlit as st
import pandas as pd
import io

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

st.markdown("<h2>📂 Data Upload & Cleaning</h2>", unsafe_allow_html=True)
config.render_gradient_header()

st.write("Upload raw sales, order, or customer data sheets (CSV or Excel) to evaluate structures, check completeness, and apply automated formatting.")

uploaded_file = st.file_uploader("Select data file...", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    # Read the file
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success("🎉 File uploaded successfully!")
        
        # Details layout
        st.markdown("### 📊 Raw Dataset Profile")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            config.render_kpi_card("Number of Rows", f"{df.shape[0]:,}", card_type="primary")
        with col2:
            config.render_kpi_card("Number of Columns", f"{df.shape[1]}", card_type="info")
        with col3:
            total_missing = df.isna().sum().sum()
            config.render_kpi_card("Missing Values", f"{total_missing:,}", card_type="warning" if total_missing > 0 else "success")
        with col4:
            total_dups = df.duplicated().sum()
            config.render_kpi_card("Duplicate Rows", f"{total_dups:,}", card_type="danger" if total_dups > 0 else "success")
            
        # Detail Tabs
        tab_preview, tab_types, tab_missing, tab_stats = st.tabs([
            "📋 Data Preview", 
            "🗂️ Data Types", 
            "❓ Missing Details", 
            "📈 Summary Statistics"
        ])
        
        with tab_preview:
            st.dataframe(df.head(50), use_container_width=True)
            
        with tab_types:
            st.dataframe(df.dtypes.astype(str).to_frame(name="Data Type"), use_container_width=True)
            
        with tab_missing:
            missing_df = df.isna().sum().to_frame(name="Missing Counts")
            missing_df["Missing Percentage (%)"] = round((missing_df["Missing Counts"] / len(df)) * 100, 2)
            st.dataframe(missing_df[missing_df["Missing Counts"] > 0], use_container_width=True)
            if total_missing == 0:
                st.info("No missing values found in the dataset.")
                
        with tab_stats:
            st.dataframe(df.describe(include='all').fillna('-'), use_container_width=True)
            
        # Data Cleaning Module
        st.markdown("---")
        st.markdown("### 🛠️ Data Cleaning Operations")
        
        col_clean_1, col_clean_2 = st.columns(2)
        
        with col_clean_1:
            st.write("Configure the operations to run on your dataset:")
            opt_duplicates = st.checkbox("Remove Duplicate Records", value=True)
            opt_missing = st.checkbox("Fill Missing Values (Numeric: Median, Categorical: Mode)", value=True)
            opt_cols = st.checkbox("Standardize Column Headers (lowercase, strip, snake_case)", value=True)
            
        with col_clean_2:
            st.write("Action Hub:")
            if st.button("🧼 Run Data Cleanse", type="primary", use_container_width=True):
                with st.spinner("Processing dataset..."):
                    cleaned_df = utils.clean_uploaded_dataset(
                        df, 
                        remove_dups=opt_duplicates, 
                        fill_na=opt_missing, 
                        standardize_cols=opt_cols
                    )
                    st.session_state["cleaned_df"] = cleaned_df
                    database.log_activity(st.session_state['username'], f"Cleaned uploaded data file: {uploaded_file.name}")
                    st.success("Dataset cleaned successfully!")
                    
        # Cleaned dataset preview
        if "cleaned_df" in st.session_state:
            cleaned_df = st.session_state["cleaned_df"]
            st.markdown("### 🌟 Cleaned Dataset Preview")
            st.dataframe(cleaned_df.head(20), use_container_width=True)
            
            # Export controls
            st.write("Export clean files:")
            
            # Convert to CSV buffer
            csv_buffer = io.StringIO()
            cleaned_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Convert to Excel buffer
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                cleaned_df.to_excel(writer, index=False)
            excel_data = excel_buffer.getvalue()
            
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label="⬇️ Download Cleaned CSV",
                    data=csv_data,
                    file_name="cleaned_dataset.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with dl_col2:
                st.download_button(
                    label="⬇️ Download Cleaned Excel",
                    data=excel_data,
                    file_name="cleaned_dataset.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    except Exception as e:
        st.error(f"Failed to read/process the uploaded file. Error: {str(e)}")
        database.log_activity(st.session_state['username'], f"Error uploading data: {str(e)}")
else:
    st.info("Please upload a file using the picker above to begin.")
