import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Crypto Dashboard",
    page_icon="💰",
    layout="wide",
)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# ─────────────────────────────────────────────
# Cached API Fetch Functions
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_markets(vs_currency: str, top_n: int) -> pd.DataFrame:
    """Fetch top N coins by market cap."""
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": top_n,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df = df[[
            "id", "name", "symbol", "current_price",
            "market_cap", "total_volume",
            "price_change_percentage_24h",
            "high_24h", "low_24h",
        ]]
        df.columns = [
            "ID", "Name", "Symbol", "Price (USD)",
            "Market Cap", "Volume (24h)",
            "Change 24h (%)",
            "High 24h", "Low 24h",
        ]
        df["Symbol"] = df["Symbol"].str.upper()
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch market data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_price_history(coin_id: str, vs_currency: str, days: int) -> pd.DataFrame:
    """Fetch historical price data for a single coin."""
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": vs_currency,
        "days": days,
        "interval": "daily" if days > 1 else "hourly",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch price history for {coin_id}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_global_stats() -> dict:
    """Fetch global crypto market statistics."""
    url = f"{COINGECKO_BASE}/global"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch global stats: {e}")
        return {}


# ─────────────────────────────────────────────
# Sidebar – User Input Widgets
# ─────────────────────────────────────────────

st.sidebar.title("⚙️ Dashboard Settings")
st.sidebar.markdown("---")

# Widget 1: Currency selector
currency = st.sidebar.selectbox(
    "Display Currency",
    options=["usd", "eur", "gbp", "jpy", "btc"],
    format_func=lambda x: x.upper(),
    index=0,
)

# Widget 2: Number of top coins to display
top_n = st.sidebar.slider(
    "Number of Top Coins",
    min_value=5,
    max_value=50,
    value=15,
    step=5,
)

# Widget 3: Coin selector for price history (populated after market data loads)
st.sidebar.markdown("---")
st.sidebar.subheader("Price History")

days = st.sidebar.select_slider(
    "Historical Period (days)",
    options=[1, 7, 14, 30, 90, 180, 365],
    value=30,
)

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────

df_markets = fetch_markets(currency, top_n)
global_stats = fetch_global_stats()

# Coin selector depends on market data being loaded
if not df_markets.empty:
    coin_options = df_markets[["ID", "Name"]].copy()
    coin_options["label"] = coin_options["Name"] + " (" + coin_options["ID"] + ")"
    selected_coin_label = st.sidebar.selectbox(
        "Select Coin for Price History",
        options=coin_options["label"].tolist(),
        index=0,
    )
    selected_coin_id = coin_options.loc[
        coin_options["label"] == selected_coin_label, "ID"
    ].values[0]
else:
    selected_coin_id = "bitcoin"

df_history = fetch_price_history(selected_coin_id, currency, days)

# ─────────────────────────────────────────────
# Dashboard Header
# ─────────────────────────────────────────────

st.title("Cryptocurrency Market Dashboard")
st.caption("Powered by CoinGecko Public API · Data refreshes every 5 minutes")
st.markdown("---")

# ─────────────────────────────────────────────
# Component 1: KPI / Metric Cards (Global Stats)
# ─────────────────────────────────────────────

st.subheader("Global Market Overview")

if global_stats:
    total_mcap = global_stats.get("total_market_cap", {}).get(currency, 0)
    total_vol = global_stats.get("total_volume", {}).get(currency, 0)
    btc_dominance = global_stats.get("market_cap_percentage", {}).get("btc", 0)
    active_coins = global_stats.get("active_cryptocurrencies", 0)
    mcap_change = global_stats.get("market_cap_change_percentage_24h_usd", 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Market Cap",
        f"{currency.upper()} {total_mcap:,.0f}",
        delta=f"{mcap_change:.2f}% (24h)",
    )
    col2.metric(
        "24h Trading Volume",
        f"{currency.upper()} {total_vol:,.0f}",
    )
    col3.metric(
        "BTC Dominance",
        f"{btc_dominance:.1f}%",
    )
    col4.metric(
        "Active Cryptocurrencies",
        f"{active_coins:,}",
    )
else:
    st.warning("Global stats unavailable.")

st.markdown("---")

# ─────────────────────────────────────────────
# Component 2: Time Series Chart (Price History)
# ─────────────────────────────────────────────

st.subheader(f"{selected_coin_id.capitalize()} Price History — Last {days} Day(s) ({currency.upper()})")

if not df_history.empty:
    st.line_chart(df_history["price"])
else:
    st.warning("Price history data is unavailable.")

st.markdown("---")

# ─────────────────────────────────────────────
# Component 3: Bar Chart – Top Coins by Market Cap
# ─────────────────────────────────────────────

st.subheader(f"Top {top_n} Coins by Market Cap ({currency.upper()})")

if not df_markets.empty:
    bar_df = df_markets[["Symbol", "Market Cap"]].set_index("Symbol")
    st.bar_chart(bar_df)
else:
    st.warning("Market data is unavailable.")

st.markdown("---")

# ─────────────────────────────────────────────
# Component 4: Data Table – Full Market Overview
# ─────────────────────────────────────────────

st.subheader(f"Market Data Table — Top {top_n} Coins")

if not df_markets.empty:
    display_df = df_markets.drop(columns=["ID"]).copy()
    display_df["Price (USD)"] = display_df["Price (USD)"].apply(lambda x: f"{x:,.4f}")
    display_df["Market Cap"] = display_df["Market Cap"].apply(lambda x: f"{x:,.0f}")
    display_df["Volume (24h)"] = display_df["Volume (24h)"].apply(lambda x: f"{x:,.0f}")
    display_df["High 24h"] = display_df["High 24h"].apply(lambda x: f"{x:,.4f}")
    display_df["Low 24h"] = display_df["Low 24h"].apply(lambda x: f"{x:,.4f}")
    display_df["Change 24h (%)"] = display_df["Change 24h (%)"].apply(
        lambda x: f"+{x:.2f}%" if x >= 0 else f"{x:.2f}%"
    )
    st.dataframe(display_df, use_container_width=True)
else:
    st.warning("No market data to display.")

st.markdown("---")
st.caption("CS 2850 · PA4 · Data from CoinGecko (https://www.coingecko.com)")
