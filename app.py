import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Función para acortar textos largos y evitar solapamientos ---
def acortar(texto, limite=18):
    texto_str = str(texto)
    if len(texto_str) > limite:
        return texto_str[:limite] + "..."
    return texto_str

# --- Función para limpiar formatos numéricos ---
def clean_numeric(val):
    if pd.isna(val) or val == '':
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if '.' in val_str and ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    val_str = ''.join(c for c in val_str if c.isdigit() or c == '-' or c == '.')
    try:
        return float(val_str)
    except:
        return 0.0

# --- Configuración visual de la App ---
st.set_page_config(page_title="Dashboard Ecovida", layout="wide")

# Variables de Estado para el Drill-down
if 'drill_ingreso' not in st.session_state: st.session_state.drill_ingreso = None
if 'drill_ingreso_concepto' not in st.session_state: st.session_state.drill_ingreso_concepto = None

if 'drill_egreso' not in st.session_state: st.session_state.drill_egreso = None
if 'drill_egreso_concepto' not in st.session_state: st.session_state.drill_egreso_concepto = None

if 'last_uploaded' not in st.session_state: st.session_state.last_uploaded = None

# --- BARRA LATERAL Y PERSISTENCIA DE ARCHIVO ---
DATA_FILE = "datos_guardados.xlsx"

try:
    st.sidebar.image("logo.jpeg", use_container_width=True)
except:
    pass

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='text-align: center;'>Actualizar Datos</h3>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Subir nuevo Excel (reemplaza al anterior)", type=["xlsx"])

if uploaded_file is not None:
    file_signature = f"{uploaded_file.name}_{uploaded_file.size}"
    
    if st.session_state.last_uploaded != file_signature:
        with open(DATA_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ Datos actualizados exitosamente.")
        
        st.session_state.drill_ingreso = None
        st.session_state.drill_ingreso_concepto = None
        st.session_state.drill_egreso = None
        st.session_state.drill_egreso_concepto = None
        st.session_state.last_uploaded = file_signature

# --- LÓGICA DE PANTALLAS ---
if not os.path.exists(DATA_FILE):
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.jpeg", use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center; color: #1b5e20;'>ECOVIDA BARINAS</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #555;'>Plataforma de Control Financiero y Operativo</h3>", unsafe_allow_html=True)
        st.info("👈 No hay datos guardados. Por favor, sube el archivo de Excel en el panel izquierdo.")

else:
    st.markdown("<h2 style='text-align: center; color: #1b5e20; margin-top:0px;'>CONTROL DE ENTRADAS Y SALIDAS ECOVIDA</h2>", unsafe_allow_html=True)

    try:
        df = pd.read_excel(DATA_FILE, sheet_name='General')
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)
        
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha']) 
        df['Mes_Filtro'] = df['Fecha'].dt.strftime('%Y-%m') 
        
        meses_disponibles = sorted(df['Mes_Filtro'].unique().tolist(), reverse=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align: center;'>Filtro de Tiempo</h3>", unsafe_allow_html=True)
        meses_seleccionados = st.sidebar.multiselect("Seleccione los meses a visualizar", options=meses_disponibles, default=meses_disponibles)
        
        if meses_seleccionados:
            df = df[df['Mes_Filtro'].isin(meses_seleccionados)]
        
        df['Monto $+'] = df['Monto$ +'].apply(clean_numeric)
        df['Metodo Bs +'] = df['Metodo Bs +'].apply(clean_numeric) 
        df['Monto $-'] = df['Monto$ -'].apply(clean_numeric)
        df['Monto Bs -'] = df['Monto Bs -'].apply(clean_numeric)
        
        df['Destinado'] = df['Destinado'].fillna('No Especificado').astype(str).str.strip().str.title()
        df['Concepto'] = df['Concepto'].fillna('No Especificado').astype(str).str.strip().str.title()
        
        ingresos_global = df.groupby('Destinado')[['Metodo Bs +', 'Monto $ +']].sum()
        ingresos_global = ingresos_global[(ingresos_global['Metodo Bs +'] > 0) | (ingresos_global['Monto $ +'] > 0)]
        
        egresos_global = df.groupby('Destinado')[['Monto Bs -', 'Monto $ -']].sum()
        egresos_global = egresos_global[(egresos_global['Monto Bs -'] > 0) | (egresos_global['Monto $ -'] > 0)]
        
        tot_ing_usd = ingresos_global['Monto $ +'].sum()
        tot_ing_bs = ingresos_global['Metodo Bs +'].sum()
        tot_egr_usd = egresos_global['Monto $ -'].sum()
        tot_egr_bs = egresos_global['Monto Bs -'].sum()

        st.markdown("---