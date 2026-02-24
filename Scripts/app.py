import html
import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Page configuration
st.set_page_config(layout="wide", page_title="Crypto Watch", page_icon="📈")

BINANCE_GREEN = "#26a69a"
BINANCE_RED = "#ef5350"

APP_BG = "#0b1220"
APP_PANEL = "#111a2e"
APP_PANEL_2 = "#0f172a"
APP_TEXT_MUTED = "rgba(255, 255, 255, 0.72)"

# --- COPY (English-only) ---

TEXT = {
    "title": "Crypto Watch",
    "subtitle": "Price dashboard + conversion and real-time candlestick charts (exchange-style)",
    "sidebar_crypto": "Select cryptocurrency",
    "sidebar_source": "Data source",
    "source_real": "Real data (yfinance)",
    "source_simulated": "Simulated",
    "source_label": "Data source",
    "last_update": "Last updated",
    "period": "Period",
    "interval": "Interval",
    "auto_refresh_on": "Auto-refresh: on",
    "auto_refresh_off": "Auto-refresh: off",
    "auto_refresh_toggle": "Toggle auto-refresh",
    "refresh_seconds": "Interval (seconds)",
    "refresh_info": "The chart refreshes every {refresh_seconds}s when enabled.",
    "sim_notice": "Simulated data is randomly generated.",
    "error_fetch": "Error fetching data for",
    "fiat_display": "Conversion currency",
    "fiat_multi": "Show conversions in",
    "amount": "Amount",
    "converter": "Quick converter",
    "market_overview": "Market (Prices + Conversion)",
    "table_title": "Price + conversion table",
    "chart_title": "Chart (Candlestick)",
    "price_now": "Price now",
    "change": "Change",
}

CRYPTO_NAMES = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
    "BNB-USD": "BNB",
    "XRP-USD": "XRP",
    "DOGE-USD": "Dogecoin",
}

CRYPTO_TICKERS = list(CRYPTO_NAMES.keys())
PERIOD_OPTIONS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "max"]
INTERVAL_OPTIONS = ["5m", "15m", "30m", "1h", "1d", "1wk"]

BASE_PRICES = {
    "BTC-USD": 45000.0,
    "ETH-USD": 2500.0,
    "SOL-USD": 110.0,
    "BNB-USD": 300.0,
    "XRP-USD": 0.55,
    "DOGE-USD": 0.08,
}

PERIOD_TO_DAYS = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "max": 730}
INTERVAL_TO_FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1H", "1d": "1D", "1wk": "1W"}

FIAT_CHOICES = ["USD", "BRL", "EUR", "GBP"]
FX_TICKERS_USD_BASED = {"BRL": "USDBRL=X", "EUR": "USDEUR=X", "GBP": "USDGBP=X"}
FX_FALLBACK = {"USD": 1.0, "BRL": 5.2, "EUR": 0.92, "GBP": 0.79}


# --- DATA FETCHING ---

@st.cache_data(ttl=60)
def get_crypto_data(ticker: str, period: str, interval: str):
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        if data is None or data.empty:
            return None, f"No data found for ticker {ticker}"

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data = data.reset_index()
        date_col = next((c for c in data.columns if isinstance(c, str) and "date" in c.lower()), None)
        if not date_col:
            return None, "Datetime column not found in data"
        data = data.rename(columns={date_col: "Date"})
        return data, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=300)
def get_fx_rates_usd_to(fiat_codes: list[str]):
    fiat_codes = [c for c in dict.fromkeys(fiat_codes) if c in FIAT_CHOICES]
    rates: dict[str, float] = {"USD": 1.0}

    tickers = [FX_TICKERS_USD_BASED.get(code) for code in fiat_codes if code != "USD"]
    tickers = [t for t in tickers if t]
    if not tickers:
        for code in fiat_codes:
            rates[code] = rates.get(code, FX_FALLBACK.get(code, 1.0))
        return rates

    try:
        fx = yf.download(tickers=tickers, period="5d", interval="1d", progress=False, auto_adjust=False)
        if fx is None or fx.empty:
            for code in fiat_codes:
                rates[code] = rates.get(code, FX_FALLBACK.get(code, 1.0))
            return rates

        if isinstance(fx.columns, pd.MultiIndex):
            close = fx.xs("Close", axis=1, level=0, drop_level=True)
        else:
            close = fx[["Close"]].rename(columns={"Close": tickers[0]})

        last_row = close.ffill().dropna(how="all").tail(1)
        if last_row.empty:
            for code in fiat_codes:
                rates[code] = rates.get(code, FX_FALLBACK.get(code, 1.0))
            return rates

        last = last_row.iloc[0].to_dict()
        for code in fiat_codes:
            if code == "USD":
                rates["USD"] = 1.0
                continue
            fx_ticker = FX_TICKERS_USD_BASED.get(code)
            value = last.get(fx_ticker)
            if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                value = FX_FALLBACK.get(code, 1.0)
            rates[code] = float(value)
        return rates
    except Exception:
        for code in fiat_codes:
            rates[code] = rates.get(code, FX_FALLBACK.get(code, 1.0))
        return rates


@st.cache_data(ttl=60)
def get_market_snapshot_usd(tickers: list[str]):
    tickers = list(dict.fromkeys(tickers))
    try:
        data = yf.download(tickers=tickers, period="2d", interval="1h", progress=False, auto_adjust=False)
        if data is None or data.empty:
            return None, "No market data"

        if isinstance(data.columns, pd.MultiIndex):
            close = data.xs("Close", axis=1, level=0, drop_level=True)
        else:
            close = data[["Close"]].rename(columns={"Close": tickers[0]})

        close = close.ffill().dropna(how="all")
        if close.empty:
            return None, "No close data"

        tail2 = close.tail(2)
        last = tail2.iloc[-1]
        prev = tail2.iloc[0] if len(tail2) >= 2 else tail2.iloc[-1]

        out = {}
        for t in tickers:
            last_v = float(last.get(t, np.nan))
            prev_v = float(prev.get(t, np.nan))
            if np.isnan(last_v) or np.isnan(prev_v) or prev_v == 0:
                change = np.nan
            else:
                change = (last_v - prev_v) / prev_v * 100.0
            out[t] = {"last": last_v, "prev": prev_v, "change_pct": change}
        return out, None
    except Exception as e:
        return None, str(e)


def generate_fake_data(ticker: str, period: str, interval: str, seed: int | None = None):
    days = PERIOD_TO_DAYS.get(period, 30)
    freq = INTERVAL_TO_FREQ.get(interval, "1H")

    end = pd.Timestamp.now()
    start = end - pd.Timedelta(days=days)
    dates = pd.date_range(start=start, end=end, freq=freq)
    if len(dates) < 2:
        dates = pd.date_range(end=end, periods=60, freq=freq)

    rng = np.random.default_rng(seed)
    base_price = BASE_PRICES.get(ticker, 1000.0)

    returns = rng.normal(0, 0.002, size=len(dates))
    closes = base_price * np.exp(np.cumsum(returns))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]

    wick = rng.uniform(0.0005, 0.01, size=len(dates))
    highs = np.maximum(opens, closes) * (1 + wick)
    lows = np.minimum(opens, closes) * (1 - wick)

    df = pd.DataFrame({"Date": dates, "Open": opens, "High": highs, "Low": lows, "Close": closes})
    return df, None


# --- UI HELPERS ---

def fmt_money(value: float, code: str):
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "—"
    if code == "USD":
        return f"${value:,.2f}"
    if code == "BRL":
        return f"R${value:,.2f}"
    if code == "EUR":
        return f"€{value:,.2f}"
    if code == "GBP":
        return f"£{value:,.2f}"
    return f"{value:,.2f} {code}"


def pct_badge(value: float):
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return ("—", APP_TEXT_MUTED)
    color = BINANCE_GREEN if value >= 0 else BINANCE_RED
    sign = "+" if value >= 0 else ""
    return (f"{sign}{value:.2f}%", color)


def render_market_card(name: str, symbol: str, price_usd: float, change_pct: float, fx_rates: dict, extra_fiats: list[str]):
    safe_name = html.escape(name)
    safe_symbol = html.escape(symbol)
    change_text, change_color = pct_badge(change_pct)
    lines = []
    lines.append(f"<div class='mcard-title'>{safe_name} <span class='mcard-symbol'>{safe_symbol}</span></div>")
    lines.append(f"<div class='mcard-price'>{fmt_money(price_usd, 'USD')}</div>")
    lines.append(f"<div class='mcard-change' style='color:{change_color}'>{change_text}</div>")
    if extra_fiats:
        conv = []
        for code in extra_fiats:
            rate = fx_rates.get(code, 1.0)
            conv.append(
                f"<span class='mcard-conv'>{html.escape(code)} {html.escape(fmt_money(price_usd * rate, code))}</span>"
            )
        lines.append("<div class='mcard-conversions'>" + "".join(conv) + "</div>")
    return "<div class='mcard'>" + "".join(lines) + "</div>"


# --- PLOTTING ---

def create_candlestick_chart(df: pd.DataFrame, crypto_name: str):
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color=BINANCE_GREEN,
            decreasing_line_color=BINANCE_RED,
            name=crypto_name,
        )
    )

    fig.update_layout(
        title={
            "text": f"{crypto_name.upper()}/USD",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": {"size": 24, "color": "white"},
        },
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        xaxis_title=None,
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        font=dict(family="Arial, sans-serif", size=14, color="white"),
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)", showgrid=True),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)", showgrid=True, side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d-%b'%y")
    return fig


# --- UI & APP LOGIC ---

st.markdown(
    f"""
    <style>
      .stApp {{
        background: radial-gradient(1200px 800px at 10% 0%, rgba(38,166,154,0.10), transparent 60%),
                    radial-gradient(900px 600px at 90% 10%, rgba(239,83,80,0.10), transparent 55%),
                    {APP_BG};
        color: white;
      }}
      [data-testid="stSidebar"] > div:first-child {{
        background: linear-gradient(180deg, {APP_PANEL} 0%, {APP_PANEL_2} 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
      }}
      .app-hero {{
        padding: 18px 18px 8px 18px;
        border: 1px solid rgba(255,255,255,0.06);
        background: linear-gradient(135deg, rgba(38,166,154,0.12), rgba(17,26,46,0.85));
        border-radius: 14px;
        margin-bottom: 14px;
      }}
      .app-hero h1 {{
        font-size: 28px;
        margin: 0;
        letter-spacing: .2px;
      }}
      .app-hero p {{
        margin: 6px 0 0 0;
        color: {APP_TEXT_MUTED};
      }}
      .section-title {{
        margin: 10px 0 6px 0;
        font-size: 14px;
        color: rgba(255,255,255,0.92);
        letter-spacing: .2px;
        text-transform: uppercase;
      }}
      .mcard {{
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(17,26,46,0.75);
        border-radius: 14px;
        padding: 12px 12px;
        height: 132px;
      }}
      .mcard-title {{
        font-size: 13px;
        color: rgba(255,255,255,0.90);
        display: flex;
        gap: 8px;
        align-items: baseline;
      }}
      .mcard-symbol {{
        font-size: 11px;
        color: rgba(255,255,255,0.55);
      }}
      .mcard-price {{
        font-size: 22px;
        font-weight: 700;
        margin-top: 6px;
      }}
      .mcard-change {{
        margin-top: 2px;
        font-size: 12px;
        font-weight: 600;
      }}
      .mcard-conversions {{
        margin-top: 10px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        color: rgba(255,255,255,0.70);
        font-size: 11px;
      }}
      .mcard-conv {{
        padding: 4px 8px;
        border-radius: 999px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.06);
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True


with st.sidebar:
    data_source = st.radio(TEXT["sidebar_source"], options=[TEXT["source_real"], TEXT["source_simulated"]], index=0)
    use_simulated = data_source == TEXT["source_simulated"]

    st.markdown("---")

    crypto_options_display = [CRYPTO_NAMES[ticker] for ticker in CRYPTO_TICKERS]
    selected_crypto_name = st.selectbox(TEXT["sidebar_crypto"], options=crypto_options_display)
    selected_ticker = next(ticker for ticker, name in CRYPTO_NAMES.items() if name == selected_crypto_name)

    col1, col2 = st.columns(2)
    with col1:
        selected_period = st.selectbox(TEXT["period"], PERIOD_OPTIONS, index=1)
    with col2:
        selected_interval = st.selectbox(TEXT["interval"], INTERVAL_OPTIONS, index=1)

    st.markdown("---")

    if st.button(TEXT["auto_refresh_toggle"]):
        st.session_state["auto_refresh"] = not st.session_state["auto_refresh"]
    auto_refresh = st.session_state["auto_refresh"]
    st.caption(TEXT["auto_refresh_on"] if auto_refresh else TEXT["auto_refresh_off"])
    refresh_seconds = st.slider(TEXT["refresh_seconds"], min_value=10, max_value=300, value=60, step=10)

    if use_simulated:
        st.caption(TEXT["sim_notice"])

    st.info(TEXT["refresh_info"].format(refresh_seconds=refresh_seconds))

    st.markdown("---")

    default_multi = ["USD", "BRL"]
    display_fiat = st.selectbox(TEXT["fiat_display"], options=FIAT_CHOICES, index=0)
    extra_fiats = st.multiselect(TEXT["fiat_multi"], options=FIAT_CHOICES, default=default_multi)

    st.markdown("---")
    st.subheader(TEXT["converter"])
    amount = st.number_input(TEXT["amount"], min_value=0.0, value=1.0, step=0.1)


st.markdown(
    f"""
    <div class="app-hero">
      <h1>{html.escape(TEXT["title"])}</h1>
      <p>{html.escape(TEXT["subtitle"])} · {html.escape(TEXT["source_label"])}: {html.escape(data_source)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# Fetch chart data (selected crypto)
if use_simulated:
    seed = int(time.time() // max(refresh_seconds, 1))
    df, error_msg = generate_fake_data(selected_ticker, selected_period, selected_interval, seed=seed)
else:
    df, error_msg = get_crypto_data(selected_ticker, selected_period, selected_interval)


# Market snapshot (all cryptos) + FX
fx_rates = get_fx_rates_usd_to(extra_fiats + [display_fiat])

if use_simulated:
    rng = np.random.default_rng(int(time.time() // max(refresh_seconds, 1)))
    snapshot = {}
    for t in CRYPTO_TICKERS:
        base = BASE_PRICES.get(t, 100.0)
        last = float(base * (1 + rng.normal(0, 0.01)))
        prev = float(base * (1 + rng.normal(0, 0.01)))
        change = (last - prev) / prev * 100.0 if prev else np.nan
        snapshot[t] = {"last": last, "prev": prev, "change_pct": change}
else:
    snapshot, _ = get_market_snapshot_usd(CRYPTO_TICKERS)


st.markdown(f"<div class='section-title'>{html.escape(TEXT['market_overview'])}</div>", unsafe_allow_html=True)

cols = st.columns(len(CRYPTO_TICKERS))
for col, t in zip(cols, CRYPTO_TICKERS):
    with col:
        name = CRYPTO_NAMES.get(t, t)
        symbol = t.split("-")[0]
        price_usd = (snapshot or {}).get(t, {}).get("last", np.nan)
        change_pct = (snapshot or {}).get(t, {}).get("change_pct", np.nan)
        st.markdown(
            render_market_card(
                name=name,
                symbol=symbol,
                price_usd=price_usd,
                change_pct=change_pct,
                fx_rates=fx_rates,
                extra_fiats=[c for c in extra_fiats if c != "USD"][:2],
            ),
            unsafe_allow_html=True,
        )


rows = []
for t in CRYPTO_TICKERS:
    name = CRYPTO_NAMES.get(t, t)
    price_usd = (snapshot or {}).get(t, {}).get("last", np.nan)
    change_pct = (snapshot or {}).get(t, {}).get("change_pct", np.nan)
    row = {
        "Ticker": t,
        "Name": name,
        f"{TEXT['price_now']} (USD)": price_usd,
        f"{TEXT['change']} (%)": change_pct,
    }
    for code in sorted(set(extra_fiats)):
        row[f"{TEXT['price_now']} ({code})"] = price_usd * fx_rates.get(code, 1.0)
    rows.append(row)

table = pd.DataFrame(rows)
st.markdown(f"<div class='section-title'>{html.escape(TEXT['table_title'])}</div>", unsafe_allow_html=True)
st.dataframe(table, use_container_width=True, hide_index=True)


if snapshot and selected_ticker in snapshot:
    price_usd = snapshot[selected_ticker]["last"]
    rate = fx_rates.get(display_fiat, 1.0)
    converted = amount * price_usd * rate

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric(label=f"{amount:g} {selected_crypto_name}", value=fmt_money(amount * price_usd, "USD"))
    with c2:
        st.metric(label=f"→ {display_fiat}", value=fmt_money(converted, display_fiat))
    with c3:
        st.caption(" ")


if df is not None:
    st.markdown(f"<div class='section-title'>{html.escape(TEXT['chart_title'])}</div>", unsafe_allow_html=True)
    fig = create_candlestick_chart(df, selected_crypto_name)
    st.plotly_chart(fig, use_container_width=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.write(f"*{TEXT['last_update']}: {now}*")
else:
    st.error(f"{TEXT['error_fetch']} **{selected_crypto_name}**: `{error_msg}`")
    st.warning("Please try a different period/interval or check the ticker.")


if auto_refresh:
    time.sleep(refresh_seconds)
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()
