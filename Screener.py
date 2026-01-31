import streamlit as st
import pandas as pd
import requests
import os
import plotly.graph_objects as go
import numpy as np
import io
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. FUNCIÓN DE SEGURIDAD (LA CERRADURA) ---
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

# --- 3. PERSISTENCIA POR USUARIO (TUS 3 PUNTOS) ---
def get_user_path(base_name):
    # Crea un nombre de archivo único por usuario (ej. .jose_tradier_token)
    usuario_limpio = st.session_state.get("usuario", "default").lower()
    return f".{usuario_limpio}_{base_name}"

def save_data(f_name, content): 
    path = get_user_path(f_name)
    with open(path, "w") as file: 
        file.write(content)

def load_data(f_name, default=""): 
    path = get_user_path(f_name)
    return open(path, "r").read().strip() if os.path.exists(path) else default

# --- 4. ESTILO VISUAL ORIGINAL ---
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
st.sidebar.write(f"👤 Usuario: **{st.session_state.get('usuario', 'Invitado')}**")

# Cargamos las keys específicas de este usuario
tradier_token = st.sidebar.text_input("Tradier Token", value=load_data("tradier_token"), type="password")
av_key = st.sidebar.text_input("Alpha Vantage Key", value=load_data("av_key"), type="password")

# Botón para guardar manualmente y confirmar persistencia
if st.sidebar.button("💾 Guardar mis Credenciales"):
    save_data("tradier_token", tradier_token)
    save_data("av_key", av_key)
    st.sidebar.success("¡Claves guardadas para tu usuario!")

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

# --- 6. MOTORES DE DATOS ---
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
            return {"target": float(r.get('AnalystTargetPrice', 0)), "margin": float(r.get('OperatingMarginTTM', 0)) * 100, 
                    "roe": float(r.get('ReturnOnEquityTTM', 0)) * 100, "debt": float(r.get('DebtToEquityRatio', 0)), "source": "Alpha Vantage"}
    except: pass
    try:
        i = yf.Ticker(sym).info
        return {"target": i.get('targetMeanPrice', 0), "margin": i.get('operatingMargins', 0) * 100, "roe": i.get('returnOnEquity', 0) * 100, 
                "debt": i.get('debtToEquity', 0) / 100 if i.get('debtToEquity') else 0, "source": "Yahoo Finance (Backup)"}
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

# --- 7. PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 SCREENER PROFESIONAL", "🏗️ BÚNKER DE TICKERS", "🧠 ACADEMIA DE VOLATILIDAD"])

with tab2:
    st.subheader("⚙️ Configuración del Búnker")
    def_list = "AAPL,AMD,AMZN,META,MSFT,NVDA,TSLA,PLTR"
    user_list = st.text_area("Lista de tickers:", value=load_data(".watchlist", def_list), height=150)
    if st.button("Guardar Búnker"):
        save_data(".watchlist", user_list)
        st.success("¡Búnker actualizado!")
        st.rerun()
    tickers_clean = sorted(list(set([x.strip().upper() for x in user_list.split(",") if x.strip()])))
    cols = st.columns(6)
    for i, t in enumerate(tickers_clean): cols[i % 6].caption(f"🔹 {t}")

with tab1:
    CATEGORIAS = {"🌐 SCANNER GLOBAL": ["SPY","TSLA","NVDA","AAPL","META","AMD","MSFT","PLTR","AMZN","NFLX"], "🌐 WATCHLIST PRO": tickers_clean, "🎯 INDIVIDUAL": ["CUSTOM"]}
    sector_sel = st.selectbox("Sector de Escaneo", list(CATEGORIAS.keys()))
    tickers_lista = [st.text_input("Ticker individual", "NVDA").upper()] if sector_sel == "🎯 INDIVIDUAL" else CATEGORIAS[sector_sel]
    
    earnings_db = sync_global_earnings(av_key) if av_key else {}

    if st.button("🚀 INICIAR BARRIDO"):
        res_list = []
        prog = st.progress(0)
        today = datetime.now()
        for idx, sym in enumerate(tickers_lista):
            try:
                q_res = requests.get(f"{API_TRADIER}markets/quotes", params={'symbols': sym}, headers={'Authorization': f'Bearer {tradier_token}', 'Accept': 'application/json'}).json()
                if not q_res or 'quotes' not in q_res or not q_res['quotes']: continue
                price = float(q_res['quotes']['quote'].get('last', 0))
                sma200, sma40, stoch_v, atr_v, hv_v = get_market_techs(sym)
                e_date = earnings_db.get(sym)
                exps = requests.get(f"{API_TRADIER}markets/options/expirations", params={'symbol': sym}, headers={'Authorization': f'Bearer {tradier_token}', 'Accept': 'application/json'}).json()
                if not exps or 'expirations' not in exps: continue
                
                for d_str in exps['expirations']['date']:
                    dte = (datetime.strptime(d_str, "%Y-%m-%d") - today).days
                    if dte_r[0] <= dte <= dte_r[1]:
                        chain = requests.get(f"{API_TRADIER}markets/options/chains", params={'symbol': sym, 'expiration': d_str, 'greeks': 'true'}, headers={'Authorization': f'Bearer {tradier_token}', 'Accept': 'application/json'}).json()
                        if not chain or 'options' not in chain or not chain['options']: continue
                        opts = chain['options']['option']
                        if isinstance(opts, dict): opts = [opts]
                        for opt in opts:
                            if opt['option_type'] == ('put' if estrategia == "Cash Secured Put (CSP)" else 'call'):
                                strike = float(opt['strike'])
                                premium = round(float((opt.get('bid', 0) + opt.get('ask', 0)) / 2), 2)
                                if estrategia == "Cash Secured Put (CSP)":
                                    cap_r = (strike - premium) * 100
                                    if cap_r > max_cap_input: continue
                                    delta = round(float(opt.get('greeks', {}).get('delta', 0)), 2)
                                    if not (delta_r[0] <= delta <= delta_r[1]): continue
                                    base = strike
                                else:
                                    if s_obj > 0 and strike != s_obj: continue
                                    delta, base = 0.0, (c_base if c_base > 0 else price)
                                
                                if f_sma and sma200 and strike >= sma200: continue
                                if f_stoch and stoch_v >= 30: continue
                                roi_a = round(((premium / base) * 100) * (365 / max(dte, 1)), 2)
                                if roi_a >= roi_min_f:
                                    res_list.append({"Ticker": sym, "Exp": d_str, "DTE": dte, "Precio": price, "Strike": strike, "Prima": premium, "Ret. %": round((premium/base)*100, 2), "ROI Ann %": roi_a, "Delta": delta, "POP %": round((1 + delta)*100, 2), "BE": round(strike - premium if estrategia == "Cash Secured Put (CSP)" else price - premium, 2), "Earnings": "SÍ" if e_date and d_str >= e_date >= today.strftime('%Y-%m-%d') else "NO", "Stoch": stoch_v, "sma200_val": sma200, "sma40_val": sma40, "atr_val": atr_v, "hv": hv_v, "iv": (opt.get('greeks', {}).get('mid_iv', 0) * 100) if isinstance(opt.get('greeks'), dict) else 0.0})
            except: continue
            prog.progress((idx + 1) / len(tickers_lista))
        st.session_state['res'] = pd.DataFrame(res_list)

    if 'res' in st.session_state and not st.session_state['res'].empty:
        df = st.session_state['res']
        df_v = df.copy()
        df_v['SMA 200'] = df_v.apply(lambda r: "✅" if r['sma200_val'] and r['Strike'] < r['sma200_val'] else "⚠️", axis=1)
        df_v['Stoch 📉'] = df_v['Stoch'].map(lambda v: "✅" if v < 30 else "⚠️")
        event = st.dataframe(df_v[["Ticker", "Exp", "DTE", "Precio", "Strike", "Prima", "Ret. %", "ROI Ann %", "Delta", "POP %", "BE", "Earnings", "SMA 200", "Stoch 📉"]], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        if event.selection.rows:
            row = df.iloc[event.selection.rows[0]]
            st.divider()
            st.subheader(f"🔍 Ficha Sniper: {row['Ticker']} - Strike ${row['Strike']:,.2f}")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(f"<div class='metric-card'><b style='color:#2ecc71'>ROI ANUAL</b><br><h3>{row['ROI Ann %']}%</h3><b>DTE: {row['DTE']}</b></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><b>BLOQUEADO</b><br><h3>${(row['Strike']*100):,.2f}</h3><b>PRIMA: ${(row['Prima']*100):,.2f}</b></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><b style='color:#e74c3c'>CAPITAL RIESGO</b><br><h3>${(row['Strike'] - row['Prima']) * 100:,.2f}</h3><b>BE: ${row['BE']}</b></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='metric-card'><b>POP / STOCH</b><br><h3>{row['POP %']}%</h3><b>STOCH: {row['Stoch']}</b></div>", unsafe_allow_html=True)
            with c5: st.markdown(f"<div class='metric-card'><b>EARNINGS</b><br><h3>{row['Earnings']}</h3></div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='vola-master'><h3>📡 Radar: IV {row['iv']:,.2f}% | HV {row['hv']:,.2f}% | ATR ${row['atr_val']}</h3></div>", unsafe_allow_html=True)
            
            if st.button(f"📊 Análisis de Negocio {row['Ticker']}"):
                av = get_hybrid_overview(row['Ticker'], av_key)
                if av: st.write(av)

            # Gráfico de Payoff
            x = np.linspace(row['BE'] * 0.8, row['Precio'] * 1.2, 300)
            y = np.where(x >= row['Strike'], row['Prima'] * 100, (x - row['Strike'] + row['Prima']) * 100)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x, y=y, name="P/L", line=dict(color='#2ecc71', width=4)))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

