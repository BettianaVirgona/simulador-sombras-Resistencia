import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Carta Solar UTN - Final", layout="wide")

LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Cilíndrica Profesional")

if 'sombras' not in st.session_state:
    st.session_state.sombras = []

# --- GESTIÓN DE OBSTÁCULOS ---
with st.sidebar.expander("Añadir Sombra", expanded=True):
    nombre = st.text_input("Etiqueta", "Edificio")
    az_in = st.number_input("Azimut Inicial", value=-90)
    az_fi = st.number_input("Azimut Final", value=-60)
    alt_h = st.number_input("Altura", value=30)
    if st.button("Dibujar"):
        st.session_state.sombras.append({"nom": nombre, "az": (az_in, az_fi), "alt": alt_h})
        st.rerun()

# --- CÁLCULOS DE ALTA RESOLUCIÓN ---
@st.cache_data
def obtener_datos_suaves(lat, lon):
    # Aumentamos la frecuencia a 5 min para que las curvas sean suaves
    tiempos = pd.date_range(start='2024-01-01', end='2024-12-31 23:55', freq='5min', tz=ZONA_HORARIA)
    sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
    sol = sol[sol['elevation'] > 0]
    
    # Normalización del Azimut (Norte = 0)
    sol['az_plot'] = np.where(sol['azimuth'] > 180, sol['azimuth'] - 360, sol['azimuth'])
    sol['hora_exacta'] = sol.index.hour
    sol['minuto'] = sol.index.minute
    return sol

df_total = obtener_datos_suaves(LATITUD, LONGITUD)

fig = go.Figure()

# 1. DIBUJAR SOMBRAS
for s in st.session_state.sombras:
    fig.add_trace(go.Scatter(
        x=[s['az'][0], s['az'][0], s['az'][1], s['az'][1], s['az'][0]],
        y=[0, s['alt'], s['alt'], 0, 0],
        fill="toself", name=s['nom'], fillcolor='rgba(100, 100, 100, 0.3)',
        line=dict(color='rgba(0,0,0,0.5)', width=1), showlegend=False
    ))

# 2. DIBUJAR ANALEMAS CON ETIQUETAS EN EL LIENZO
horas_interes = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
for h in horas_interes:
    # Filtramos exactamente la hora en punto
    df_h = df_total[(df_total['hora_exacta'] == h) & (df_total['minuto'] == 0)].sort_index()
    if not df_h.empty:
        # Dibujamos la línea del analema
        fig.add_trace(go.Scatter(
            x=df_h['az_plot'], y=df_h['elevation'],
            mode='lines',
            line=dict(color='rgba(0, 0, 255, 0.2)', width=1, dash='dot'),
            showlegend=False, hoverinfo='skip'
        ))
        
        # Agregamos la ETIQUETA de la hora en el punto más alto del analema
        punto_etiqueta = df_h.loc[df_h['elevation'].idxmax()]
        fig.add_annotation(
            x=punto_etiqueta['az_plot'], y=punto_etiqueta['elevation'],
            text=f"<b>{h}h</b>", showarrow=False,
            font=dict(size=10, color="blue"), yshift=10
        )

# 3. DIBUJAR CURVAS MENSUALES (Día 21)
meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
colores = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', 
           '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94']

for i, mes in enumerate(meses, 1):
    df_mes = df_total[(df_total.index.month == i) & (df_total.index.day == 21)].sort_values('az_plot')
    if not df_mes.empty:
        fig.add_trace(go.Scatter(
            x=df_mes['az_plot'], y=df_mes['elevation'],
            mode='lines', name=f"{mes} (21)",
            line=dict(color=colores[i-1], width=3)
        ))

# --- ESTÉTICA FINAL ---
fig.update_layout(
    xaxis=dict(title="Acimut Solar [°]", range=[-180, 180], dtick=30, gridcolor='lightgray'),
    yaxis=dict(title="Elevación Solar [°]", range=[0, 90], dtick=10, gridcolor='lightgray'),
    template="plotly_white", height=750,
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(l=60, r=160, t=50, b=50)
)

st.plotly_chart(fig, use_container_width=True)
