import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carta Solar - UTN FRRe", layout="wide")

# Datos fijos para Resistencia
LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Cilíndrica - Analizador de Sombras")

# --- ESTADO DE LA SESIÓN ---
if 'sombras' not in st.session_state:
    st.session_state.sombras = []

# --- SIDEBAR ---
st.sidebar.header("📐 Configuración de Escena")

with st.sidebar.expander("Añadir Obstáculo", expanded=True):
    nombre = st.text_input("Etiqueta", "Edificio")
    col1, col2 = st.columns(2)
    with col1:
        az_in = st.number_input("Azimut Inicial", value=-90)
    with col2:
        az_fi = st.number_input("Azimut Final", value=-60)
    alt_h = st.number_input("Altura (Elevación)", value=30)
    
    if st.button("Agregar a la Carta"):
        st.session_state.sombras.append({"nom": nombre, "az": (az_in, az_fi), "alt": alt_h})
        st.rerun()

if st.sidebar.button("Limpiar todo"):
    st.session_state.sombras = []
    st.rerun()

# --- CÁLCULO DE TRAYECTORIAS (LOS 12 MESES) ---
@st.cache_data
def generar_curvas_meses(lat, lon):
    meses_nombres = ['Ene (21)', 'Feb (21)', 'Mar (21)', 'Abr (21)', 'May (21)', 'Jun (21)',
                     'Jul (21)', 'Ago (21)', 'Sep (21)', 'Oct (21)', 'Nov (21)', 'Dic (21)']
    colores = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', 
               '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94']
    
    lineas = []
    for i, nombre in enumerate(meses_nombres):
        fecha = f'2024-{i+1:02d}-21'
        tiempos = pd.date_range(start=f'{fecha} 05:00', end=f'{fecha} 20:00', freq='10min', tz=ZONA_HORARIA)
        sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
        sol = sol[sol['elevation'] > 0]
        
        # Ajuste de Azimut: pvlib (180=Sur) -> Queremos 0=Sur? 
        # En tu imagen: -180=Sur, -90=Este, 0=Norte, 90=Oeste, 180=Sur
        # Calculamos según la escala de tu imagen:
        az_plot = sol['azimuth'] - 180 
        
        lineas.append({'x': az_plot, 'y': sol['elevation'], 'nom': nombre, 'col': colores[i]})
    return lineas

curvas = generar_curvas_meses(LATITUD, LONGITUD)

# --- GRÁFICO ---
fig = go.Figure()

# 1. Dibujar Sombras
for s in st.session_state.sombras:
    fig.add_trace(go.Scatter(
        x=[s['az'][0], s['az'][0], s['az'][1], s['az'][1], s['az'][0]],
        y=[0, s['alt'], s['alt'], 0, 0],
        fill="toself", name=s['nom'], opacity=0.6,
        line=dict(width=1, color="black")
    ))

# 2. Dibujar las curvas de los meses
for c in curvas:
    fig.add_trace(go.Scatter(
        x=c['x'], y=c['y'], mode='lines',
        name=c['nom'], line=dict(color=c['col'], width=2.5)
    ))

# 3. ESTÉTICA IGUAL A TU IMAGEN (Eje X de 30 en 30)
fig.update_layout(
    xaxis=dict(
        title="Acimut Solar [°] (-180=Sur, -90=Este, 0=Norte, 90=Oeste, 180=Sur)",
        range=[-180, 180],
        dtick=30, # Divisiones cada 30 grados
        gridcolor='lightgray',
        zerolinecolor='black'
    ),
    yaxis=dict(
        title="Elevación Solar [°]",
        range=[0, 90],
        dtick=10,
        gridcolor='lightgray'
    ),
    template="plotly_white",
    height=700,
    legend=dict(title="Meses (21)", orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=50, r=150, t=50, b=50)
)

st.plotly_chart(fig, use_container_width=True)
