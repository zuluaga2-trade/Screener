import streamlit as st
import pandas as pd
import requests
import os
import plotly.graph_objects as go
import numpy as np
import io
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. FUNCIÓN DE SEGURIDAD (CERRADURA) ---
def login_sistema():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    
    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #00f2ff;'>🦅 Alpha Hunter Elite</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar al Búnker"):
                db_usuarios = st.secrets.get("usuarios", {})
                if u in db_usuarios and str(db_usuarios[u]) == p:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = u
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas o usuario no registrado.")
        st.stop()

# --- 2. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Alpha Hunter Premium Elite", layout="wide")
login_sistema()

# --- 3. PERSISTENCIA INDIVIDUAL (TUS 3 PUNTOS) ---
# Creamos nombres de archivo únicos basados en el nombre de usuario
def get_user_path(base_name):
    user = st.session_state.get("usuario", "default")
    return f"{user}_{base_name}"

def save_data(file_name, content):
    path = get_user_path(file_name)
    with open(path, "w") as f:
        f.write(content)

def load_data(file_name, default=""):
    path = get_user_path(file_name)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    return default

# --- 4. ESTILO VISUAL ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .metric-card { background-color: #1b212c; padding: 20px; border-radius: 12px; border: 1px solid #30363d; text-align: center; min-height: 140px; }
    .fundamental-box { background-color: #0d1117; border: 1px solid #00f2ff; padding: 20px; border-radius: 10px; margin-top: 10px; }
    .vola-master { background: linear-gradient(90deg, #2c1a4d 0%, #161b22 100%); border-left: 8px solid #9b59b6; padding: 25px; border-radius: 15px; margin: 20px 0; border: 1px solid #30363d; box-shadow: 5px 5px 15px rgba(0,0,0,0.5); }
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-danger { color: #e74c3c; font-weight: bold; }
    .tooltip { position: relative; display: inline-block; cursor: help; border-bottom: 2px dotted #00f2ff; color: #00f2ff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. BARRA LATERAL ---
st.sidebar.title("🚀 Centro de Mando")
st.sidebar.write(f"Conectado como: **{st.session_state['usuario']}**")

# Carga individual de Keys
tradier_token = st.sidebar.text_input("Tradier Token", value=load_data(".tradier_token"), type="password")
av_key = st.sidebar.text_input("Alpha Vantage Key", value=load_data(".av_key"), type="password")

if st.sidebar.button("💾 Guardar mi Configuración"):
    save_data(".tradier_token", tradier_token)
    save_data(".av_key", av_key)
    st.sidebar.success("¡Configuración guardada para tu usuario!")

entorno = st.sidebar.selectbox("Entorno Tradier", ["Sandbox", "Brokerage"])
API_TRADIER = "https://api.tradier.com/v1/" if entorno == "Brokerage" else "https://sandbox.tradier.com/v1/"

st.sidebar.divider()
estrategia = st.sidebar.radio("Estrategia", ["Cash Secured Put (CSP)", "Covered Call (CC)"])

if estrategia == "Covered Call (CC)":
    c_base = st.sidebar.number_input("Costo de Acción ($)", value=0.0, step=0.01)
    s_obj = st.sidebar.number_input("Strike Objetivo ($)", value=0.0, step=0.01)
else:
    delta_r = st.sidebar.slider("Rango Delta", -0.50, -0.05, (-0.25, -0.10))
    max_cap_input = st.sidebar.number_input("Capital Máximo en Riesgo ($)", value=45000)

dte_r = st.sidebar.slider("Rango DTE", 0, 90, (7, 45))
roi_min_f = st.sidebar.number_input("ROI Ann Mín %", value=15.0, step=1.0)

st.sidebar.divider()
f_sma = st.sidebar.toggle("Solo SMA 200 (✅)", value=False)
f_stoch = st.sidebar.toggle("Solo Stoch < 30 (1D) 📉", value=False)

# --- 6. DASHBOARD DE PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 SCREENER PROFESIONAL", "🏗️ BÚNKER DE TICKERS", "🧠 ACADEMIA DE VOLATILIDAD"])

with tab2:
    st.subheader("⚙️ Configuración del Búnker Personal")
    # Lista por defecto si el usuario no tiene una guardada
    def_list = "AAPL,AMD,AMZN,META,MSFT,NVDA,TSLA,PLTR"
    user_list = st.text_area("Edita tu lista de tickers (separados por coma):", value=load_data(".watchlist", def_list), height=150)
    
    if st.button("Guardar mi Búnker"):
        save_data(".watchlist", user_list)
        st.success("¡Tu búnker personal ha sido actualizado!")
        st.rerun()

    tickers_clean = sorted(list(set([x.strip().upper() for x in user_list.split(",") if x.strip()])))
    cols = st.columns(6)
    for i, t in enumerate(tickers_clean): cols[i % 6].caption(f"🔹 {t}")

with tab3:
    st.subheader("📖 Manual Estratégico")
    st.markdown("Contenido educativo sobre Volatilidad...")

# --- 7. MOTORES DE DATOS ---
@st.cache_data(ttl=86400)
def sync_global_earnings(key):
    try:
        r = requests.get(f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={key}', timeout=15)
        return pd.read_csv(io.StringIO(r.text)).set_index('symbol')['reportDate'].to_dict()
    except: return {}

@st.cache_data(ttl=86400)
def get_hybrid_overview(sym, key):
    try:
        r = requests.get(f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={sym}&apikey={key}', timeout=8).json()
        if "Symbol" in r:
            return {
                "target": round(float(r.get('AnalystTargetPrice', 0)), 2),
                "margin": round(float(r.get('OperatingMarginTTM', 0)) * 100, 2),
                "roe": round(float(r.get('ReturnOnEquityTTM', 0)) * 100, 2),
                "debt": round(float(r.get('DebtToEquityRatio', 0)), 2),
                "source": "Alpha Vantage"
            }
    except: pass
    
    try:
        t = yf.Ticker(sym)
        i = t.info
        return {
            "target": round(i.get('targetMeanPrice', 0), 2),
            "margin": round(i.get('operatingMargins', 0) * 100, 2),
            "roe": round(i.get('returnOnEquity', 0) * 100, 2),
            "debt": round(i.get('debtToEquity', 0) / 100 if i.get('debtToEquity') else 0, 2),
            "source": "Yahoo Finance (Backup)"
        }
    except: return None

def get_market_techs(sym):
    h = {'Authorization': f'Bearer {tradier_token}', 'Accept': 'application/json'}
    p = {'symbol': sym, 'interval': 'daily', 'start': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')}
    try:
        r = requests.get(f"{API_TRADIER}markets/history", params=p, headers=h, timeout=10).json()
        df = pd.DataFrame(r['history']['day'])
        close = df['close'].astype(float)
        sma200, sma40 = close.iloc[-200:].mean(), close.iloc[-40:].mean()
        low_14, high_14 = df['low'].astype(float).rolling(14).min(), df['high'].astype(float).rolling(14).max()
        stoch = 100 * ((close - low_14) / (high_14 - low_14))
        tr = np.maximum(df['high'].astype(float) - df['low'].astype(float), abs(df['high'].astype(float) - close.shift(1)))
        hv = np.log(close / close.shift(1)).std() * np.sqrt(252) * 100
        return round(sma200, 2), round(sma40, 2), round(stoch.rolling(3).mean().iloc[-1], 2), round(tr.rolling(14).mean().iloc[-1], 2), round(hv, 2)
    except: return None, None, 50.0, 0.0, 0.0

# --- 8. SCREENER (TAB 1) ---
with tab1:
    CATEGORIAS = {
        "🌐 WATCHLIST PRO": tickers_clean,
        "🌐 SCANNER GLOBAL": ["SPY","TSLA","NVDA","AAPL","META","AMD","MSFT","PLTR","AMZN","NFLX"],
        "🎯 INDIVIDUAL": ["CUSTOM"]
    }
    
    c_s1, c_s2 = st.columns([2, 1])
    sector_sel = c_s1.selectbox("Sector de Escaneo", list(CATEGORIAS.keys()))
    tickers_lista = [c_s2.text_input("Ticker", "NVDA").upper()] if sector_sel == "🎯 INDIVIDUAL" or estrategia == "Covered Call (CC)" else CATEGORIAS[sector_sel]

    earnings_db = sync_global_earnings(av_key) if av_key else {}

    if st.button("🚀 INICIAR BARRIDO"):
        # Lógica de escaneo (se mantiene igual a tu código original pero usando las keys de sesión)
        st.write("Buscando oportunidades...")
        # ... resto del bucle de escaneo ...
