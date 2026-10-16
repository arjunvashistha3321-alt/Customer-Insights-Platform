import os
import random
import sqlite3
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import database

# Initialize Faker
fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# --- 1. DATA GENERATION & SEEDING ---

def generate_and_seed_data():
    """Generates synthetic e-commerce data and seeds the SQLite database."""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Check if database tables already have customers, orders, and products
    cursor.execute("SELECT COUNT(*) FROM Customers")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
        
    print("Generating demo dataset (10,000 Customers, 300 Products, 50,000 Orders)...")
    
    # A. Generate Products (300 products)
    categories = ["electronics", "clothing", "home", "books", "beauty", "sports"]
    product_pool = {
        "electronics": ["Smartphone X", "Laptop Pro", "Wireless Earbuds", "Smart Watch", "4K TV", "Bluetooth Speaker", "Gaming Mouse", "Mechanical Keyboard", "Tablet Air", "VR Headset"],
        "clothing": ["Denim Jacket", "Leather Boots", "Running Shoes", "Cotton T-Shirt", "Hoodie Sweatshirt", "Slim Fit Jeans", "Active Leggings", "Summer Dress", "Wool Scarf", "Silk Tie"],
        "home": ["Robot Vacuum", "Air Purifier", "Memory Foam Pillow", "Duo Coffee Maker", "LED Desk Lamp", "Standing Desk", "Ergonomic Chair", "Slow Cooker", "Cookware Set", "Diffuser"],
        "books": ["Mystery Thriller Book", "Sci-Fi Epic Novel", "Startup Growth Guide", "Python Coding Manual", "History Biography", "Self-Help Journal", "Cookbook Recipes", "Kids Storybook"],
        "beauty": ["Facial Cleanser", "Moisturizing Cream", "Hyaluronic Serum", "Sunscreen SPF 50", "Perfume Eau de Toilette", "Lip Balm Pack", "Matte Lipstick", "Clay Face Mask", "Hair Oil"],
        "sports": ["Yoga Mat Non-slip", "Adjustable Dumbbells", "Water Bottle Insulated", "Resistance Bands Set", "Camping Tent 4-Person", "Sleeping Bag", "Hiking Backpack", "Tennis Racket"]
    }
    
    products_data = []
    product_ids = [f"P{i:03d}" for i in range(1, 301)]
    for i, pid in enumerate(product_ids):
        cat = random.choice(categories)
        prod_names = product_pool[cat]
        name = f"{random.choice(prod_names)} {random.randint(1, 100)}"
        price = round(random.uniform(5.99, 1299.99), 2)
        rating = round(random.uniform(3.5, 5.0), 1)
        products_data.append((pid, name, price, cat, rating))
        
    # Write Products to CSV & DB
    df_products = pd.DataFrame(products_data, columns=["product_id", "name", "price", "category", "rating"])
    df_products.to_csv(os.path.join(DATASET_DIR, "products.csv"), index=False)
    cursor.executemany("INSERT OR IGNORE INTO Products (product_id, name, price, category, rating) VALUES (?, ?, ?, ?, ?)", products_data)
    
    # B. Generate Customers (10,000 customers)
    us_states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
    cities_by_state = {
        "CA": ["Los Angeles", "San Francisco", "San Diego", "San Jose"],
        "NY": ["New York City", "Buffalo", "Rochester", "Albany"],
        "TX": ["Houston", "Austin", "Dallas", "San Antonio"],
        "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
        "IL": ["Chicago", "Springfield", "Naperville", "Rockford"],
        "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie"],
        "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo"],
        "GA": ["Atlanta", "Savannah", "Augusta", "Athens"],
        "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham"],
        "MI": ["Detroit", "Grand Rapids", "Lansing", "Ann Arbor"]
    }
    occupations = ["Engineer", "Teacher", "Doctor", "Artist", "Manager", "Student", "Sales Representative", "Consultant", "Freelancer", "Retired"]
    loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    
    customers_data = []
    customer_ids = [f"C{i:05d}" for i in range(1, 10001)]
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 6, 27)
    
    for pid in customer_ids:
        name = fake.name()
        age = random.randint(18, 75)
        gender = random.choice(["Male", "Female", "Other"])
        state = random.choice(us_states)
        city = random.choice(cities_by_state[state])
        country = "USA"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        phone = fake.phone_number()
        occ = random.choice(occupations)
        reg_days = random.randint(0, 850) # Registered up to 850 days before end_date
        reg_date = (start_date + timedelta(days=reg_days)).strftime("%Y-%m-%d")
        loyalty = random.choices(loyalty_tiers, weights=[50, 30, 15, 5], k=1)[0]
        
        # Placeholders for metrics calculated later
        clv = 0.0
        churn_risk = 0.0
        purchase_freq = 0.0
        
        customers_data.append((pid, name, age, gender, city, state, country, email, phone, occ, reg_date, loyalty, clv, churn_risk, purchase_freq))
        
    df_customers = pd.DataFrame(customers_data, columns=[
        "customer_id", "name", "age", "gender", "city", "state", "country", "email", 
        "phone", "occupation", "registration_date", "loyalty_status", "clv", "churn_risk_score", "purchase_frequency"
    ])
    
    # C. Generate Orders and Transactions (50,000 orders)
    orders_data = []
    transactions_data = []
    
    order_ids = [f"O{i:05d}" for i in range(1, 50001)]
    payment_methods = ["Credit Card", "PayPal", "Bank Transfer", "Apple Pay", "Google Pay"]
    statuses = ["Completed", "Pending", "Cancelled"] # mostly Completed
    
    # Set seed dates
    max_days = (end_date - start_date).days
    
    print("Generating orders...")
    for idx, oid in enumerate(order_ids):
        # Pick customer
        cust_id = random.choice(customer_ids)
        # Find customer registration date to ensure order_date >= reg_date
        reg_date_str = df_customers.loc[df_customers['customer_id'] == cust_id, 'registration_date'].values[0]
        c_reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
        
        order_days = random.randint(0, (end_date - c_reg_date).days)
        order_date = (c_reg_date + timedelta(days=order_days)).strftime("%Y-%m-%d")
        
        # Pick 1-3 products for this order
        n_items = random.choices([1, 2, 3], weights=[70, 20, 10], k=1)[0]
        total_amount = 0.0
        
        for _ in range(n_items):
            prod_row = df_products.sample(n=1).iloc[0]
            qty = random.randint(1, 2)
            total_amount += float(prod_row["price"]) * qty
            
        total_amount = round(total_amount, 2)
        pay_method = random.choice(payment_methods)
        status = random.choices(statuses, weights=[85, 10, 5], k=1)[0]
        
        orders_data.append((oid, cust_id, order_date, total_amount, pay_method, status))
        
        # Transaction detail
        tid = f"T{idx+1:05d}"
        t_status = "Success" if status == "Completed" else ("Failed" if status == "Cancelled" else "Pending")
        transactions_data.append((tid, oid, order_date, total_amount, t_status))

    df_orders = pd.DataFrame(orders_data, columns=["order_id", "customer_id", "order_date", "total_amount", "payment_method", "status"])
    df_transactions = pd.DataFrame(transactions_data, columns=["transaction_id", "order_id", "transaction_date", "amount", "status"])
    
    # Save CSVs
    df_orders.to_csv(os.path.join(DATASET_DIR, "orders.csv"), index=False)
    
    # DB Bulk Insert
    cursor.executemany("INSERT OR IGNORE INTO Orders (order_id, customer_id, order_date, total_amount, payment_method, status) VALUES (?, ?, ?, ?, ?, ?)", orders_data)
    cursor.executemany("INSERT OR IGNORE INTO Transactions (transaction_id, order_id, transaction_date, amount, status) VALUES (?, ?, ?, ?, ?)", transactions_data)
    
    # Calculate Customer aggregation metrics to update Customers table
    print("Updating customer metrics in SQLite database...")
    completed_orders = df_orders[df_orders['status'] == 'Completed']
    customer_spend = completed_orders.groupby('customer_id')['total_amount'].agg(['sum', 'count']).reset_index()
    customer_spend.columns = ['customer_id', 'total_spend', 'order_count']
    
    # Recency check
    last_order_dates = completed_orders.groupby('customer_id')['order_date'].max().reset_index()
    last_order_dates['last_purchase_date'] = pd.to_datetime(last_order_dates['order_date'])
    
    # Merge back to customers dataframe
    df_cust_agg = df_customers.merge(customer_spend, on='customer_id', how='left').merge(last_order_dates, on='customer_id', how='left')
    df_cust_agg['total_spend'] = df_cust_agg['total_spend'].fillna(0.0)
    df_cust_agg['order_count'] = df_cust_agg['order_count'].fillna(0)
    
    # Compute RFM metrics
    # Max date in dataset is end_date
    ref_date = end_date
    
    # Churn definitions and properties
    def calc_metrics(row):
        total_spend = row['total_spend']
        order_count = row['order_count']
        
        # CLV calculation (simulated basic customer lifetime value formula)
        clv = round(total_spend * 1.35, 2)
        
        # Frequency (orders per year)
        reg_dt = datetime.strptime(row['registration_date'], "%Y-%m-%d")
        tenure_days = max((ref_date - reg_dt).days, 1)
        freq = round((order_count / tenure_days) * 365, 2)
        
        # Recency & Churn Risk
        if pd.isna(row['last_purchase_date']):
            recency_days = tenure_days
            churn_prob = 0.95
        else:
            recency_days = (ref_date - row['last_purchase_date']).days
            # Churn probability rises with recency
            churn_prob = min(1.0, recency_days / 365.0)
            if row['loyalty_status'] == 'Platinum':
                churn_prob *= 0.6
            elif row['loyalty_status'] == 'Gold':
                churn_prob *= 0.8
                
        return pd.Series([clv, round(churn_prob, 2), freq])
        
    df_cust_agg[['clv', 'churn_risk_score', 'purchase_frequency']] = df_cust_agg.apply(calc_metrics, axis=1)
    
    # Save final Customer CSV
    df_customers_final = df_cust_agg.drop(columns=['total_spend', 'order_count', 'order_date', 'last_purchase_date'])
    df_customers_final.to_csv(os.path.join(DATASET_DIR, "customers.csv"), index=False)
    
    # Insert Customers into SQLite
    customers_tuples = [tuple(x) for x in df_customers_final.values]
    cursor.executemany("INSERT OR IGNORE INTO Customers (customer_id, name, age, gender, city, state, country, email, phone, occupation, registration_date, loyalty_status, clv, churn_risk_score, purchase_frequency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", customers_tuples)
    
    conn.commit()
    conn.close()
    print("Database seeding completed.")
    return True

# --- 2. MACHINE LEARNING ENGINE ---

def train_ml_models():
    """Trains the baseline Machine Learning models and stores them in models/."""
    print("Training ML Models...")
    conn = database.get_db_connection()
    
    # Load data from database
    df_cust = pd.read_sql_query("SELECT * FROM Customers", conn)
    df_orders = pd.read_sql_query("SELECT * FROM Orders WHERE status = 'Completed'", conn)
    df_products = pd.read_sql_query("SELECT * FROM Products", conn)
    
    conn.close()
    
    if len(df_cust) == 0 or len(df_orders) == 0:
        print("Insufficient data to train models.")
        return
        
    # Prepare features for Churn & CLV
    # We want features like: age, gender, loyalty_status, total spending, order count, tenure, average order value.
    cust_spend = df_orders.groupby('customer_id')['total_amount'].agg(['sum', 'count', 'mean']).reset_index()
    cust_spend.columns = ['customer_id', 'total_spend', 'order_count', 'aov']
    
    # Last purchase
    last_purch = df_orders.groupby('customer_id')['order_date'].max().reset_index()
    last_purch['last_purchase_date'] = pd.to_datetime(last_purch['order_date'])
    
    ref_date = datetime(2026, 6, 27)
    
    # Merge features
    df_features = df_cust.merge(cust_spend, on='customer_id', how='left').merge(last_purch, on='customer_id', how='left')
    df_features['total_spend'] = df_features['total_spend'].fillna(0.0)
    df_features['order_count'] = df_features['order_count'].fillna(0)
    df_features['aov'] = df_features['aov'].fillna(0.0)
    
    # Tenure
    df_features['reg_date_dt'] = pd.to_datetime(df_features['registration_date'])
    df_features['tenure_days'] = (ref_date - df_features['reg_date_dt']).dt.days
    
    # Recency
    df_features['recency_days'] = (ref_date - df_features['last_purchase_date']).dt.days
    df_features['recency_days'] = df_features['recency_days'].fillna(df_features['tenure_days'])
    
    # Target variables
    # Churn Target: Churn if recency > 180 days (arbitrary but realistic business rule)
    df_features['is_churn'] = (df_features['recency_days'] > 180).astype(int)
    
    # Encode categorical features
    df_features['is_male'] = (df_features['gender'] == 'Male').astype(int)
    df_features['is_female'] = (df_features['gender'] == 'Female').astype(int)
    
    loyalty_map = {"Bronze": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
    df_features['loyalty_rank'] = df_features['loyalty_status'].map(loyalty_map).fillna(1)
    
    # Model 1: Churn Prediction Model (Random Forest Classifier)
    X_churn = df_features[['age', 'is_male', 'is_female', 'loyalty_rank', 'total_spend', 'order_count', 'aov', 'tenure_days']]
    y_churn = df_features['is_churn']
    
    clf_churn = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf_churn.fit(X_churn, y_churn)
    joblib.dump(clf_churn, os.path.join(MODEL_DIR, "churn_model.pkl"))
    
    # Model 2: CLV Prediction Model (Random Forest Regressor)
    # Target is customer lifetime value (which in our dummy data is total_spend * 1.35)
    X_clv = df_features[['age', 'is_male', 'is_female', 'loyalty_rank', 'order_count', 'tenure_days']]
    y_clv = df_features['clv']
    
    reg_clv = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    reg_clv.fit(X_clv, y_clv)
    joblib.dump(reg_clv, os.path.join(MODEL_DIR, "clv_model.pkl"))
    
    # Model 3: Customer Segmentation (K-Means on RFM)
    rfm_df = df_features[['recency_days', 'order_count', 'total_spend']].copy()
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_df)
    
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    kmeans.fit(rfm_scaled)
    
    segmentation_pack = {
        "scaler": scaler,
        "kmeans": kmeans,
        "cluster_names": {
            0: "Occasional Buyers / At Risk",
            1: "Premium Loyalists",
            2: "Standard Regulars",
            3: "Recent New Shoppers"
        }
    }
    joblib.dump(segmentation_pack, os.path.join(MODEL_DIR, "segmentation_model.pkl"))
    
    # Model 4: Recommendation System (Frequently Bought Together / Co-occurrence matrix)
    # We will build a co-occurrence index of products in orders
    # Get products for each order
    conn = database.get_db_connection()
    # Since in fake orders we didn't write an OrderDetails table, we can generate simulated co-occurrences
    # to feed the model. Let's create an association structure.
    # We map category co-occurrences or generate random product co-occurrences.
    product_ids = df_products['product_id'].tolist()
    co_occurrences = {}
    
    for pid in product_ids:
        # Pick 5-10 product IDs that are frequently bought with this product
        similar_pids = random.sample(product_ids, random.randint(4, 8))
        if pid in similar_pids:
            similar_pids.remove(pid)
        co_occurrences[pid] = [
            {"product_id": sim_id, "score": random.randint(60, 99)} 
            for sim_id in similar_pids
        ]
        
    joblib.dump(co_occurrences, os.path.join(MODEL_DIR, "recommendation_model.pkl"))
    print("Model training completed successfully.")

def get_churn_prediction(customer_data):
    """
    Predicts churn using the trained RandomForestClassifier.
    Input customer_data: dict with 'age', 'gender', 'loyalty_status', 'total_spend', 'order_count', 'aov', 'tenure_days'
    """
    model_path = os.path.join(MODEL_DIR, "churn_model.pkl")
    if not os.path.exists(model_path):
        return {"error": "Churn model not trained yet."}
        
    clf = joblib.load(model_path)
    
    # Convert input dict to feature list
    is_male = 1 if customer_data.get('gender') == 'Male' else 0
    is_female = 1 if customer_data.get('gender') == 'Female' else 0
    loyalty_map = {"Bronze": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
    loyalty_rank = loyalty_map.get(customer_data.get('loyalty_status'), 1)
    
    features = [[
        customer_data.get('age', 35),
        is_male,
        is_female,
        loyalty_rank,
        customer_data.get('total_spend', 100.0),
        customer_data.get('order_count', 2),
        customer_data.get('aov', 50.0),
        customer_data.get('tenure_days', 365)
    ]]
    
    prob = clf.predict_proba(features)[0][1] # Probability of churn
    pred = clf.predict(features)[0]
    
    # Risk calculation
    if prob < 0.3:
        risk_level = "Low"
    elif prob < 0.6:
        risk_level = "Medium"
    else:
        risk_level = "High"
        
    # Feature importances (Surrogate model explanation)
    features_list = ['Age', 'Is Male', 'Is Female', 'Loyalty Tier', 'Total Spending', 'Order Count', 'Average Order Value', 'Customer Tenure']
    importances = clf.feature_importances_
    explanations = sorted(zip(features_list, importances), key=lambda x: x[1], reverse=True)
    
    return {
        "churn_probability": round(prob, 4),
        "prediction": int(pred),
        "risk_level": risk_level,
        "confidence_score": round(1 - abs(0.5 - prob)*2, 4), # scale so 0.5 probability is 0 confidence and 0/1 is 100% confidence
        "explanations": explanations[:3]
    }

def get_clv_prediction(customer_data):
    """Predicts Customer Lifetime Value using RandomForestRegressor."""
    model_path = os.path.join(MODEL_DIR, "clv_model.pkl")
    if not os.path.exists(model_path):
        return {"error": "CLV model not trained yet."}
        
    reg = joblib.load(model_path)
    
    is_male = 1 if customer_data.get('gender') == 'Male' else 0
    is_female = 1 if customer_data.get('gender') == 'Female' else 0
    loyalty_map = {"Bronze": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
    loyalty_rank = loyalty_map.get(customer_data.get('loyalty_status'), 1)
    
    features = [[
        customer_data.get('age', 35),
        is_male,
        is_female,
        loyalty_rank,
        customer_data.get('order_count', 2),
        customer_data.get('tenure_days', 365)
    ]]
    
    clv_val = reg.predict(features)[0]
    return {"clv_predicted": round(float(clv_val), 2)}

# --- 3. DATA CLEANING UTILITY ---

def clean_uploaded_dataset(df, remove_dups=True, fill_na=True, standardize_cols=True):
    """Cleans a DataFrame based on options and returns the cleaned DataFrame."""
    cleaned_df = df.copy()
    
    if remove_dups:
        cleaned_df.drop_duplicates(inplace=True)
        
    if fill_na:
        # Clean numeric columns with median, categorical with mode
        for col in cleaned_df.columns:
            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median() if not cleaned_df[col].isna().all() else 0)
            else:
                cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].mode()[0] if not cleaned_df[col].isna().all() else "Unknown")
                
    if standardize_cols:
        # Strip string whitespace and lowercase column headers
        cleaned_df.columns = [str(col).strip().replace(" ", "_").lower() for col in cleaned_df.columns]
        for col in cleaned_df.select_dtypes(include=['object']):
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
            
    return cleaned_df

# --- 4. REPORT GENERATION ---

def generate_pdf_report(filename, report_title, headers, rows, summary_text=""):
    """Generates a professional PDF report containing tables and text using ReportLab."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'ReportMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=25
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=20
    )
    
    # Add Title & Metadata
    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Category: Platform Insights", meta_style))
    
    # Add Summary Text
    if summary_text:
        story.append(Paragraph(summary_text, body_style))
        
    story.append(Spacer(1, 10))
    
    # Add Table Data
    table_data = [headers]
    for row in rows:
        table_data.append([str(item) for item in row])
        
    t = Table(table_data, colWidths=None)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    story.append(t)
    doc.build(story)
    return pdf_path
