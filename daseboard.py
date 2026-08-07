import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Stock Market Dashboard", page_icon="📈", layout="wide")

st.title("📈 All India Stock Market & News Dashboard")
st.markdown("Aapka apna custom Stock API Dashboard powered by FastAPI, Docker & Streamlit.")

# API Key input in sidebar
st.sidebar.header("Authentication & Keys")
api_key = st.sidebar.text_input("Enter your API Key", type="password", value="")

# --- Phone se API Key banane ka feature ---
with st.sidebar.expander("🔑 Generate New API Key"):
    key_name_input = st.text_input("Key Name (e.g., Phone App)", value="Mobile User")
    if st.button("Create Key"):
        try:
            response = requests.post("http://localhost:8000/api/v1/apikey/create", json={"name": key_name_input})
            if response.status_code == 200:
                key_data = response.json()
                st.success("API Key successfully ban gayi!")
                st.code(key_data["api_key"])
                st.info("Ise turant copy karke safe jagah rakh lein, yeh dobara nahi dikhegi!")
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(f"Failed to connect: {e}")

BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {"Authorization": f"Bearer {api_key}", "accept": "application/json"}

# Tabs for navigation (Added Tab 4 for Charts)
tab1, tab2, tab3, tab4 = st.tabs(["📊 Watchlist", "🔍 Search Stocks", "📰 Market News", "📉 Historical Charts"])

with tab1:
    st.subheader("Your Live Watchlist (NSE/BSE)")
    custom_symbols = st.text_input(
        "Enter Stock Symbols (comma separated)", 
        "RELIANCE.NS, TCS.NS, INFY.NS, ^NSEI, HDFCBANK.NS, TATAMOTORS.NS"
    )
    
    if st.button("Fetch Watchlist"):
        if not api_key:
            st.warning("Pehle sidebar mein apni API Key daalein!")
        else:
            try:
                response = requests.get(f"{BASE_URL}/market/watchlist?symbols={custom_symbols}", headers=HEADERS)
                if response.status_code == 200:
                    data = response.json()
                    watchlist = data.get("watchlist_data", {})
                    
                    df = pd.DataFrame(list(watchlist.items()), columns=["Stock Symbol", "Price (INR)"])
                    st.dataframe(df, use_container_width=True)
                    
                    st.bar_chart(df.set_index("Stock Symbol"))
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Failed to connect to API: {e}")

with tab2:
    st.subheader("Search Stock Data")
    symbol_input = st.text_input("Enter Stock Symbol (e.g., RELIANCE.NS, TCS.NS, ^NSEI)", "RELIANCE.NS")
    if st.button("Get Stock Details"):
        if not api_key:
            st.warning("Pehle sidebar mein apni API Key daalein!")
        else:
            try:
                response = requests.get(f"{BASE_URL}/market/stocks?symbol={symbol_input}", headers=HEADERS)
                if response.status_code == 200:
                    st.json(response.json())
                else:
                    st.error("Could not fetch data. Check symbol or API Key.")
            except Exception as e:
                st.error(f"Error: {e}")

with tab3:
    st.subheader("📰 All India Live Market News")
    if st.button("Fetch Latest News"):
        if not api_key:
            st.warning("Pehle sidebar mein apni API Key daalein!")
        else:
            try:
                response = requests.get(f"{BASE_URL}/market/news", headers=HEADERS)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("news", [])
                    
                    st.success(f"Total {len(articles)} live articles fetched successfully!")
                    
                    for idx, article in enumerate(articles, 1):
                        with st.expander(f"{idx}. {article['title']}"):
                            st.write(f"**Published:** {article['published']}")
                            st.write(f"**Summary:** {article['summary'] if article['summary'] else 'No summary available.'}")
                            st.markdown(f"[Read Full Article]({article['link']})")
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Failed to connect to API: {e}")

with tab4:
    st.subheader("📉 Historical Stock Charts")
    symbol_chart = st.text_input("Enter Symbol for Chart", "RELIANCE.NS")
    period_chart = st.selectbox("Select Period", ["1mo", "3mo", "6mo", "1y"])
    
    if st.button("Show Chart"):
        if not api_key:
            st.warning("Pehle sidebar mein apni API Key daalein!")
        else:
            try:
                response = requests.get(f"{BASE_URL}/market/history?symbol={symbol_chart}&period={period_chart}", headers=HEADERS)
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    df = pd.DataFrame(data)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    
                    st.line_chart(df[['Close']])
                else:
                    st.error("Error fetching historical data.")
            except Exception as e:
                st.error(f"Error: {e}")
