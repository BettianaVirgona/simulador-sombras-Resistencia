import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Carta Solar Interactiva", layout="wide")

LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Interactiva - Resistencia, Chaco")

if 'sombras' not in st.session_state:
    st.session_state.sombras = []

# --- SIDEBAR (IGUAL AL ANTERIOR) ---
st.sidebar.header("📐 Configuración de Obstáculos")
with st.sidebar.expander("Añadir Sombra", expanded=True):
    nombre = st.text_input("Nombre", "Obstáculo")
    az_in = st.number_input("Azimut Inicial", value=-90)
    az_fi = st.number_input("Azimut Final", value=-60)
    alt_h = st.number_input("Elevación Máxima", value=30)
    if st.button("Dibujar Sombra"):
        st.session_state.sombras.append({"nom": nombre, "az": (az_in, az_fi), "alt": alt_h})
        st.rerun()

# --- CÁLCULO DE DATOS (MESES Y ANALEMAS) ---
@st.cache_data
def obtener_todo_el_anio(lat, lon):
    # Rango de todo el año para los analemas
    tiempos_anio = pd.date_range(start='2024-01-01', end='2024-12-31 23:59', freq='60min', tz=ZONA_HORARIA)
    sol_anio = pvlib.solarposition.get_solarposition(tiempos_anio, lat, lon)
    sol_anio = sol_anio[sol_anio['elevation'] > 0]
    
    # Normalizar Azimut para el "Pico" en 0 (Norte)
    sol_anio['az_plot'] = np.where(sol_anio['azimuth'] > 180, sol_anio['azimuth'] - 360, sol_anio['azimuth'])
    sol_anio['hora'] = sol_anio.index.hour
    
    return sol_anio

df_total = obtener_todo_el_anio(LATITUD, LONGITUD)

# --- GRÁFICO ---
fig = go.Figure()

# 1. Dibujar Sombras
for s in st.session_state.sombras:
    fig.add_trace(go.Scatter(
        x=[s['az'][0], s['az'][0], s['az'][1], s['az'][1], s['az'][0]],
        y=[0, s['alt'], s['alt'], 0, 0],
        fill="toself", name=s['nom'], fillcolor='rgba(128, 128, 128, 0.4)',
        line=dict(width=1, color="gray"), hoverinfo='name'
    ))

# 2. Dibujar ANALEMAS (Las curvas de las horas)
# Elegimos las horas más importantes para no saturar
horas_analema = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
for h in horas_analema:
    df_h = df_total[df_total['hora'] == h].sort_index()
    if not df_h.empty:
        fig.add_trace(go.Scatter(
            x=df_h['az_plot'], y=df_h['elevation'],
            mode='lines',
            name=f"{h}:00 hs",
            line=dict(color='rgba(100, 100, 255, 0.4)', width=1, dash='dot'),
            hoverinfo='name'
        ))

# 3. Dibujar Meses (Líneas gruesas)
meses_nombres = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 
                 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
colores = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', 
           '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94']

for i in range(1, 13):
    # Filtramos el día 21 de cada mes
    df_mes = df_total[(df_total.index.month == i) & (df_total.index.day == 21)].sort_values('az_plot')
    if not df_mes.empty:
        fig.add_trace(go.Scatter(
            x=df_mes['az_plot'], y=df_mes['elevation'],
            mode='lines',
            name=f"{meses_nombres[i]} (21)",
            line=dict(color=colores[i-1], width=2.5)
        ))

# --- AJUSTES FINALES ---
fig.update_layout(
    xaxis=dict(title="Acimut Solar [°]", range=[-180, 180], dtick=30, gridcolor='lightgray'),
    yaxis=dict(title="Elevación Solar [°]", range=[0, 90], dtick=10, gridcolor='lightgray'),
    template="plotly_white", height=750,
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=60, r=160, t=50, b=50)
)

st.plotly_chart(fig, use_container_width=True)
