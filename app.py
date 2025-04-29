import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- Authentication ---
def check_credentials(username, password):
    return username == "admin" and password == "password123"  # Set your own password

# --- Page Config ---
st.set_page_config(page_title="Sales Analytics", layout="wide", initial_sidebar_state="expanded")

# --- Load custom CSS ---
with open("styles.css") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- Session Management ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- Login ---
if not st.session_state["logged_in"]:
    st.title("Login to Access Dashboard")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_credentials(username, password):
            st.session_state["logged_in"] = True
            st.success("Login Successful!")
            st.rerun()
        else:
            st.error("Incorrect username or password. Please try again.")

else:
    # --- Google Sheets Data Loader ---
    @st.cache_data(show_spinner=False)
    def load_data_from_sheet():
        # Retrieve the credentials JSON string from Streamlit Secrets
        google_sheets_credentials = st.secrets["google_sheets_credentials"]

        if google_sheets_credentials is None:
            st.error("Google Sheets credentials are missing in Streamlit secrets!")
            return None

        # Load the credentials from Streamlit secrets
        creds = google_sheets_credentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
        client = gspread.authorize(credentials)
        sheet = client.open("data").sheet1  # Make sure your sheet is named "data"
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df["ORDERDATE"] = pd.to_datetime(df["ORDERDATE"], errors="coerce")
        return df

    # --- Refresh Button ---
    st.sidebar.button("🔄 Refresh Data", on_click=lambda: [st.cache_data.clear(), st.rerun()])

    # --- Load Data ---
    df = load_data_from_sheet()

    if df is None:
        st.stop()

    # --- Preprocessing ---
    df["Month"] = df["ORDERDATE"].dt.to_period("M").astype(str)
    df["Year"] = df["ORDERDATE"].dt.year.astype(str)

    # --- Sidebar ---
    st.sidebar.title("SWIFT SAMPLE DASHBOARD")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Earnings", "Products", "Analytics", "Edit Database"], label_visibility="collapsed")
    st.sidebar.markdown("---")
    st.sidebar.write("SWIFT")
    st.sidebar.write("🔊")

    # --- KPIs ---
    total_orders = df["ORDERNUMBER"].nunique()
    completed_orders = df[df["STATUS"] == "Shipped"]["ORDERNUMBER"].nunique()
    pending_orders = total_orders - completed_orders
    total_revenue = df["SALES"].sum()
    unique_clients = df["CUSTOMERNAME"].nunique()

    st.markdown("## 📊 Sales Analytics")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Orders", f"{total_orders}")
    k2.metric("Completed Orders", f"{completed_orders}")
    k3.metric("Pending Orders", f"{pending_orders}")
    k4.metric("Total Revenue", f"${total_revenue:,.0f}")

    # --- Charts Row 1 ---
    row1_col1, row1_col2 = st.columns([1,2])
    fig_orders = px.pie(df.groupby("STATUS").size().reset_index(name="Count"), names="STATUS", values="Count", hole=0.6, title="Orders by Status")
    row1_col1.plotly_chart(fig_orders, use_container_width=True)

    clients_month = df.groupby("Month")["CUSTOMERNAME"].nunique().reset_index(name="Active Clients")
    fig_clients = px.bar(clients_month, x="Month", y="Active Clients", title="Clients Activity", text="Active Clients")
    row1_col2.plotly_chart(fig_clients, use_container_width=True)

    # --- Summary & Profit ---
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.markdown("### Summary")
        sum1, sum2, sum3 = st.columns(3)
        sum1.metric("Unique Clients", unique_clients)
        sum2.metric("Avg Deal Size", df["DEALSIZE"].value_counts(normalize=True).idxmax())
        sum3.metric("Avg Order Value", f"${(total_revenue / total_orders):.2f}")

    with row2_col2:
        st.markdown("### Total Profit Over Time")
        profit_time = df.groupby("Month")["SALES"].sum().reset_index()
        fig_profit = px.area(profit_time, x="Month", y="SALES", title="Sales Over Time")
        st.plotly_chart(fig_profit, use_container_width=True)

    # --- Sales Summary & Top Clients ---
    st.markdown("---")
    r3c1, r3c2 = st.columns([2,1])
    with r3c1:
        st.markdown("#### Sales Summary by Month")
        fig_sales = px.line(profit_time, x="Month", y="SALES", markers=True, title="Monthly Sales Trend")
        st.plotly_chart(fig_sales, use_container_width=True)

    with r3c2:
        st.markdown("#### Top Clients")
        top_clients = df.groupby("CUSTOMERNAME")["SALES"].sum().reset_index().sort_values("SALES", ascending=False).head(5)
        st.table(top_clients.style.format({"SALES": "${:,.0f}"}))

    # --- Bottom Charts ---
    st.markdown("---")
    b1, b2, _ = st.columns(3)

    with b1:
        st.markdown("##### Best Sellers")
        top_products = df.groupby("PRODUCTCODE")["SALES"].sum().reset_index().sort_values("SALES", ascending=False).head(5)
        fig_prod = px.bar(top_products, x="PRODUCTCODE", y="SALES", title="Top Products", text="SALES")
        st.plotly_chart(fig_prod, use_container_width=True)

    with b2:
        st.markdown("##### Customer Satisfaction")
        status_counts = df["STATUS"].value_counts(normalize=True).reset_index()
        status_counts.columns = ["Status", "Share"]
        fig_sat = px.pie(status_counts, names="Status", values="Share", hole=0.6, title="On-Time vs. Other")
        st.plotly_chart(fig_sat, use_container_width=True)

    # --- Data Table ---
    st.markdown("---")
    st.markdown("### View CSV Data")
    st.dataframe(df, use_container_width=True)
