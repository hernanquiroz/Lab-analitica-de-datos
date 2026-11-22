import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Laboratorio de Análisis", page_icon="📊", layout="wide")

# --- VARIABLES GLOBALES ---
DB_PATH = 'data/02_processed/laboratorio.duckdb'
DATA_DIR = 'data/01_raw/'

# Asegurar que las carpetas existan
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs('data/02_processed/', exist_ok=True)

# Función para conectar a DuckDB
def get_connection():
    return duckdb.connect(DB_PATH)

# --- BARRA LATERAL: CRÉDITOS ---
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Diseño Vibe coding por:<br><b>Ing. Hernan Quiroz</b></small>
    </div>
    """, unsafe_allow_html=True
)
st.sidebar.markdown("---")

# --- 1. SECCIÓN: SUBIR ARCHIVO ---
st.sidebar.header("📤 Subir nuevo CSV")
uploaded_file = st.sidebar.file_uploader("Selecciona un archivo CSV", type=["csv"])

if uploaded_file is not None:
    # Guardar el archivo en la carpeta raw
    file_path = os.path.join(DATA_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Archivo guardado: {uploaded_file.name}")

# --- 2. SECCIÓN: BUSCAR ARCHIVO EXISTENTE ---
st.sidebar.header("🔍 Buscar archivo existente")
# Listar los CSV disponibles en la carpeta
archivos_disponibles = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

if archivos_disponibles:
    archivo_seleccionado = st.sidebar.selectbox("Selecciona un archivo de la lista:", archivos_disponibles)
else:
    archivo_seleccionado = None
    st.sidebar.warning("No hay archivos CSV en el sistema.")

# --- 3. SECCIÓN: BORRAR ARCHIVO (Con protección) ---
st.sidebar.header("🗑️ Eliminar archivo")
if archivo_seleccionado:
    # Para evitar borrados accidentales, pedimos una confirmación
    confirmar_borrado = st.sidebar.checkbox(f"Confirmo que deseo borrar: {archivo_seleccionado}")
    
    if st.sidebar.button("Borrar archivo seleccionado"):
        if confirmar_borrado:
            ruta_borrar = os.path.join(DATA_DIR, archivo_seleccionado)
            os.remove(ruta_borrar)
            st.sidebar.success(f"Archivo {archivo_seleccionado} eliminado.")
            st.rerun() # Recargar la página para actualizar la lista
        else:
            st.sidebar.error("Debes marcar la casilla de confirmación para borrar.")

# --- ÁREA PRINCIPAL (DASHBOARD) ---
st.title("📊 Laboratorio de Análisis de Datos con DuckDB")

if archivo_seleccionado:
    st.markdown(f"**Analizando el archivo:** `{archivo_seleccionado}`")
    
    con = get_connection()
    
    # Cargar el archivo en DuckDB (como vista temporal para esta sesión)
    # Usamos una vista para no tener que importarlo físicamente cada vez
    query_vista = f"CREATE OR REPLACE VIEW datos_actuales AS SELECT * FROM read_csv_auto('{os.path.join(DATA_DIR, archivo_seleccionado)}')"
    con.execute(query_vista)
    
    # Pestañas para organizar el laboratorio
    tab1, tab2, tab3 = st.tabs(["🔎 Ficha Técnica", "📈 Gráficos Dinámicos", "📝 Hallazgos (Consejero)"])
    
    with tab1:
        st.subheader("Perfil de los Datos (SUMMARIZE)")
        if st.button("Generar Ficha Técnica"):
            df_summary = con.execute("SUMMARIZE datos_actuales").fetchdf()
            st.dataframe(df_summary)
            
    with tab2:
        st.subheader("Generación de Gráficos")
        # Obtener las columnas para que el usuario elija
        columnas = con.execute("SELECT * FROM datos_actuales LIMIT 1").df().columns.tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            eje_x = st.selectbox("Variable para Eje X (Categorías):", columnas)
        with col2:
            tipo_grafico = st.selectbox("Tipo de Gráfico:", ["Barras", "Torta"])
            
        if st.button("Graficar"):
            # Consulta agrupada básica
            query_grafico = f"SELECT {eje_x}, COUNT(*) as Conteo FROM datos_actuales GROUP BY {eje_x} ORDER BY Conteo DESC LIMIT 20"
            df_grafico = con.execute(query_grafico).fetchdf()
            
            if tipo_grafico == "Barras":
                fig = px.bar(df_grafico, x=eje_x, y='Conteo', title=f"Distribución de {eje_x}")
            else:
                fig = px.pie(df_grafico, names=eje_x, values='Conteo', title=f"Proporción de {eje_x}")
            
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("Redacción de Hallazgos Automatizada")
        st.info("El consejero estadístico analizará los datos y redactará los hallazgos basados en reglas (sin uso de APIs de IA).")
        
        if st.button("Ejecutar Consejero Estadístico"):
            # Ejemplo de lógica de "consejero" basada en reglas
            total_registros = con.execute("SELECT COUNT(*) FROM datos_actuales").fetchone()[0]
            
            # Buscar la columna con más nulos
            df_nulos = con.execute(f"""
                SELECT column_name, null_percentage 
                FROM (SUMMARIZE datos_actuales) 
                ORDER BY null_percentage DESC LIMIT 1
            """).fetchdf()
            
            col_nulos = df_nulos.iloc[0]['column_name']
            pct_nulos = df_nulos.iloc[0]['null_percentage']
            
            st.markdown(f"""
            ### 📋 Reporte de Hallazgos (Piloto)
            *   **Total de encuestados analizados:** {total_registros}
            *   **Alerta de calidad:** La variable `{col_nulos}` presenta un **{pct_nulos:.2f}%** de valores nulos. Se recomienda revisar la pregunta en el formulario para la encuesta general.
            *   **Recomendación metodológica:** Asegurar que el tamaño de la muestra general sea representativo. Si el piloto tiene {total_registros} casos, se sugiere calcular el tamaño muestral con un margen de error del 5%.
            """)
    
    con.close()

else:
    st.info("👈 Por favor, sube un archivo CSV o selecciona uno existente en la barra lateral para comenzar.")
