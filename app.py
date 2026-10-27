import streamlit as st
import pandas as pd
import plotly.express as px
import os
from github import Github

def acortar(texto, limite=18):
    texto_str = str(texto)
    return texto_str[:limite] + "..." if len(texto_str) > limite else texto_str

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
    except Exception:
        return 0.0

# --- Función para guardar el Excel directamente en GitHub ---
def guardar_en_github(file_bytes, filename):
    try:
        token = st.secrets["GITHUB_TOKEN"]
        g = Github(token)
        repo = g.get_repo("Ludert-hub/dashboard-ecovida")
        try:
            # Si el archivo ya existe en GitHub, lo actualiza
            contents = repo.get_contents(filename)
            repo.update_file(contents.path, "Actualizando base de datos Excel desde la App", file_bytes, contents.sha)
        except Exception:
            # Si no existe aún en GitHub, lo crea por primera vez
            repo.create_file(filename, "Creando base de datos Excel inicial desde la App", file_bytes)
        return True
    except Exception as e:
        st.sidebar.warning(f"⚠️ Guardado temporalmente. Para fijarlo en GitHub configura el Token. ({e})")
        return False

st.set_page_config(page_title="Dashboard Ecovida", layout="wide")

if 'drill_ingreso' not in st.session_state: st.session_state.drill_ingreso = None
if 'drill_ingreso_concepto' not in st.session_state: st.session_state.drill_ingreso_concepto = None
if 'drill_egreso' not in st.session_state: st.session_state.drill_egreso = None
if 'drill_egreso_concepto' not in st.session_state: st.session_state.drill_egreso_concepto = None
if 'last_uploaded' not in st.session_state: st.session_state.last_uploaded = None

DATA_FILE = "datos_guardados.xlsx"

if os.path.exists("logo.jpeg"):
    st.sidebar.image("logo.jpeg", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='text-align: center;'>Actualizar Datos</h3>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Subir nuevo Excel (reemplaza al de la nube)", type=["xlsx"])

if uploaded_file is not None:
    file_signature = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.last_uploaded != file_signature:
        file_bytes = uploaded_file.getvalue()
        
        # 1. Guardar copia rápida en el servidor local para visualización inmediata
        with open(DATA_FILE, "wb") as f:
            f.write(file_bytes)
            
        # 2. Subir y sobrescribir permanentemente en GitHub
        with st.sidebar:
            with st.spinner("Sincronizando archivo con GitHub en la nube..."):
                exito = guardar_en_github(file_bytes, DATA_FILE)
        
        if exito:
            st.sidebar.success("✅ Excel guardado permanentemente en GitHub.")
        
        st.session_state.drill_ingreso = None
        st.session_state.drill_ingreso_concepto = None
        st.session_state.drill_egreso = None
        st.session_state.drill_egreso_concepto = None
        st.session_state.last_uploaded = file_signature

if not os.path.exists(DATA_FILE):
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.jpeg"):
            st.image("logo.jpeg", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #1b5e20;'>ECOVIDA BARINAS</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #555;'>Plataforma de Control Financiero y Operativo</h3>", unsafe_allow_html=True)
        st.info("👈 Sube el archivo de Excel por primera vez en el panel izquierdo para dejarlo guardado en la nube.")

else:
    st.markdown("<h2 style='text-align: center; color: #1b5e20; margin-top:0px;'>CONTROL DE ENTRADAS Y SALIDAS ECOVIDA</h2>", unsafe_allow_html=True)

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
    
    df['Monto $ +'] = df['Monto $ +'].apply(clean_numeric)
    df['Metodo Bs +'] = df['Metodo Bs +'].apply(clean_numeric)
    df['Monto $ -'] = df['Monto $ -'].apply(clean_numeric)
    df['Monto Bs -'] = df['Monto Bs -'].apply(clean_numeric)
    
    df['Destinado'] = df['Destinado'].fillna('No Especificado').astype(str).str.strip().str.title()
    df['Concepto'] = df['Concepto'].fillna('No Especificado').astype(str).str.strip().str.title()
    
    ingresos_global = df.groupby('Destinado')[['Metodo Bs +', 'Monto $ +']].sum()
    ingresos_global = ingresos_global[(ingresos_global['Metodo Bs +'] > 0) | (ingresos_global['Monto $ +'] > 0)]
    ingresos_global = ingresos_global.sort_values(by='Monto $ +', ascending=False)
    
    egresos_global = df.groupby('Destinado')[['Monto Bs -', 'Monto $ -']].sum()
    egresos_global = egresos_global[(egresos_global['Monto Bs -'] > 0) | (egresos_global['Monto $ -'] > 0)]
    egresos_global = egresos_global.sort_values(by='Monto $ -', ascending=False)
    
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

    st.markdown("<style>.nowrap-text { white-space: nowrap; font-size: 15px; overflow: hidden; text-overflow: ellipsis; }</style>", unsafe_allow_html=True)

    col_ingresos, col_divider, col_egresos = st.columns([10, 1, 10])

    with col_ingresos:
        st.markdown("<div style='background-color: #e8f5e9; padding: 10px; border-radius: 5px; text-align: center; border-bottom: 4px solid #4caf50; margin-bottom: 15px;'><h3 style='color: #2e7b32; margin: 0;'>🟢 INGRESOS</h3></div>", unsafe_allow_html=True)
        
        if st.session_state.drill_ingreso is None:
            st.markdown("**Desglose por Destinado:**")
            for dest, row in ingresos_global.iterrows():
                rc1, rc2, rc3, rc4 = st.columns([5, 2, 3, 3])
                pct = (row['Monto $ +'] / tot_ing_usd * 100) if tot_ing_usd > 0 else 0
                dest_str = acortar(dest, 18)
                
                rc1.markdown(f"<div title='{dest}' style='font-size: 15px;'><b>{dest_str}</b></div>", unsafe_allow_html=True)
                rc2.markdown(f"<div style='font-size: 15px;'>{pct:.1f}%</div>", unsafe_allow_html=True)
                rc3.markdown(f"<div style='font-size: 15px;'>$ {row['Monto $ +']:,.2f}</div>", unsafe_allow_html=True)
                if rc4.button("🔍 Ver", key=f"btn_ing_{dest}"):
                    st.session_state.drill_ingreso = dest
                    st.rerun()
            
            if not ingresos_global.empty:
                fig1 = px.bar(ingresos_global.reset_index(), x='Destinado', y='Monto $ +', color='Destinado', title="Ingresos Globales ($)", text_auto='.2s')
                st.plotly_chart(fig1, use_container_width=True)
        
        else:
            dest = st.session_state.drill_ingreso
            
            if st.session_state.drill_ingreso_concepto is None:
                col_b1, col_b2 = st.columns([1, 3])
                with col_b1:
                    if st.button("⬅ Volver", key="back_ing"):
                        st.session_state.drill_ingreso = None
                        st.rerun()
                
                st.markdown(f"**Conceptos de: {dest}**")
                df_filt = df[(df['Destinado'] == dest) & ((df['Metodo Bs +'] > 0) | (df['Monto $ +'] > 0))]
                
                agrup_conc = df_filt.groupby('Concepto')[['Metodo Bs +', 'Monto $ +']].sum()
                agrup_conc = agrup_conc.sort_values(by='Monto $ +', ascending=False)
                
                total_dest_usd = agrup_conc['Monto $ +'].sum()
                
                for conc, row in agrup_conc.iterrows():
                    rc1, rc2, rc3, rc4 = st.columns([5, 2, 3, 3])
                    pct = (row['Monto $ +'] / total_dest_usd * 100) if total_dest_usd > 0 else 0
                    conc_str = acortar(conc, 20)
                    
                    rc1.markdown(f"<div title='{conc}' style='font-size: 15px;'>{conc_str}</div>", unsafe_allow_html=True)
                    rc2.markdown(f"<div style='font-size: 15px;'>{pct:.1f}%</div>", unsafe_allow_html=True)
                    rc3.markdown(f"<div style='font-size: 15px;'>$ {row['Monto $ +']:,.2f}</div>", unsafe_allow_html=True)
                    if rc4.button("👁️ Detalle", key=f"btn_ing_conc_{dest}_{conc}"):
                        st.session_state.drill_ingreso_concepto = conc
                        st.rerun()
                        
                if not agrup_conc.empty:
                    fig_pie = px.pie(agrup_conc.reset_index(), names='Concepto', values='Monto $ +', hole=0.4, title=f"Distribución - {dest} ($)")
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            else:
                conc = st.session_state.drill_ingreso_concepto
                col_b1, col_b2 = st.columns([1, 3])
                with col_b1:
                    if st.button("⬅ Volver", key="back_ing_conc"):
                        st.session_state.drill_ingreso_concepto = None
                        st.rerun()
                        
                st.markdown(f"**Transacciones de: {conc}**")
                df_detalle = df[(df['Destinado'] == dest) & (df['Concepto'] == conc) & ((df['Metodo Bs +'] > 0) | (df['Monto $ +'] > 0))].copy()
                
                df_detalle = df_detalle.sort_values(by='Fecha', ascending=True)
                df_detalle['Fecha'] = df_detalle['Fecha'].dt.strftime('%d/%m/%Y')
                
                styled_df = df_detalle[['Fecha', 'Descripción', 'Monto $ +', 'Metodo Bs +']].style.format({
                    'Monto $ +': '{:,.2f}',
                    'Metodo Bs +': '{:,.2f}'
                })
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

    with col_divider:
        st.markdown("<div style='border-left: 2px solid #ccc; height: 100%; min-height: 500px; margin: auto;'></div>", unsafe_allow_html=True)

    with col_egresos:
        st.markdown("<div style='background-color: #ffebee; padding: 10px; border-radius: 5px; text-align: center; border-bottom: 4px solid #f44336; margin-bottom: 15px;'><h3 style='color: #c62828; margin: 0;'>🔴 EGRESOS</h3></div>", unsafe_allow_html=True)
        
        if st.session_state.drill_egreso is None:
            st.markdown("**Desglose por Destinado:**")
            for dest, row in egresos_global.iterrows():
                rc1, rc2, rc3, rc4 = st.columns([5, 2, 3, 3])
                pct = (row['Monto $ -'] / tot_egr_usd * 100) if tot_egr_usd > 0 else 0
                dest_str = acortar(dest, 18)
                
                rc1.markdown(f"<div title='{dest}' style='font-size: 15px;'><b>{dest_str}</b></div>", unsafe_allow_html=True)
                rc2.markdown(f"<div style='font-size: 15px;'>{pct:.1f}%</div>", unsafe_allow_html=True)
                rc3.markdown(f"<div style='font-size: 15px;'>$ {row['Monto $ -']:,.2f}</div>", unsafe_allow_html=True)
                if rc4.button("🔍 Ver", key=f"btn_egr_{dest}"):
                    st.session_state.drill_egreso = dest
                    st.rerun()
                    
            if not egresos_global.empty:
                fig2 = px.bar(egresos_global.reset_index(), x='Destinado', y='Monto $ -', color='Destinado', title="Egresos Globales ($)", text_auto='.2s')
                st.plotly_chart(fig2, use_container_width=True)
        
        else:
            dest = st.session_state.drill_egreso
            
            if st.session_state.drill_egreso_concepto is None:
                col_b1, col_b2 = st.columns([1, 3])
                with col_b1:
                    if st.button("⬅ Volver", key="back_egr"):
                        st.session_state.drill_egreso = None
                        st.rerun()
                        
                st.markdown(f"**Conceptos de: {dest}**")
                df_filt = df[(df['Destinado'] == dest) & ((df['Monto Bs -'] > 0) | (df['Monto $ -'] > 0))]
                
                agrup_conc = df_filt.groupby('Concepto')[['Monto Bs -', 'Monto $ -']].sum()
                agrup_conc = agrup_conc.sort_values(by='Monto $ -', ascending=False)
                
                total_dest_usd_egr = agrup_conc['Monto $ -'].sum()
                
                for conc, row in agrup_conc.iterrows():
                    rc1, rc2, rc3, rc4 = st.columns([5, 2, 3, 3])
                    pct = (row['Monto $ -'] / total_dest_usd_egr * 100) if total_dest_usd_egr > 0 else 0
                    conc_str = acortar(conc, 20)
                    
                    rc1.markdown(f"<div title='{conc}' style='font-size: 15px;'>{conc_str}</div>", unsafe_allow_html=True)
                    rc2.markdown(f"<div style='font-size: 15px;'>{pct:.1f}%</div>", unsafe_allow_html=True)
                    rc3.markdown(f"<div style='font-size: 15px;'>$ {row['Monto $ -']:,.2f}</div>", unsafe_allow_html=True)
                    if rc4.button("👁️ Detalle", key=f"btn_egr_conc_{dest}_{conc}"):
                        st.session_state.drill_egreso_concepto = conc
                        st.rerun()
                        
                if not agrup_conc.empty:
                    fig_pie2 = px.pie(agrup_conc.reset_index(), names='Concepto', values='Monto $ -', hole=0.4, title=f"Distribución - {dest} ($)")
                    st.plotly_chart(fig_pie2, use_container_width=True)
            
            else:
                conc = st.session_state.drill_egreso_concepto
                col_b1, col_b2 = st.columns([1, 3])
                with col_b1:
                    if st.button("⬅ Volver", key="back_egr_conc"):
                        st.session_state.drill_egreso_concepto = None
                        st.rerun()
                        
                st.markdown(f"**Transacciones de: {conc}**")
                df_detalle = df[(df['Destinado'] == dest) & (df['Concepto'] == conc) & ((df['Monto Bs -'] > 0) | (df['Monto $ -'] > 0))].copy()
                
                df_detalle = df_detalle.sort_values(by='Fecha', ascending=True)
                df_detalle['Fecha'] = df_detalle['Fecha'].dt.strftime('%d/%m/%Y')
                
                styled_df2 = df_detalle[['Fecha', 'Descripción', 'Monto $ -', 'Monto Bs -']].style.format({
                    'Monto $ -': '{:,.2f}',
                    'Monto Bs -': '{:,.2f}'
                })
                st.dataframe(styled_df2, use_container_width=True, hide_index=True)
