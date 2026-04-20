import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Solar Interactiva UTN", layout="wide")

# Datos fijos de Resistencia (podes hacerlos variables si querés)
LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Analizador de Sombras y Carta Solar")
st.sidebar.header("🔧 Parámetros de Simulación")

# --- FUNCION DE CALCULO ---
@st.cache_data
def obtener_datos_anuales(lat, lon):
    # Generamos un rango de todo el año cada 30 min
    tiempos = pd.date_range(start='2024-01-01', end='2024-12-31 23:00', freq='30min', tz=ZONA_HORARIA)
    sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
    sol = sol[sol['elevation'] > 0] # Solo cuando hay sol
    sol['hora'] = sol.index.hour
    sol['mes'] = sol.index.month
    return sol

df_sol = obtener_datos_anuales(LATITUD, LONGITUD)

# --- INTERFAZ DE SOMBRAS ---
st.sidebar.subheader("Edificios y Obstáculos")
def configurar_obstaculo(nombre, az_def, alt_def):
    with st.sidebar.expander(f"Configurar {nombre}"):
        az = st.slider(f"Azimut {nombre}", 0, 360, az_def)
        alt = st.slider(f"Altura {nombre}", 0, 90, alt_def)
        return az, alt

# Aquí definimos los obstáculos que tenías en tu código original
az_anexo, alt_anexo = configurar_obstaculo("Anexo/Lab", (0, 60), 6)
az_db, alt_db = configurar_obstaculo("Club Don Bosco", (60, 85), 25)
az_euc, alt_euc = configurar_obstaculo("Eucalipto", (270, 300), 29)

# --- CREACIÓN DEL GRÁFICO ---
fig = go.Figure()

# 1. Dibujar Sombras (Rectángulos)
def agregar_sombra(fig, az_range, alt_max, nombre, color):
    fig.add_trace(go.Scatter(
        x=[az_range[0], az_range[0], az_range[1], az_range[1], az_range[0]],
        y=[0, alt_max, alt_max, 0, 0],
        fill="toself", fillcolor=color, line=dict(color='black', width=0.5),
        name=nombre, opacity=0.4
    ))

agregar_sombra(fig, az_anexo, alt_anexo, "Anexo", "gray")
agregar_sombra(fig, az_db, alt_db, "Don Bosco", "darkgray")
agregar_sombra(fig, az_euc, alt_euc, "Eucalipto", "green")

# 2. Dibujar Analemas (Curvas de las horas)
horas_a_mostrar = [8, 10, 12, 14, 16, 18]
for h in horas_a_mostrar:
    df_h = df_sol[df_sol['hora'] == h]
    fig.add_trace(go.Scatter(
        x=df_h['azimuth'], y=df_h['elevation'],
        mode='lines', line=dict(color='blue', width=1, dash='dot'),
        name=f"{h}:00 hs", hoverinfo='name'
    ))

# 3. Dibujar Solsticios y Equinoccios (Los meses clave)
meses_clave = {12: "Solsticio Verano", 6: "Solsticio Invierno", 9: "Equinoccio"}
for mes, etiqueta in meses_clave.items():
    df_m = df_sol[(df_sol['mes'] == mes) & (df_sol.index.day == 21)]
    fig.add_trace(go.Scatter(
        x=df_m['azimuth'], y=df_m['elevation'],
        mode='lines', line=dict(width=3), name=etiqueta
    ))

# --- ESTÉTICA ---
fig.update_layout(
    xaxis=dict(title="Azimut (0°=N, 180°=S)", range=[0, 360]),
    yaxis=dict(title="Elevación", range=[0, 90]),
    template="plotly_white", height=700
)

st.plotly_chart(fig, use_container_width=True)
