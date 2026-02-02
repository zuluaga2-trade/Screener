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
                # ESTA LÍNEA ES LA CLAVE:
                # Intenta leer de Secrets, si no encuentra nada, el diccionario está vacío {}
                db_usuarios = st.secrets.get("usuarios", {})
                
                # Verificamos si el usuario existe en los Secrets y si la clave coincide
                if u in db_usuarios and str(db_usuarios[u]) == p:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = u
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas o usuario no registrado.")
        st.stop()

# --- 2. CONFIGURACIÓN INICIAL (ESTO DEBE IR PRIMERO) ---
st.set_page_config(page_title="Alpha Hunter Premium Elite", layout="wide")

# Lanzamos el muro
login_sistema()

# --- 3. TU ESTILO ORIGINAL (EL DISEÑO HERMOSO) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .metric-card { background-color: #1b212c; padding: 20px; border-radius: 12px; border: 1px solid #30363d; text-align: center; min-height: 140px; }
    .fundamental-box { background-color: #0d1117; border: 1px solid #00f2ff; padding: 20px; border-radius: 10px; margin-top: 10px; }
    .vola-master { background: linear-gradient(90deg, #2c1a4d 0%, #161b22 100%); border-left: 8px solid #9b59b6; padding: 25px; border-radius: 15px; margin: 20px 0; border-top: 1px solid #30363d; border-right: 1px solid #30363d; box-shadow: 5px 5px 15px rgba(0,0,0,0.5); }
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-danger { color: #e74c3c; font-weight: bold; }
    .tooltip { position: relative; display: inline-block; cursor: help; border-bottom: 2px dotted #00f2ff; color: #00f2ff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# A PARTIR DE AQUÍ SIGUE TU CÓDIGO DE PERSISTENCIA (def save_data, etc.)

import streamlit as st
import pandas as pd
import requests
import os
import plotly.graph_objects as go
import numpy as np
import io
import yfinance as yf  # <-- PARCHE: Importación necesaria
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE ESTILO ---
st.set_page_config(page_title="Alpha Hunter Premium Elite", layout="wide")
login_sistema()
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .metric-card { background-color: #1b212c; padding: 20px; border-radius: 12px; border: 1px solid #30363d; text-align: center; min-height: 140px; }
    .fundamental-box { background-color: #0d1117; border: 1px solid #00f2ff; padding: 20px; border-radius: 10px; margin-top: 10px; }
    .vola-master { background: linear-gradient(90deg, #2c1a4d 0%, #161b22 100%); border-left: 8px solid #9b59b6; padding: 25px; border-radius: 15px; margin: 20px 0; border-top: 1px solid #30363d; border-right: 1px solid #30363d; box-shadow: 5px 5px 15px rgba(0,0,0,0.5); }
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-danger { color: #e74c3c; font-weight: bold; }
    .tooltip { position: relative; display: inline-block; cursor: help; border-bottom: 2px dotted #00f2ff; color: #00f2ff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENCIA PERSONALIZADA POR USUARIO ---
def get_user_path(base_name):
    # Crea un nombre de archivo único para cada usuario (ej. .jose_tradier_token)
    usuario_id = st.session_state.get("usuario", "default").lower()
    return f".{usuario_id}_{base_name}"

def save_data(f_name, content): 
    path = get_user_path(f_name)
    with open(path, "w") as file: 
        file.write(content)

def load_data(f_name, default=""): 
    path = get_user_path(f_name)
    return open(path, "r").read().strip() if os.path.exists(path) else default

# --- 3. BARRA LATERAL (DATOS DEL USUARIO) ---
st.sidebar.title("🚀 Centro de Mando")
st.sidebar.write(f"👤 Usuario: **{st.session_state.get('usuario', 'Invitado')}**")

# Cargamos las claves específicas del usuario actual
tradier_token = st.sidebar.text_input("Tradier Token", value=load_data("tradier_token"), type="password")
av_key = st.sidebar.text_input("Alpha Vantage Key", value=load_data("av_key"), type="password")

# Botón para guardar las llaves de forma permanente para este usuario
if st.sidebar.button("💾 Guardar mis Credenciales"):
    save_data("tradier_token", tradier_token)
    save_data("av_key", av_key)
    st.sidebar.success("¡Credenciales guardadas!")

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
f_earnings = st.sidebar.toggle("Evitar Earnings (Solo NO) 🚫", value=False) # <--- NUEVA OPCIÓN

# --- 4. DASHBOARD DE PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 SCREENER PROFESIONAL", "🏗️ BÚNKER DE TICKERS", "🧠 ACADEMIA DE VOLATILIDAD", "📖 GUÍA DE INICIO"])

with tab2:
    st.subheader("⚙️ Configuración del Búnker")
    # Lista por defecto si el archivo está vacío
    def_list = "AAPL,ADBE,AGQ,AMD,AMDL,AMZN,ANET,ARM,AVGO,BA,BITO,COST,CRM,DIS,FTNT,GOOGL,HIMS,JNJ,LULU,META,MSFL,MSFT,NAIL,NKE,NOW,NVDA,NVDL,NVO,PLTR,SOXL,TECL,TLT,TQQQ,TSLA,TSLL,UNH"
    
    # Cargamos la lista actual del usuario
    current_watchlist = load_data("watchlist", def_list)
    
    # Área de texto para editar
    user_list = st.text_area("Edita la lista de fundamentales (separada por coma):", value=current_watchlist, height=150)
    
    # BOTÓN CLAVE: Solo guarda cuando el usuario hace clic
    if st.button("💾 Guardar Mi Búnker Personalizado"):
        save_data("watchlist", user_list)
        st.success("✅ ¡Lista guardada correctamente para tu usuario!")
        st.rerun() # Forzamos recarga para que el screener vea los cambios
    
    # Visualización de los tickers actuales
    tickers_clean = sorted(list(set([x.strip().upper() for x in user_list.split(",") if x.strip()])))
    st.divider()
    cols = st.columns(6)
    for i, t in enumerate(tickers_clean): 
        cols[i % 6].caption(f"🔹 {t}")

with tab3:
    st.subheader("📖 Manual Estratégico de Volatilidad")
    st.markdown("""
    Para operar como un profesional, debes entender que la **Volatilidad** es el precio del miedo.
    
    - **IV Rank:** Indica en qué percentil está la IV actual respecto al último año. Si es **> 50%**, las primas están inusualmente caras.
    - **ATR (Average True Range):** Define el 'ruido' diario. Si tu Strike está a menos de 2 ATRs del precio, tienes alta probabilidad de ser asignado.
    - **HV (Volatilidad Histórica):** El movimiento real. Si **IV > HV**, existe una 'Prima de Riesgo' que el vendedor captura a su favor.
    
    **Ejemplo Real:**
    - Acción a $150. Strike a $130. ATR es $3.00.
    - Estás a $20 de distancia, lo que equivale a casi **7 días de ATR**. Si la IV es mayor que la HV y no hay Earnings, la probabilidad de éxito es masiva.
    """)

with tab4:
    st.header("🚀 Guía de Inicio Rápido")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("🔑 1. Configuración de Keys")
        st.markdown("""
        Para que el sistema funcione, necesitas conectar con los proveedores de datos:
        * **Tradier Brokerage:** Es de donde obtenemos los precios de opciones en tiempo real. 
            1. Crea una cuenta en [Tradier](https://tradier.com/).
            2. En tu dashboard, busca 'API Settings' y genera un **Access Token**.
            3. Pégalo en la barra lateral y dale a **Guardar**.
        * **Alpha Vantage:** Proporciona el calendario de Earnings y datos fundamentales.
            1. Solicita una key gratuita en [Alpha Vantage](https://www.alphavantage.co/support/#api-key).
            2. Pégala en la barra lateral y dale a **Guardar**.
        """)
        
    with col_g2:
        st.subheader("🎯 2. Estrategias Básicas")
        st.info("**Cash Secured Put (CSP):** Vendes el derecho a que alguien te venda acciones a un precio más bajo (Strike). Cobras una renta hoy. Si la acción baja del strike, compras las acciones con descuento.")
        st.info("**Covered Call (CC):** Si ya tienes 100 acciones, vendes el derecho a que alguien te las compre a un precio más alto. Cobras la renta mientras esperas que suban.")

    st.divider()
    
    st.subheader("🛠️ 3. Cómo usar el Screener")
    st.markdown("""
    1.  **Selecciona tu Búnker:** Ve a la pestaña 'Búnker' y pega los tickers de las empresas que te gustaría ser dueño (ej: AAPL, MSFT, NVDA).
    2.  **Ajusta tus filtros:** En la barra lateral, define el **DTE** (días a expiración, recomendado 30-45) y el **ROI Anualizado** que buscas.
    3.  **Inicia el Barrido:** Presiona el botón de cohete. El sistema buscará entre miles de contratos cuáles cumplen con tus filtros técnicos (SMA 200, Stoch, Delta).
    4.  **Analiza la Ficha Sniper:** Haz clic en una fila para ver el análisis detallado, el riesgo de capital y el gráfico de ganancias/pérdidas.
    """)
    
    st.success("💡 **Consejo Pro:** Mira siempre el **IV vs HV** en el Radar de Volatilidad. Si la IV es mayor, te están pagando una prima 'cara', lo cual es ideal para vendedores.")
def generar_texto_compartir(row, estrategia):
    texto = f"🦅 *ALPHA HUNTER ELITE - ALERTA DE POSICIÓN*\n\n"
    texto += f"🎯 **Ticker:** {row['Ticker']}\n"
    texto += f"🛠 **Estrategia:** {estrategia}\n"
    texto += f"📅 **Expira:** {row['Exp']} ({row['DTE']} DTE)\n"
    texto += f"💰 **Strike:** ${row['Strike']}\n"
    texto += f"💵 **Prima:** ${row['Prima']}\n"
    texto += f"📈 **ROI Anual:** {row['ROI Ann %']}%\n"
    texto += f"🛡 **Breakeven:** ${row['BE']}\n"
    texto += f"📊 **POP:** {row['POP %']}%\n"
    texto += f"\n🔥 *Análisis generado por Alpha Hunter Elite*"
    return texto
# --- 5. MOTORES DE DATOS (CON PARCHE DE REDUNDANCIA) ---
@st.cache_data(ttl=86400)
def sync_global_earnings(key):
    try:
        r = requests.get(f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={key}', timeout=15)
        return pd.read_csv(io.StringIO(r.text)).set_index('symbol')['reportDate'].to_dict()
    except: return {}

@st.cache_data(ttl=86400)
def get_hybrid_overview(sym, key): # <-- PARCHE: Función híbrida
    # Intento 1: Alpha Vantage
    try:
        r = requests.get(f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={sym}&apikey={key}', timeout=8).json()
        if "Symbol" in r and float(r.get('AnalystTargetPrice', 0)) > 0:
            return {
                "target": round(float(r.get('AnalystTargetPrice', 0)), 2),
                "margin": round(float(r.get('OperatingMarginTTM', 0)) * 100, 2),
                "roe": round(float(r.get('ReturnOnEquityTTM', 0)) * 100, 2),
                "debt": round(float(r.get('DebtToEquityRatio', 0)), 2),
                "source": "Alpha Vantage"
            }
    except: pass
    
    # Intento 2: yFinance (Respaldo)
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

# --- 6. SCREENER ---
    with tab1:
        CATEGORIAS = {
            "🛡️ MI BÚNKER": tickers_clean,
            "📊 ETFs & Índices": ["SPY", "QQQ", "IWM", "DIA", "TLT", "XLF", "XLE", "XLK", "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLC", "EEM", "EWZ", "FXI", "SLV", "GLD"],
            "🚀 HIGH VOL": ["TSLA", "NVDA", "MSTR", "MARA", "COIN", "PLTR", "AMD", "SMCI", "ARM", "SOXL", "TQQQ", "SQ", "ROKU", "GME", "AMC", "NIO", "AFRM", "HOOD", "PATH", "SHOP"],
            "💻 TECNOLOGÍA": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "AVGO", "ORCL", "CRM", "INTC", "CSCO", "ADBE", "TXN", "QCOM", "AMAT", "MU", "LRCX", "NOW", "PANW", "SNPS", "CDNS"],
            "🛍️ CONSUMO": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "COST", "WMT", "TGT", "LOW", "BKNG", "LULU", "TJX", "ORLY", "MAR", "EL", "PG", "KO", "PEP", "PM"],
            "💊 SALUD": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "ISRG", "AMGN", "CVS", "BMY", "GILD", "MRNA", "VRTX", "REGN", "HUM", "CI", "ELV"],
            "🏦 FINANZAS": ["JPM", "BAC", "V", "MA", "WFC", "MS", "GS", "AXP", "C", "PYPL", "SQ", "BLK", "BX", "SCHW", "SOFI", "CB", "PGR", "MMC", "AON", "USB"],
            "🏗️ INDUSTRIAL": ["BA", "CAT", "GE", "UNP", "HON", "UPS", "FDX", "LMT", "RTX", "DE", "MMM", "WM", "NSC", "ETN", "ITW", "EMR", "ADM", "GEV", "GD", "NOC"],
            "🛢️ ENERGÍA": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "PSX", "VLO", "HES", "BKR", "HAL", "DVN", "FANG", "WMB", "OKE", "LNG", "ET", "KMI", "PBR"],
            "🏢 INMOBILIARIO": ["PLD", "AMT", "EQIX", "CCI", "WY", "SPG", "O", "WELL", "PSA", "DLR", "VICI", "AVB", "EQR", "CBRE", "ARE", "EXR", "VRE", "FRT", "SBAC", "BXP"],
            "⛏️ MATERIALES": ["LIN", "APD", "NEM", "FCX", "SHW", "CTVA", "ECL", "ALB", "DOW", "LYB", "NUE", "MLM", "VMC", "RIO", "VALE", "MOS", "FMC", "IFF", "EMN", "SMG"],
            "🔌 UTILITIES": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PCG", "PEG", "ED", "WEC", "XEL", "AWK", "EIX", "ES", "FE", "DTE", "PPL", "CNP", "LNT"],
            "📡 COMUNICACIONES": ["GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "T", "CHTR", "WBD", "PARA", "ROKU", "SNAP", "PINS", "BIDU", "SPOT", "EA", "TTWO", "SHOP", "MTCH"],
            "🎯 INDIVIDUAL": ["CUSTOM"]
        }
    
    c_s1, c_s2 = st.columns([2, 1])
    sector_sel = c_s1.selectbox("Sector de Escaneo", list(CATEGORIAS.keys()))
    tickers_lista = [c_s2.text_input("Ticker", "NVDA").upper()] if sector_sel == "🎯 INDIVIDUAL" or estrategia == "Covered Call (CC)" else CATEGORIAS[sector_sel]

    earnings_db = sync_global_earnings(av_key) if av_key else {}
    if st.button("🚀 INICIAR BARRIDO"):
        res_list = []
        prog = st.progress(0)
        today = datetime.now()
        for idx, sym in enumerate(tickers_lista):
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
                            bid_price = opt.get('bid') if opt.get('bid') is not None else 0
                            ask_price = opt.get('ask') if opt.get('ask') is not None else 0
                            premium = round(float((bid_price + ask_price) / 2), 2)
                            if estrategia == "Cash Secured Put (CSP)":
                                cap_r = round((strike - premium) * 100, 2)
                                if cap_r > max_cap_input: continue
                                delta = round(float(opt.get('greeks', {}).get('delta', 0)), 2)
                                if not (delta_r[0] <= delta <= delta_r[1]): continue
                                base = strike
                            else:
                                if s_obj > 0 and strike != s_obj: continue
                                delta, base = 0.0, (c_base if c_base > 0 else price)
                            
                            if f_sma and sma200 and strike >= sma200: continue
                            if f_stoch and stoch_v >= 30: continue
                            
                            # NUEVO FILTRO DE EARNINGS
                            es_earnings = "SÍ" if e_date and d_str >= e_date >= today.strftime('%Y-%m-%d') else "NO"
                            if f_earnings and es_earnings == "SÍ": continue
                            
                            roi_a = round(((premium / base) * 100) * (365 / max(dte, 1)), 2)
                            if roi_a >= roi_min_f:
                                res_list.append({
                                    "Ticker": sym, "Exp": d_str, "DTE": dte, "Precio": price, "Strike": strike, "Prima": premium, 
                                    "Ret. %": round((premium/base)*100, 2), "ROI Ann %": roi_a, "Delta": delta, 
                                    "POP %": round((1 + delta)*100, 2), "BE": round(strike - premium if estrategia == "Cash Secured Put (CSP)" else price - premium, 2),
                                    "Earnings": "SÍ" if e_date and d_str >= e_date >= today.strftime('%Y-%m-%d') else "NO", 
                                    "earn_date": e_date, "Stoch": stoch_v, "sma200_val": sma200, "sma40_val": sma40, "atr_val": atr_v, "hv": hv_v,
                                    "iv": (opt.get('greeks', {}).get('mid_iv', 0) * 100) if isinstance(opt.get('greeks'), dict) else 0.0
                                })
            prog.progress((idx + 1) / len(tickers_lista))
        st.session_state['res'] = pd.DataFrame(res_list)

    if 'res' in st.session_state and not st.session_state['res'].empty:
        df = st.session_state['res']
        df_v = df.copy()
        df_v['SMA 200'] = df_v.apply(lambda r: "✅" if r['sma200_val'] and r['Strike'] < r['sma200_val'] else "⚠️", axis=1)
        df_v['Stoch 📉'] = df_v['Stoch'].map(lambda v: "✅" if v < 30 else "⚠️")
        for col in ["Precio", "Strike", "Prima", "BE", "Delta", "ROI Ann %", "Ret. %", "POP %"]:
            df_v[col] = df_v[col].map("{:,.2f}".format)
        
        event = st.dataframe(df_v[["Ticker", "Exp", "DTE", "Precio", "Strike", "Prima", "Ret. %", "ROI Ann %", "Delta", "POP %", "BE", "Earnings", "SMA 200", "Stoch 📉"]].style.map(lambda v: f'background-color: {"#721c24" if v == "SÍ" else "#155724"}; color: white', subset=['Earnings']), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        if event.selection.rows and estrategia == "Cash Secured Put (CSP)":
            row = df.iloc[event.selection.rows[0]]
            st.divider()
            st.subheader(f"🔍 Ficha Sniper: {row['Ticker']} - Strike ${row['Strike']:,.2f}")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(f"<div class='metric-card'><b style='color:#2ecc71'>ROI ANUAL</b><br><h3>{row['ROI Ann %']:,.2f}%</h3><b>DTE: {row['DTE']}</b></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><b>BLOQUEADO</b><br><h3>${(row['Strike']*100):,.2f}</h3><b>PRIMA: ${(row['Prima']*100):,.2f}</b></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><b style='color:#e74c3c'>CAPITAL RIESGO</b><br><h3>${(row['Strike'] - row['Prima']) * 100:,.2f}</h3><b>BE: ${row['BE']:,.2f}</b></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='metric-card'><b>POP / STOCH</b><br><h3>{row['POP %']:,.2f}%</h3><b>STOCH: {row['Stoch']:,.2f} {'✅' if row['Stoch'] < 30 else '⚠️'}</b></div>", unsafe_allow_html=True)
            with c5: st.markdown(f"<div class='metric-card'><b>EARNINGS / SMA40</b><br><h3 style='color:{'#e74c3c' if row['Earnings']=='SÍ' else '#2ecc71'}'>{row['Earnings']}</h3><b>SMA40: {'✅' if row['Precio'] > row['sma40_val'] else '⚠️'}</b></div>", unsafe_allow_html=True)

            st.markdown(f"""
            <div class='vola-master'>
                <h3 style='margin:0; color:#9b59b6;'>📡 Radar de Volatilidad & Riesgo</h3>
                <table style='width:100%; border-collapse: collapse; margin-top:15px;'>
                    <tr style='font-size:18px;'>
                        <td style='padding:10px;'><b>IV Actual:</b> {row['iv']:,.2f}%</td>
                        <td style='padding:10px;'><b>HV (Histórica):</b> {row['hv']:,.2f}%</td>
                        <td style='padding:10px;'><b>ATR (14D):</b> ${row['atr_val']:,.2f}</td>
                        <td style='padding:10px; background: rgba(0,242,255,0.1); border-radius:10px; text-align:center;'>
                            {'🎯 <b style="color:#2ecc71">RECOMENDACIÓN: CSP CONVENIENTE</b>' if row['iv'] > row['hv'] and row['Earnings'] == 'NO' else '⚖️ <b style="color:#f39c12">RECOMENDACIÓN: EVALUAR RIESGO</b>'}
                        </td>
                    </tr>
                </table>
            </div>""", unsafe_allow_html=True)

                 # --- SECCIÓN DE HERRAMIENTAS (CON CIERRE MANUAL) ---
            with st.expander(f"📊 Ver Análisis de Negocio para {row['Ticker']}", expanded=False):
                av = get_hybrid_overview(row['Ticker'], av_key)
                if av:
                    up = round(((av['target'] - row['Precio']) / row['Precio']) * 100, 2)
                    st.markdown(f"""
                    <div class='fundamental-box'>
                       <b>📊 Perfil Financiero (Fuente: {av['source']}):</b><br>
                        Márgenes: <b class='status-ok'>{av['margin']:,.2f}%</b> | 
                        ROE: <b class='status-ok'>{av['roe']:,.2f}%</b> | 
                        Deuda/Eq: <b class='status-ok'>{av['debt']:,.2f}</b><br>
                        Target Wall St: <b class='status-ok'>${av['target']:,.2f}</b> | 
                        Potencial: <b class='status-ok'>{up:,.2f}%</b>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.warning("No se pudieron obtener datos fundamentales.")

            with st.expander("🔗 Compartir esta Alerta", expanded=False):
                resumen_txt = generar_texto_compartir(row, estrategia)
                st.write("Copia el texto para pegarlo en WhatsApp o Telegram:")
                st.code(resumen_txt, language=None)
                st.caption("Haz clic en el icono de la derecha del cuadro gris para copiar.")

            x = np.linspace(row['BE'] * 0.8, row['Precio'] * 1.2, 300)
            y = np.where(x >= row['Strike'], row['Prima'] * 100, (x - row['Strike'] + row['Prima']) * 100)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x[x >= row['BE']], y=y[x >= row['BE']], fill='tozeroy', name='Ganancia', line=dict(color='#2ecc71', width=4)))
            fig.add_trace(go.Scatter(x=x[x < row['BE']], y=y[x < row['BE']], fill='tozeroy', name='Pérdida', line=dict(color='#e74c3c', width=4)))
            fig.add_trace(go.Scatter(x=[row['BE'], row['BE']], y=[min(y), max(y)], name="BE", line=dict(color="yellow", dash='dot')))
            fig.add_trace(go.Scatter(x=[row['Precio'], row['Precio']], y=[min(y), max(y)], name="Precio Hoy", line=dict(color="white", width=4)))
            if row['sma200_val']: fig.add_trace(go.Scatter(x=[row['sma200_val'], row['sma200_val']], y=[min(y), max(y)], name="SMA 200", line=dict(color="#3498db", dash='dash')))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Precio del Activo ($)", yaxis_title="Profit / Loss ($)")
            st.plotly_chart(fig, use_container_width=True)








