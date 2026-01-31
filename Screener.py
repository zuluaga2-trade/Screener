import streamlit as st
import pandas as pd
import requests
import os
import plotly.graph_objects as go
import numpy as np
import io
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Alpha Hunter Premium Elite", layout="wide")

# --- 2. FUNCIÓN DE LOGIN ---
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

# --- 3. ESTILO PERSONALIZADO ---
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

# --- 4. FUNCIONES DE PERSISTENCIA ---
def save_data(f, k): 
    with open(f, "w") as file: 
        file.write(k)

def load_data(f, default=""): 
    return open(f, "r").read().strip() if os.path.exists(f) else default

# --- 5. CONFIGURACIÓN Y BUNKER ---
def bunker_configuration():
    st.subheader("⚙️ Configuración del Búnker")
    def_list = "AAPL,ADBE,AGQ,AMD,AMDL,AMZN,ANET,ARM,AVGO,BA,BITO,COST,CRM,DIS,FTNT,GOOGL,HIMS,JNJ,LULU,META,MSFL,MSFT,NAIL,NKE,NOW,NVDA,NVDL,NVO,PLTR,SOXL,TECL,TLT,TQQQ,TSLA,TSLL,UNH"
    
    if "user_list" not in st.session_state:
        st.session_state.user_list = def_list

    user_list = st.text_area("Edita la lista de fundamentales (separada por coma):", value=st.session_state.user_list, height=150)
    st.session_state.user_list = user_list
    
    tickers_clean = sorted(list(set([x.strip().upper() for x in user_list.split(",") if x.strip()])))
    cols = st.columns(6)
    for i, t in enumerate(tickers_clean): 
        cols[i % 6].caption(f"🔹 {t}")

# --- 6. BARRA LATERAL ---
def sidebar_configuration():
    st.sidebar.title("🚀 Centro de Mando")
    
    tradier_token = st.sidebar.text_input("Tradier Token", value=load_data(".tradier_token"), type="password")
    av_key = st.sidebar.text_input("Alpha Vantage Key", value=load_data(".av_key"), type="password")
    
    if tradier_token: 
        save_data(".tradier_token", tradier_token)
    if av_key: 
        save_data(".av_key", av_key)

    entorno = st.sidebar.selectbox("Entorno Tradier", ["Sandbox", "Brokerage"])
    return tradier_token, av_key, entorno

# --- 7. FUNCIONALIDAD PRINCIPAL ---
def main():
    login_sistema()
    tradier_token, av_key, entorno = sidebar_configuration()
    API_TRADIER = "https://api.tradier.com/v1/" if entorno == "Brokerage" else "https://sandbox.tradier.com/v1/"

    tab1, tab2, tab3 = st.tabs(["📊 SCREENER PROFESIONAL", "🏗️ BÚNKER DE TICKERS", "🧠 ACADEMIA DE VOLATILIDAD"])

    with tab2:
        bunker_configuration()

    # Aquí puedes añadir más funcionalidades para los otros tabs
    
if __name__ == "__main__":
    main()
