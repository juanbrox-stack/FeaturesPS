import streamlit as st
import pandas as pd
import re
import io

# Configuración
st.set_page_config(page_title="Generador de Cargas PIM", layout="centered")

# --- FUNCIONES DE APOYO ---
def limpiar_html(texto):
    if pd.isna(texto): return ""
    limpio = re.compile('<.*?>')
    return " ".join(re.sub(limpio, '', str(texto)).split())

def validar_sku(sku):
    sku = str(sku).strip()
    if sku.startswith('0') and len(sku) == 5: return True
    if sku.startswith('A') and len(sku) == 15: return True
    return False

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- LÓGICA DE ESTADO (SESSION STATE) ---
if 'procesado' not in st.session_state:
    st.session_state.procesado = False
    st.session_state.data_exito = None
    st.session_state.data_error = None

# --- INTERFAZ ---
st.title("🚀 Herramienta de Generación de Cargas")

col1, col2 = st.columns(2)
with col1:
    fichero_inc = st.file_uploader("1. Archivo Incompleto", type=["xlsx"])
with col2:
    fichero_pim = st.file_uploader("2. Exportación PIM", type=["xlsx"])

# Si el usuario sube archivos nuevos, reseteamos el estado para obligar a procesar de nuevo
if st.sidebar.button("Limpiar todo / Resetear"):
    st.session_state.procesado = False
    st.rerun()

if fichero_inc and fichero_pim:
    if st.button("Procesar Archivos"):
        with st.spinner('Procesando...'):
            # Lectura (usamos posición de columnas A=0, B=1)
            df_inc = pd.read_excel(fichero_inc, dtype=str).iloc[:, [0]]
            df_inc.columns = ['sku']
            
            df_pim = pd.read_excel(fichero_pim, dtype=str).iloc[:, [0, 1]]
            df_pim.columns = ['sku', 'dato_bruto']

            # Limpieza y Cruce
            df_inc['sku'] = df_inc['sku'].str.strip()
            df_pim['sku'] = df_pim['sku'].str.strip()

            mask = df_inc['sku'].apply(validar_sku)
            df_ok = df_inc[mask]
            df_err_fmt = df_inc[~mask].copy()
            df_err_fmt['motivo'] = 'Formato SKU incorrecto'

            df_unido = pd.merge(df_ok, df_pim, on='sku', how='left')
            df_unido['caracteristica'] = df_unido['dato_bruto'].apply(limpiar_html)

            df_final = df_unido.dropna(subset=['dato_bruto'])[['sku', 'caracteristica']]
            df_no_pim = df_unido[df_unido['dato_bruto'].isna()].copy()
            df_no_pim['motivo'] = 'No encontrado en el PIM'

            # Guardar en el ESTADO DE LA SESIÓN
            st.session_state.data_exito = to_excel(df_final)
            st.session_state.data_error = to_excel(pd.concat([df_err_fmt, df_no_pim[['sku', 'motivo']]]))
            st.session_state.procesado = True

# --- MOSTRAR BOTONES SI YA SE HA PROCESADO ---
if st.session_state.procesado:
    st.divider()
    st.success("¡Datos listos! Puedes descargar ambos ficheros sin perder la sesión.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="📥 Descargar Fichero Subida",
            data=st.session_state.data_exito,
            file_name="fichero_subida.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c2:
        st.download_button(
            label="⚠️ Descargar Errores",
            data=st.session_state.data_error,
            file_name="log_errores.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )