import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carta Solar UTN - Colector A", layout="wide")

LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Cilíndrica - Colector A")

if 'sombras' not in st.session_state:
    st.session_state.sombras = []

# --- SIDEBAR ---
st.sidebar.header("📐 Configuración de Obstáculos")
with st.sidebar.expander("Añadir Sombra", expanded=True):
    nombre = st.text_input("Nombre", "Obstáculo")
    az_in = st.number_input("Azimut Inicial", value=-180, min_value=-180, max_value=180)
    az_fi = st.number_input("Azimut Final", value=60, min_value=-180, max_value=180)
    alt_h = st.number_input("Elevación Máxima", value=40)
    
    if st.button("Dibujar Sombra"):
        st.session_state.sombras.append({"nom": nombre, "az": (az_in, az_fi), "alt": alt_h})
        st.rerun()

if st.sidebar.button("Borrar todo"):
    st.session_state.sombras = []
    st.rerun()

# --- CÁLCULO DE TRAYECTORIAS ---
@st.cache_data
def generar_curvas(lat, lon):
    meses_nombres = ['Ene (21)', 'Feb (21)', 'Mar (21)', 'Abr (21)', 'May (21)', 'Jun (21)',
                     'Jul (21)', 'Ago (21)', 'Sep (21)', 'Oct (21)', 'Nov (21)', 'Dic (21)']
    
    # Colores aproximados a tu imagen
    colores = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', 
               '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94']
    
    lineas = []
    for i, nombre in enumerate(meses_nombres):
        fecha = f'2024-{i+1:02d}-21'
        tiempos = pd.date_range(start=f'{fecha} 05:00', end=f'{fecha} 20:00', freq='5min', tz=ZONA_HORARIA)
        sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
        sol = sol[sol['elevation'] > -1] # Un margen para que llegue al horizonte
        
        # LÓGICA CLAVE PARA EL "PICO":
        # pvlib: 0=N, 90=E, 180=S, 270=O.
        # Queremos: 0=N, -90=E, -180=S, 90=O, 180=S.
        az_plot = sol['azimuth'].copy()
        az_plot = np.where(az_plot > 180, az_plot - 360, az_plot)
        
        # Ordenamos para que Plotly no trace líneas cruzadas
        df_mes = pd.DataFrame({'x': az_plot, 'y': sol['elevation']}).sort_values('x')
        
        lineas.append({'x': df_mes['x'], 'y': df_mes['y'], 'nom': nombre, 'col': colores[i]})
    return lineas

curvas = generar_curvas(LATITUD, LONGITUD)

# --- GRÁFICO ---
fig = go.Figure()

# 1. Sombras
for s in st.session_state.sombras:
    fig.add_trace(go.Scatter(
        x=[s['az'][0], s['az'][0], s['az'][1], s['az'][1], s['az'][0]],
        y=[0, s['alt'], s['alt'], 0, 0],
        fill="toself", name=s['nom'], fillcolor='rgba(128, 128, 128, 0.5)',
        line=dict(width=0), hoverinfo='name'
    ))

# 2. Curvas de los meses
for c in curvas:
    fig.add_trace(go.Scatter(
        x=c['x'], y=c['y'], mode='lines', name=c['nom'],
        line=dict(color=c['col'], width=2)
    ))

# --- AJUSTES DE EJES (IDÉNTICO A LA FOTO) ---
fig.update_layout(
    xaxis=dict(
        title="Acimut Solar [°] (-180=Sur, -90=Este, 0=Norte, 90=Oeste, 180=Sur)",
        range=[-180, 180],
        dtick=30,
        gridcolor='lightgray',
        showgrid=True,
        zeroline=True,
        zerolinecolor='black'
    ),
    yaxis=dict(
        title="Elevación Solar [°]",
        range=[0, 90],
        dtick=10,
        gridcolor='lightgray',
        showgrid=True
    ),
    template="plotly_white",
    height=700,
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=60, r=160, t=50, b=50)
)

st.plotly_chart(fig, use_container_width=True)
