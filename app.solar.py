import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pvlib
import numpy as np

# --- INTERRUPTOR DE MANTENIMIENTO ---
# Cambiá esto a False cuando quieras que la app sea visible
en_construccion = False 

if en_construccion:
    st.title("🚧 Sitio en Mantenimiento")
    st.subheader("Estamos realizando mejoras técnicas en la Carta Solar.")
    st.write("Volvé a visitarnos pronto. Atte: Equipo GITEA - UTN FRRe.")
    
    st.stop() 
  
# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carta Solar Interactiva", layout="wide")

# --- SIDEBAR: CONFIGURACIÓN UBICACIÓN ---
st.sidebar.header("🌍 Ubicación Geográfica")
lat_user = st.sidebar.number_input("Latitud (Sur es negativo)", value=-27.45, format="%.2f")
lon_user = st.sidebar.number_input("Longitud (Oeste es negativo)", value=-58.98, format="%.2f")
tz_user = st.sidebar.selectbox("Zona Horaria (UTC)", 
                               options=["America/Argentina/Cordoba", "America/Argentina/Buenos_Aires", "Etc/GMT+3", "Etc/GMT+4", "Europe/Madrid"],
                               index=0)

st.title("☀️ Carta Solar Cilíndrica Interactiva")
st.markdown(f"**Ubicación actual:** Lat {lat_user}, Lon {lon_user} | **Zona Horaria:** {tz_user}")

# --- ESTADO DE LA SESIÓN (Sombras) ---
if 'sombras' not in st.session_state:
    st.session_state.sombras = {}

# --- SIDEBAR: GESTIÓN DE OBSTÁCULOS ---
st.sidebar.markdown("---")
st.sidebar.header("📐 Configuración de Obstáculos")

with st.sidebar.expander("➕ Añadir Nueva Sombra", expanded=False):
    nombre_nueva = st.text_input("Etiqueta", "Obstáculo")
    col_az1, col_az2 = st.columns(2)
    az_in = col_az1.number_input("Azimut Inicial", value=-90)
    az_fi = col_az2.number_input("Azimut Final", value=-60)
    
    col_h1, col_h2 = st.columns(2)
    h1 = col_h1.number_input("Altura 1 (°)", value=30.0)
    h2 = col_h2.number_input("Altura 2 (opcional)", value=0.0)
    
    if st.button("Dibujar Sombra"):
        if nombre_nueva in st.session_state.sombras:
            st.error("Ese nombre ya existe.")
        else:
            altura_final = h2 if h2 > 0 else h1
            st.session_state.sombras[nombre_nueva] = {"az": (az_in, az_fi), "h": (h1, altura_final)}
            st.rerun()

if st.session_state.sombras:
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

# --- CÁLCULOS ---
@st.cache_data
def obtener_datos(lat, lon, tz):
    tiempos = pd.date_range(start='2024-01-01', end='2024-12-31 23:55', freq='5min', tz=tz)
    sol = pvlib.solarposition.get_solarposition(tiempos, lat, lon)
    sol = sol[sol['elevation'] > 0]
    sol['az_plot'] = np.where(sol['azimuth'] > 180, sol['azimuth'] - 360, sol['azimuth'])
    sol['hora'] = sol.index.hour
    sol['minuto'] = sol.index.minute
    return sol

df_total = obtener_datos(lat_user, lon_user, tz_user)

# --- GRÁFICO ---
fig = go.Figure()

paleta_colores = ['rgba(100, 100, 100, 0.6)', 'rgba(46, 125, 50, 0.6)', 'rgba(21, 101, 192, 0.6)', 
                  'rgba(198, 40, 40, 0.6)', 'rgba(156, 39, 176, 0.6)', 'rgba(255, 143, 0, 0.6)']

# 1. Sombras
for i, (nombre, datos) in enumerate(st.session_state.sombras.items()):
    az1, az2 = datos["az"]
    h1, h2 = datos["h"]
    fig.add_trace(go.Scatter(
        x=[az1, az1, az2, az2, az1], y=[0, h1, h2, 0, 0],
        fill="toself", name=f"Sombra: {nombre}",
        fillcolor=paleta_colores[i % len(paleta_colores)],
        line=dict(color='rgba(0,0,0,0.8)', width=1.5)
    ))

# 2. Analemas (Etiquetas en el lienzo)
for h in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]:
    df_h = df_total[(df_total['hora'] == h) & (df_total['minuto'] == 0)].sort_index()
    if not df_h.empty:
        fig.add_trace(go.Scatter(
            x=df_h['az_plot'], y=df_h['elevation'], mode='lines',
            line=dict(color='rgba(0,0,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='skip'
        ))
        punto = df_h.loc[df_h['elevation'].idxmax()]
        fig.add_annotation(x=punto['az_plot'], y=punto['elevation'], text=f"{h}h", 
                           showarrow=False, font=dict(color="blue", size=10), yshift=10)

# 3. Meses Agrupados (Con Dic 21 separado)
grupos_meses = [
    {'m': [6],      'nom': 'Junio (21)',   'col': '#1f77b4'},
    {'m': [5, 7],   'nom': 'May-Jul (21)', 'col': '#9467bd'},
    {'m': [4, 8],   'nom': 'Abr-Ago (21)', 'col': '#d62728'},
    {'m': [3, 9],   'nom': 'Mar-Sep (21)', 'col': '#2ca02c'},
    {'m': [2, 10],  'nom': 'Feb-Oct (21)', 'col': '#ffbb78'},
    {'m': [1, 11],  'nom': 'Nov-Ene (21)', 'col': '#e377c2'}, # Agrupados
    {'m': [12],     'nom': 'Diciembre (21)', 'col': '#ff7f0e'} # SOLSTICIO SOLO
]

for g in grupos_meses:
    m_ref = g['m'][0]
    df_m = df_total[(df_total.index.month == m_ref) & (df_total.index.day == 21)].sort_values('az_plot')
    if not df_m.empty:
        fig.add_trace(go.Scatter(x=df_m['az_plot'], y=df_m['elevation'], mode='lines', name=g['nom'], line=dict(color=g['col'], width=3)))

# --- AJUSTES DE EJES Y GRILLA ---
fig.update_layout(
    xaxis=dict(
        title="Acimut Solar [°] (-180=S, -90=E, 0=N, 90=O, 180=S)",
        range=[-180, 180],
        dtick=15, # LINEAS CADA 15 GRADOS
        gridcolor='lightgray',
        zerolinecolor='black'
    ),
    yaxis=dict(title="Elevación Solar [°]", range=[0, 90], dtick=10, gridcolor='lightgray'),
    template="plotly_white", height=750,
    margin=dict(l=60, r=200, t=50, b=50),
    legend=dict(title="<b>REFERENCIAS</b>", yanchor="top", y=1, xanchor="left", x=1.05, borderwidth=1)
)

st.plotly_chart(fig, use_container_width=True)
