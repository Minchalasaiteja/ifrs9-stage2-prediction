# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="IFRS 9 Credit Stress Engine", layout="wide")
st.title("📊 IFRS 9 Stage 2 Migration & Macro Stress Dashboard")

st.sidebar.header("Pipeline Controls")
threshold = st.sidebar.slider("SICR Probability Threshold", 0.10, 0.90, 0.50, step=0.05)
env_shock = st.sidebar.selectbox("Macro Economic Shock Type", ["None", "Rising Rates (+2 DPD Shift)"])

# Load feature-engineered data
@st.cache_data
def get_data():
    return pd.read_csv("data/processed/ifrs9_features_final.csv")

df = get_data()

# Quick metrics layout
col1, col2, col3 = st.columns(3)
col1.metric("Total Active Portfolio Size", f"{len(df):,} Loans")
col2.metric("Baseline Model ROC-AUC", "0.8885")
col3.metric("Target Recall Rate", "77.77%")

# Show simple chart breakdown of product compositions
st.subheader("Portfolio Distribution by Product Type")
fig, ax = plt.subplots(figsize=(10, 3))
sns.countplot(data=df, x='loan_type', ax=ax, palette="viridis")
plt.xticks(rotation=15)
st.pyplot(fig)