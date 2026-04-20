import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Analizador Solar UTN - Resistencia", layout="wide")

LATITUD = -27.45
LONGITUD = -58.98
ZONA_HORARIA = 'America/Argentina/Cordoba'

st.title("☀️ Carta Solar Cilíndrica - UTN FRRe")

# --- ESTADO DE LA SESIÓN (Base de datos de sombras) ---
if 'sombras' not in st.session_state:
    st.session_state.sombras = {} # Usamos diccionario para editar por nombre

# --- SIDEBAR: GESTIÓN DE SOMBRAS ---
st.sidebar.header("📐 Configuración de Obstáculos")

# 1. Formulario para añadir nuevas sombras
with st.sidebar.expander("➕ Añadir Nueva Sombra", expanded=True):
    nombre_nueva = st.text_input("Etiqueta", "Edificio")
    col_az1, col_az2 = st.columns(2)
    az_in = col_az1.number_input("Azimut Inicial", value=-90, key="new_az_in")
    az_fi = col_az2.number_input("Azimut Final", value=-60, key="new_az_fi")
    
    col_h1, col_h2 = st.columns(2)
    h1 = col_h1.number_input("Altura 1 (°)", value=30.0, key="new_h1")
    h2 = col_h2.number_input("Altura 2 (opcional)", value=0.0, key="new_h2", help="Dejar en 0 para sombra recta")
    
    if st.button("Dibujar Sombra"):
        if nombre_nueva in st.session_state.sombras:
            st.error("Ya existe una sombra con ese nombre.")
        else:
            # Si h2 es 0 o igual a h1, es rectangular. Si no, es trapecio.
            altura_final = h2 if h2 > 0 else h1
            st.session_state.sombras[nombre_nueva] = {
                "az": (az_in, az_fi),
                "h": (h1, altura_final)
            }
            st.rerun()

# 2. Lista de sombras añadidas (Edición y Borrado)
if st.session_state.sombras:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Sombras Activas")
    for nom in list(st.session_state.sombras.keys()):
        with st.sidebar.expander(f"📝 Editar: {nom}"):
            # Editores de valores
            s = st.session_state.sombras[nom]
            new_az = st.slider(f"Rango Azimut {nom}", -180, 180, s["az"])
            new_h1 = st.number_input(f"Altura inicial {nom}", value=float(s["h"][0]))
            new_h2 = st.number_input(f"Altura final {nom}", value=float(s["h"][1]))
            
            st.session_state.sombras[nom] = {"az": new_az, "h": (new_h1, new_h2)}
            
            if st.button(f"Eliminar {nom}", key=f"del_{nom}"):
                del st.session_state.sombras[nom]
                st.rerun()

# --- CÁLCULOS (ALTA RESOLUCIÓN) ---
@st.cache_data
def obtener_datos(lat, lon):
    tiempos = pd.date_range(start='2024-01-01', end='2024-12-31 23:55', freq='10min', tz=ZONA_HORARIA)
    sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
    sol = sol[sol['elevation'] > 0]
    sol['az_plot'] = np.where(sol['azimuth'] > 180, sol['azimuth'] - 360, sol['azimuth'])
    sol['hora'] = sol.index.hour
    sol['minuto'] = sol.index.minute
    return sol

df_total = obtener_datos(LATITUD, LONGITUD)

# --- GRÁFICO ---
fig = go.Figure()

# 3. Dibujar Sombras (Rectangulares o Inclinadas)
# Colores predefinidos para las sombras
colores_sombras = ['rgba(100, 100, 100, 0.5)', 'rgba(50, 150, 50, 0.5)', 'rgba(50, 50, 150, 0.5)', 'rgba(150, 50, 50, 0.5)']

for i, (nombre, datos) in enumerate(st.session_state.sombras.items()):
    az1, az2 = datos["az"]
    h1, h2 = datos["h"]
    color = colores_sombras[i % len(colores_sombras)]
    
    # El polígono ahora usa h1 para el inicio y h2 para el final
    fig.add_trace(go.Scatter(
        x=[az1, az1, az2, az2, az1],
        y=[0, h1, h2, 0, 0],
        fill="toself",
        name=f"Sombra: {nombre}", # Aparece en la leyenda a la derecha
        fillcolor=color,
        line=dict(color='black', width=1),
        hoverinfo="name"
    ))

# 4. Dibujar Analemas con etiquetas
for h in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]:
    df_h = df_total[(df_total['hora'] == h) & (df_total['minuto'] == 0)]
    if not df_h.empty:
        fig.add_trace(go.Scatter(
            x=df_h['az_plot'], y=df_h['elevation'],
            mode='lines', line=dict(color='rgba(0,0,200,0.2)', width=1, dash='dot'),
            showlegend=False, hoverinfo='skip'
        ))
        punto = df_h.loc[df_h['elevation'].idxmax()]
        fig.add_annotation(x=punto['az_plot'], y=punto['elevation'], text=f"{h}h", showarrow=False, font=dict(color="blue", size=10), yshift=10)

# 5. Dibujar Curvas Mensuales (Día 21)
meses = {1:'Ene', 3:'Mar', 6:'Jun', 9:'Sep', 12:'Dic'} # Reducimos a meses clave para claridad o todos
for i, mes_nom in meses.items():
    df_mes = df_total[(df_total.index.month == i) & (df_total.index.day == 21)].sort_values('az_plot')
    fig.add_trace(go.Scatter(x=df_mes['az_plot'], y=df_mes['elevation'], mode='lines', name=f"{mes_nom} (21)", line=dict(width=3)))

# --- ESTÉTICA ---
fig.update_layout(
    xaxis=dict(title="Azimut [°]", range=[-180, 180], dtick=30, gridcolor='lightgray'),
    yaxis=dict(title="Elevación [°]", range=[0, 90], dtick=10, gridcolor='lightgray'),
    template="plotly_white", height=700,
    legend=dict(title="Referencias", orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
)

st.plotly_chart(fig, use_container_width=True)
