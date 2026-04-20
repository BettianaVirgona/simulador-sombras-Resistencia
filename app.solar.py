import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Analizador Solar UTN - Resistencia", layout="wide")

# Datos geográficos de Resistencia, Chaco
LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Cilíndrica Interactiva - UTN FRRe")
st.markdown("Herramienta de análisis de trayectorias solares y obstrucciones de horizonte.")

# --- ESTADO DE LA SESIÓN (Base de datos de sombras) ---
if 'sombras' not in st.session_state:
    st.session_state.sombras = {}

# --- SIDEBAR: GESTIÓN DE SOMBRAS ---
st.sidebar.header("📐 Configuración de Obstáculos")

# 1. Formulario para añadir nuevas sombras
with st.sidebar.expander("➕ Añadir Nueva Sombra", expanded=True):
    nombre_nueva = st.text_input("Etiqueta", "Obstáculo")
    col_az1, col_az2 = st.columns(2)
    az_in = col_az1.number_input("Azimut Inicial", value=-90)
    az_fi = col_az2.number_input("Azimut Final", value=-60)
    
    col_h1, col_h2 = st.columns(2)
    h1 = col_h1.number_input("Altura 1 (°)", value=30.0)
    h2 = col_h2.number_input("Altura 2 (opcional)", value=0.0, help="Dejar en 0 para sombra recta")
    
    if st.button("Dibujar Sombra"):
        if nombre_nueva in st.session_state.sombras:
            st.error("Ese nombre ya existe. Usá uno diferente o editá la sombra abajo.")
        else:
            altura_final = h2 if h2 > 0 else h1
            st.session_state.sombras[nombre_nueva] = {
                "az": (az_in, az_fi),
                "h": (h1, altura_final)
            }
            st.rerun()

# 2. Lista de sombras activas (Edición y Borrado)
if st.session_state.sombras:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Sombras Activas")
    for nom in list(st.session_state.sombras.keys()):
        with st.sidebar.expander(f"📝 Editar: {nom}"):
            s = st.session_state.sombras[nom]
            new_az = st.slider(f"Rango Azimut {nom}", -180, 180, s["az"])
            new_h1 = st.number_input(f"Altura inicial {nom}", value=float(s["h"][0]), key=f"h1_{nom}")
            new_h2 = st.number_input(f"Altura final {nom}", value=float(s["h"][1]), key=f"h2_{nom}")
            
            st.session_state.sombras[nom] = {"az": new_az, "h": (new_h1, new_h2)}
            
            if st.button(f"Eliminar {nom}", key=f"del_{nom}"):
                del st.session_state.sombras[nom]
                st.rerun()

# --- CÁLCULOS DE ALTA RESOLUCIÓN ---
@st.cache_data
def obtener_datos_suaves(lat, lon):
    tiempos = pd.date_range(start='2024-01-01', end='2024-12-31 23:55', freq='5min', tz=ZONA_HORARIA)
    sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
    sol = sol[sol['elevation'] > 0]
    # Normalización del Azimut (Norte = 0)
    sol['az_plot'] = np.where(sol['azimuth'] > 180, sol['azimuth'] - 360, sol['azimuth'])
    sol['hora'] = sol.index.hour
    sol['minuto'] = sol.index.minute
    return sol

df_total = obtener_datos_suaves(LATITUD, LONGITUD)

# --- CONSTRUCCIÓN DEL GRÁFICO ---
fig = go.Figure()

# 1. Dibujar Sombras (Trapecios)
colores_s = ['rgba(100, 100, 100, 0.4)', 'rgba(60, 60, 60, 0.4)', 'rgba(150, 150, 150, 0.4)']
for i, (nombre, datos) in enumerate(st.session_state.sombras.items()):
    az1, az2 = datos["az"]
    h1, h2 = datos["h"]
    fig.add_trace(go.Scatter(
        x=[az1, az1, az2, az2, az1],
        y=[0, h1, h2, 0, 0],
        fill="toself",
        name=f"Sombra: {nombre}",
        fillcolor=colores_s[i % len(colores_s)],
        line=dict(color='black', width=1),
        hoverinfo="name"
    ))

# 2. Dibujar Analemas con etiquetas en el lienzo
horas_label = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
for h in horas_label:
    df_h = df_total[(df_total['hora'] == h) & (df_total['minuto'] == 0)].sort_index()
    if not df_h.empty:
        fig.add_trace(go.Scatter(
            x=df_h['az_plot'], y=df_h['elevation'],
            mode='lines', line=dict(color='rgba(0,0,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='skip'
        ))
        # Etiqueta de hora
        punto = df_h.loc[df_h['elevation'].idxmax()]
        fig.add_annotation(x=punto['az_plot'], y=punto['elevation'], text=f"{h}h", 
                           showarrow=False, font=dict(color="blue", size=10), yshift=10)

# 3. Dibujar Meses Agrupados (Simetría Solar)
grupos_meses = [
    {'m': [6],      'nom': 'Junio (21)',   'col': '#1f77b4'}, # Invierno
    {'m': [5, 7],   'nom': 'May-Jul (21)', 'col': '#9467bd'},
    {'m': [4, 8],   'nom': 'Abr-Ago (21)', 'col': '#d62728'},
    {'m': [3, 9],   'nom': 'Mar-Sep (21)', 'col': '#2ca02c'}, # Equinoccios
    {'m': [2, 10],  'nom': 'Feb-Oct (21)', 'col': '#ffbb78'},
    {'m': [1, 11, 12], 'nom': 'Nov-Dic-Ene (21)', 'col': '#ff7f0e'} # Verano
]

for g in grupos_meses:
    m_ref = g['m'][0]
    df_m = df_total[(df_total.index.month == m_ref) & (df_total.index.day == 21)].sort_values('az_plot')
    if not df_m.empty:
        fig.add_trace(go.Scatter(
            x=df_m['az_plot'], y=df_m['elevation'],
            mode='lines', name=g['nom'], line=dict(color=g['col'], width=3)
        ))

# --- ESTÉTICA Y EJES ---
fig.update_layout(
    xaxis=dict(
        title="Acimut Solar [°] (-180=S, -90=E, 0=N, 90=O, 180=S)",
        range=[-180, 180], dtick=30, gridcolor='lightgray', zerolinecolor='black'
    ),
    yaxis=dict(title="Elevación Solar [°]", range=[0, 90], dtick=10, gridcolor='lightgray'),
    template="plotly_white", height=750,
    legend=dict(title="<b>Referencias</b>", orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=60, r=160, t=50, b=50)
)

st.plotly_chart(fig, use_container_width=True)
