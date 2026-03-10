import streamlit as st
import pandas as pd
import re
import io

# Configuración de la página
st.set_page_config(page_title="Generador de Ficheros de Subida", layout="centered")

def limpiar_html(texto):
    """Elimina etiquetas HTML y limpia espacios."""
    if pd.isna(texto):
        return ""
    # Eliminar etiquetas HTML usando Regex
    limpio = re.compile('<.*?>')
    texto_limpio = re.sub(limpio, '', str(texto))
    # Limpiar espacios extra y saltos de línea
    return " ".join(texto_limpio.split())

def validar_sku(sku):
    """Lógica de validación de formato de SKU."""
    sku = str(sku).strip()
    if sku.startswith('0') and len(sku) == 5:
        return True
    if sku.startswith('A') and len(sku) == 15:
        return True
    return False

def to_excel(df):
    """Convierte un DataFrame a un objeto binario de Excel para descargar."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Herramienta de Generación de Cargas")
st.write("Sube los archivos para cruzar la información del PIM.")

col1, col2 = st.columns(2)

with col1:
    fichero_inc = st.file_uploader("1. Archivo Incompleto (Solo SKUs)", type=["xlsx"])
with col2:
    fichero_pim = st.file_uploader("2. Exportación PIM (Datos)", type=["xlsx"])

if fichero_inc and fichero_pim:
    if st.button("Procesar Archivos"):
        with st.spinner('Procesando datos y limpiando HTML...'):
            # Leer archivos
            df_inc_raw = pd.read_excel(fichero_inc, dtype=str)
            df_pim_raw = pd.read_excel(fichero_pim, dtype=str)

            # Selección por posición (Col A y Col B)
            df_inc = df_inc_raw.iloc[:, [0]].copy()
            df_inc.columns = ['sku']
            
            df_pim = df_pim_raw.iloc[:, [0, 1]].copy()
            df_pim.columns = ['sku', 'dato_bruto']

            # Limpiar SKUs
            df_inc['sku'] = df_inc['sku'].str.strip()
            df_pim['sku'] = df_pim['sku'].str.strip()

            # Separar por formato
            mask_formato = df_inc['sku'].apply(validar_sku)
            df_ok = df_inc[mask_formato]
            df_err_formato = df_inc[~mask_formato].copy()
            df_err_formato['motivo'] = 'Formato SKU incorrecto'

            # Cruzar datos
            df_unido = pd.merge(df_ok, df_pim, on='sku', how='left')

            # Limpiar HTML en la columna de datos
            df_unido['caracteristica'] = df_unido['dato_bruto'].apply(limpiar_html)

            # Separar resultados finales y errores de búsqueda
            df_final = df_unido.dropna(subset=['dato_bruto'])[['sku', 'caracteristica']]
            
            df_no_pim = df_unido[df_unido['dato_bruto'].isna()].copy()
            df_no_pim['motivo'] = 'No encontrado en el PIM'
            
            # Consolidar errores
            df_errores = pd.concat([df_err_formato, df_no_pim[['sku', 'motivo']]])

            st.success("¡Proceso completado!")

            # --- BOTONES DE DESCARGA ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.download_button(
                    label="📥 Descargar Fichero Subida",
                    data=to_excel(df_final),
                    file_name="fichero_subida_herramienta.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with c2:
                st.download_button(
                    label="⚠️ Descargar Errores",
                    data=to_excel(df_errores),
                    file_name="log_errores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )