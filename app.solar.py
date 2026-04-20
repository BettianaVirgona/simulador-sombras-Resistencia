import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="App Solar Interactiva - Resistencia", layout="wide")

# Datos de Resistencia, Chaco
LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Interactiva: Resistencia, Chaco")
st.markdown("Configurá tus propios obstáculos y visualizá la trayectoria solar.")

# --- ESTADO DE LA SESIÓN (Para guardar sombras) ---
if 'sombras' not in st.session_state:
    st.session_state.sombras = []

# --- SIDEBAR: GESTIÓN DE SOMBRAS ---
st.sidebar.header("📂 Gestión de Sombras")

with st.sidebar.expander("➕ Agregar Nueva Sombra", expanded=True):
    nombre_obj = st.text_input("Nombre del objeto", placeholder="Ej: Árbol, Edificio...")
    
    # Rango de Azimut de -180 a 180
    col1, col2 = st.columns(2)
    with col1:
        az_inicio = st.number_input("Azimut Inicio (°)", min_value=-180, max_value=180, value=-45)
    with col2:
        az_fin = st.number_input("Azimut Fin (°)", min_value=-180, max_value=180, value=45)
        
    alt_obj = st.number_input("Ángulo de Elevación (°)", min_value=0, max_value=90, value=20)
    
    if st.button("Guardar Objeto"):
        if nombre_obj:
            st.session_state.sombras.append({
                "nombre": nombre_obj,
                "az_range": (az_inicio, az_fin),
                "alt": alt_obj
            })
            st.rerun()
        else:
            st.error("Por favor, ponele un nombre al objeto.")

if st.sidebar.button("🗑️ Borrar todas las sombras"):
    st.session_state.sombras = []
    st.rerun()

# --- CÁLCULOS SOLARES ---
@st.cache_data
def obtener_datos_resistencia(lat, lon):
    # Generamos datos para solsticios y equinoccios
    fechas = ['2024-06-21', '2024-09-21', '2024-12-21']
    etiquetas = ['Solsticio Invierno', 'Equinoccio', 'Solsticio Verano']
    colores = ['#1f77b4', '#2ca02c', '#ff7f0e']
    
    resultados = []
    for fecha, etiqueta, color in zip(fechas, etiquetas, colores):
        tiempos = pd.date_range(start=f'{fecha} 06:00', end=f'{fecha} 20:00', freq='10min', tz=ZONA_HORARIA)
        sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
        sol = sol[sol['elevation'] > 0]
        
        # CONVERSIÓN DE AZIMUT: pvlib usa 0=Norte, 180=Sur. 
        # Para pasar a rango -180 a 180 donde 0 es el Sur:
        sol['az_plot'] = sol['azimuth'] - 180
        
        sol['etiqueta'] = etiqueta
        sol['color'] = color
        resultados.append(sol)
    return resultados

trayectorias = obtener_datos_resistencia(LATITUD, LONGITUD)

# --- GRÁFICO INTERACTIVO ---
fig = go.Figure()

# 1. Dibujar Sombras del Usuario
for s in st.session_state.sombras:
    az_min, az_max = s["az_range"]
    alt = s["alt"]
    
    fig.add_trace(go.Scatter(
        x=[az_min, az_min, az_max, az_max, az_min],
        y=[0, alt, alt, 0, 0],
        fill="toself",
        name=s["nombre"],
        opacity=0.5,
        line=dict(width=1)
    ))

# 2. Dibujar Trayectorias Solares
for df in trayectorias:
    fig.add_trace(go.Scatter(
        x=df['az_plot'],
        y=df['elevation'],
        mode='lines',
        name=df['etiqueta'].iloc[0],
        line=dict(color=df['color'].iloc[0], width=3)
    ))

# 3. Configuración de Ejes
fig.update_layout(
    xaxis=dict(
        title="Azimut Solar [°] (0° = Sur)",
        range=[-180, 180],
        tickvals=[-180, -135, -90, -45, 0, 45, 90, 135, 180],
        ticktext=['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO', 'N']
    ),
    yaxis=dict(title="Elevación Solar [°]", range=[0, 90]),
    template="plotly_white",
    height=650,
    hovermode="closest"
)

st.plotly_chart(fig, use_container_width=True)

# --- LISTADO DE OBJETOS ---
if st.session_state.sombras:
    st.subheader("📋 Objetos en la Escena")
    st.table(pd.DataFrame([
        {"Nombre": s["nombre"], "Azimut": f"{s['az_range'][0]}° a {s['az_range'][1]}°", "Altura": f"{s['alt']}°"} 
        for s in st.session_state.sombras
    ]))
