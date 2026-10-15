import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

st.markdown("<h2>🧠 Machine Learning: Customer Churn Prediction</h2>", unsafe_allow_html=True)
config.render_gradient_header()

st.write("Leverage predictive Random Forest models to evaluate individual customer churn probabilities and explore cohort risk distributions.")

# Verification that model is trained
model_path = os.path.join(utils.MODEL_DIR, "churn_model.pkl")
if not os.path.exists(model_path):
    st.warning("⚠️ Churn prediction model files are missing. Please wait, training models now...")
    with st.spinner("Training..."):
        utils.train_ml_models()
    st.success("Models trained successfully!")

# Tab Layout: Overview & Simulator
tab_overview, tab_simulator = st.tabs(["📊 Risk Overview (Cohort)", "🔮 Real-Time Risk Simulator"])

# --- TAB 1: COHORT OVERVIEW ---
with tab_overview:
    conn = database.get_db_connection()
    df_cust = pd.read_sql_query("SELECT customer_id, name, age, loyalty_status, churn_risk_score FROM Customers", conn)
    conn.close()
    
    if not df_cust.empty:
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown("#### 🚨 Churn Risk Level Breakdown")
            
            # Categorize risk levels
            def get_risk_label(score):
                if score < 0.3:
                    return "Low Risk (<30%)"
                elif score < 0.6:
                    return "Medium Risk (30%-60%)"
                else:
                    return "High Risk (>60%)"
                    
            df_cust['risk_level'] = df_cust['churn_risk_score'].apply(get_risk_label)
            risk_counts = df_cust['risk_level'].value_counts().reset_index()
            risk_counts.columns = ['Risk Level', 'Count']
            
            fig_risk = px.pie(
                risk_counts, values='Count', names='Risk Level',
                color='Risk Level',
                color_discrete_map={
                    "Low Risk (<30%)": "#10b981",
                    "Medium Risk (30%-60%)": "#f59e0b",
                    "High Risk (>60%)": "#ef4444"
                },
                template="plotly_white"
            )
            fig_risk.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
            st.plotly_chart(fig_risk, use_container_width=True)
            
        with col_c2:
            st.markdown("#### 🎯 Churn Risk by Loyalty Tier")
            loyalty_churn = df_cust.groupby('loyalty_status')['churn_risk_score'].mean().reset_index()
            loyalty_churn.columns = ['Loyalty Tier', 'Average Churn Risk']
            loyalty_churn['Average Churn Risk'] = round(loyalty_churn['Average Churn Risk'] * 100, 2)
            
            fig_loyalty = px.bar(
                loyalty_churn, x='Loyalty Tier', y='Average Churn Risk', color='Loyalty Tier',
                template="plotly_white",
                color_discrete_sequence=['#4f46e5', '#3b82f6', '#10b981', '#f59e0b']
            )
            fig_loyalty.update_layout(margin=dict(l=20, r=20, t=10, b=20), height=300, showlegend=False)
            st.plotly_chart(fig_loyalty, use_container_width=True)
            
        # Top 10 High Risk Customers Table
        st.markdown("#### ⚠️ High Churn Risk Cohort (Top 10)")
        df_high_risk = df_cust.sort_values(by='churn_risk_score', ascending=False).head(10)
        df_high_risk['churn_risk_score'] = (df_high_risk['churn_risk_score'] * 100).astype(str) + "%"
        st.dataframe(df_high_risk[['customer_id', 'name', 'loyalty_status', 'churn_risk_score']], use_container_width=True)
    else:
        st.info("No customer records found.")

# --- TAB 2: SIMULATOR ---
with tab_simulator:
    st.markdown("### 🔮 Customer Churn Risk Calculator")
    st.write("Input simulated attributes to test the model's prediction output.")
    
    col_sim_1, col_sim_2 = st.columns(2)
    
    with col_sim_1:
        sim_age = st.slider("Customer Age", 18, 80, 34)
        sim_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        sim_loyalty = st.selectbox("Loyalty status tier", ["Bronze", "Silver", "Gold", "Platinum"])
        sim_tenure = st.number_input("Customer Tenure (Days)", min_value=1, max_value=3000, value=365)
        
    with col_sim_2:
        sim_spend = st.number_input("Total Lifetime Spend ($)", min_value=0.0, value=250.0)
        sim_orders = st.number_input("Completed Orders Count", min_value=0, value=4)
        sim_aov = st.number_input("Average Order Value ($)", min_value=0.0, value=62.5)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔮 Calculate Churn Risk Probability", type="primary", use_container_width=True):
        # Prepare inputs
        cust_payload = {
            "age": sim_age,
            "gender": sim_gender,
            "loyalty_status": sim_loyalty,
            "total_spend": sim_spend,
            "order_count": sim_orders,
            "aov": sim_aov,
            "tenure_days": sim_tenure
        }
        
        with st.spinner("Processing ML prediction rules..."):
            res = utils.get_churn_prediction(cust_payload)
            clv_res = utils.get_clv_prediction(cust_payload)
            
        if "error" in res:
            st.error(res["error"])
        else:
            st.markdown("---")
            st.markdown("### 🎯 Calculation Output")
            
            # Displays
            res_col1, res_col2, res_col3 = st.columns(3)
            
            # Class definition
            predict_churn = res["prediction"] == 1
            status_text = "⚠️ Churn Risk" if predict_churn else "🟢 Retained"
            status_color = "danger" if predict_churn else "success"
            
            with res_col1:
                config.render_kpi_card(
                    "Prediction", 
                    status_text, 
                    trend=f"Confidence: {res['confidence_score']*100:.0f}%", 
                    is_up=(not predict_churn), 
                    card_type=status_color
                )
                
            with res_col2:
                config.render_kpi_card(
                    "Churn Probability", 
                    f"{res['churn_probability']*100:.1f}%", 
                    trend=f"Risk: {res['risk_level']}", 
                    is_up=(res['risk_level'] == 'Low'), 
                    card_type="warning" if res['risk_level'] == 'Medium' else ("danger" if res['risk_level'] == 'High' else "success")
                )
                
            with res_col3:
                predicted_clv = clv_res.get("clv_predicted", 0.0) if "error" not in clv_res else 0.0
                config.render_kpi_card(
                    "Predicted Future CLV", 
                    f"${predicted_clv:,.2f}", 
                    trend="Based on Value Model", 
                    is_up=True, 
                    card_type="success"
                )
                
            # Explanation
            st.markdown("#### 🔬 Model Explanation (Feature Importances)")
            st.write("Top parameters contributing to this customer's risk profile:")
            for feature, imp in res["explanations"]:
                percentage = imp * 100
                st.write(f"🔹 **{feature}**")
                st.progress(float(imp))
