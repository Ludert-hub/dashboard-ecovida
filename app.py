import streamlit as st
import pandas as pd
import plotly.express as px

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
if 'drill_egreso' not in st.session_state: st.session_state.drill_egreso = None

# --- BARRA LATERAL (LOGO PEQUEÑO Y CARGA DE DATOS) ---
try:
    st.sidebar.image("logo.jpeg", use_container_width=True)
except:
    pass

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='text-align: center;'>Carga de Datos</h3>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Adjunte el Excel de movimientos", type=["xlsx"])

# --- LÓGICA DE PANTALLAS ---
if uploaded_file is None:
    # ==========================================
    # PANTALLA DE INICIO (LANDING PAGE)
    # ==========================================
    st.markdown("<br><br>", unsafe_allow_html=True) # Espaciado superior
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            # Muestra el logo centrado y grande
            st.image("logo.jpeg", use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center; color: #1b5e20;'>ECOVIDA BARINAS</h1>", unsafe_allow_html=True)
        
        st.markdown("<h3 style='text-align: center; color: #555;'>Plataforma de Control Financiero y Operativo</h3>", unsafe_allow_html=True)
        st.info("👈 Por favor, carga el archivo de Excel en el panel lateral izquierdo para iniciar el dashboard.")

else:
    # ==========================================
    # PANTALLA DEL DASHBOARD (DATOS CARGADOS)
    # ==========================================
    st.markdown("<h2 style='text-align: center; color: #1b5e20; margin-top:0px;'>CONTROL DE ENTRADAS Y SALIDAS ECOVIDA</h2>", unsafe_allow_html=True)

    try:
        # Lectura de datos
        df = pd.read_excel(uploaded_file, sheet_name='General')
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)
        
        # --- PROCESAMIENTO DE FECHAS Y FILTRO ---
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha']) 
        df['Mes_Filtro'] = df['Fecha'].dt.strftime('%Y-%m') 
        
        meses_disponibles = sorted(df['Mes_Filtro'].unique().tolist(), reverse=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align: center;'>Filtro de Tiempo</h3>", unsafe_allow_html=True)
        meses_seleccionados = st.sidebar.multiselect("Seleccione el Mes", options=meses_disponibles, default=meses_disponibles)
        
        if meses_seleccionados:
            df = df[df['Mes_Filtro'].isin(meses_seleccionados)]
        
        # Limpieza financiera
        df['Monto $ +'] = df['Monto $ +'].apply(clean_numeric)
        df['Metodo Bs +'] = df['Metodo Bs +'].apply(clean_numeric) 
        df['Monto $ -'] = df['Monto $ -'].apply(clean_numeric)
        df['Monto Bs -'] = df['Monto Bs -'].apply(clean_numeric)
        
        df['Destinado'] = df['Destinado'].fillna('No Especificado').astype(str).str.strip().str.title()
        df['Concepto'] = df['Concepto'].fillna('No Especificado').astype(str).str.strip().str.title()
        
        # Agrupaciones
        ingresos_global = df.groupby('Destinado')[['Metodo Bs +', 'Monto $ +']].sum()
        ingresos_global = ingresos_global[(ingresos_global['Metodo Bs +'] > 0) | (ingresos_global['Monto $ +'] > 0)]
        
        egresos_global = df.groupby('Destinado')[['Monto Bs -', 'Monto $ -']].sum()
        egresos_global = egresos_global[(egresos_global['Monto Bs -'] > 0) | (egresos_global['Monto $ -'] > 0)]
        
        # --- MÉTRICAS SUPERIORES ---
        tot_ing_usd = ingresos_global['Monto $ +'].sum()
        tot_ing_bs = ingresos_global['Metodo Bs +'].sum()
        tot_egr_usd = egresos_global['Monto $ -'].sum()
        tot_egr_bs = egresos_global['Monto Bs -'].sum()

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Ingresos ($)", f"${tot_ing_usd:,.2f}")
        c2.metric("Total Ingresos (Bs)", f"Bs {tot_ing_bs:,.2f}")
        c3.metric("Total Egresos ($)", f"${tot_egr_usd:,.2f}")
        c4.metric("Total Egresos (Bs)", f"Bs {tot_egr_bs:,.2f}")
        st.markdown("---")

        # Estilos CSS para alineación perfecta
        st.markdown("""
        <style>
        .nowrap-text { white-space: nowrap; font-size: 15px; }
        </style>
        """, unsafe_allow_html=True)

        # --- ESTRUCTURA DE PANTALLA: 2 ZONAS + LÍNEA DIVISORIA ---
        col_ingresos, col_divider, col_egresos = st.columns([10, 1, 10])

        with col_ingresos:
            st.markdown("""
            <div style="background-color: #e8f5e9; padding: 10px; border-radius: 5px; text-align: center; border-bottom: 4px solid #4caf50; margin-bottom: 15px;">
                <h3 style="color: #2e7b32; margin: 0;">🟢 INGRESOS</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.drill_ingreso is None:
                st.markdown("**Desglose por Destinado:**")
                for dest, row in ingresos_global.iterrows():
                    rc1, rc2, rc3, rc4 = st.columns([3, 4, 3, 3])
                    rc1.markdown(f"<div class='nowrap-text'><b>{dest}</b></div>", unsafe_allow_html=True)
                    rc2.markdown(f"<div class='nowrap-text'>Bs {row['Metodo Bs +']:,.2f}</div>", unsafe_allow_html=True)
                    rc3.markdown(f"<div class='nowrap-text'>$ {row['Monto $ +']:,.2f}</div>", unsafe_allow_html=True)
                    if rc4.button("🔍 Ver", key=f"btn_ing_{dest}"):
                        st.session_state.drill_ingreso = dest
                        st.rerun()
                
                if not ingresos_global.empty:
                    fig1 = px.bar(ingresos_global.reset_index(), x='Destinado', y='Monto $ +', color='Destinado',
                                  title="Ingresos Globales ($)", text_auto='.2s')
                    st.plotly_chart(fig1, use_container_width=True)
            else:
                dest = st.session_state.drill_ingreso
                st.markdown(f"**Detalle de Conceptos: {dest}**")
                if st.button("⬅ Volver a Ingresos", key="back_ing"):
                    st.session_state.drill_ingreso = None
                    st.rerun()
                
                df_filt = df[(df['Destinado'] == dest) & ((df['Metodo Bs +'] > 0) | (df['Monto $ +'] > 0))]
                agrup_conc = df_filt.groupby('Concepto')[['Metodo Bs +', 'Monto $ +']].sum()
                st.dataframe(agrup_conc.style.format("{:,.2f}"), use_container_width=True)
                
                if not agrup_conc.empty:
                    fig_pie = px.pie(agrup_conc.reset_index(), names='Concepto', values='Monto $ +', 
                                     hole=0.4, title=f"Distribución - {dest} ($)")
                    st.plotly_chart(fig_pie, use_container_width=True)

        with col_divider:
            st.markdown("<div style='border-left: 2px solid #ccc; height: 100%; min-height: 500px; margin: auto;'></div>", unsafe_allow_html=True)

        with col_egresos:
            st.markdown("""
            <div style="background-color: #ffebee; padding: 10px; border-radius: 5px; text-align: center; border-bottom: 4px solid #f44336; margin-bottom: 15px;">
                <h3 style="color: #c62828; margin: 0;">🔴 EGRESOS</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.drill_egreso is None:
                st.markdown("**Desglose por Destinado:**")
                for dest, row in egresos_global.iterrows():
                    rc1, rc2, rc3, rc4 = st.columns([3, 4, 3, 3])
                    rc1.markdown(f"<div class='nowrap-text'><b>{dest}</b></div>", unsafe_allow_html=True)
                    rc2.markdown(f"<div class='nowrap-text'>Bs {row['Monto Bs -']:,.2f}</div>", unsafe_allow_html=True)
                    rc3.markdown(f"<div class='nowrap-text'>$ {row['Monto $ -']:,.2f}</div>", unsafe_allow_html=True)
                    if rc4.button("🔍 Ver", key=f"btn_egr_{dest}"):
                        st.session_state.drill_egreso = dest
                        st.rerun()
                        
                if not egresos_global.empty:
                    fig2 = px.bar(egresos_global.reset_index(), x='Destinado', y='Monto $ -', color='Destinado',
                                  title="Egresos Globales ($)", text_auto='.2s')
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                dest = st.session_state.drill_egreso
                st.markdown(f"**Detalle de Conceptos: {dest}**")
                if st.button("⬅ Volver a Egresos", key="back_egr"):
                    st.session_state.drill_egreso = None
                    st.rerun()
                
                df_filt = df[(df['Destinado'] == dest) & ((df['Monto Bs -'] > 0) | (df['Monto $ -'] > 0))]
                agrup_conc = df_filt.groupby('Concepto')[['Monto Bs -', 'Monto $ -']].sum()
                st.dataframe(agrup_conc.style.format("{:,.2f}"), use_container_width=True)
                
                if not agrup_conc.empty:
                    fig_pie2 = px.pie(agrup_conc.reset_index(), names='Concepto', values='Monto $ -', 
                                     hole=0.4, title=f"Distribución - {dest} ($)")
                    st.plotly_chart(fig_pie2, use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando los datos. Detalle técnico: {e}")