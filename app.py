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
    file_path = os.path.join(DATA_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Archivo guardado: {uploaded_file.name}")

# --- 2. SECCIÓN: BUSCAR ARCHIVO EXISTENTE ---
st.sidebar.header("🔍 Buscar archivo existente")
archivos_disponibles = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

if archivos_disponibles:
    archivo_seleccionado = st.sidebar.selectbox("Selecciona un archivo de la lista:", archivos_disponibles)
else:
    archivo_seleccionado = None
    st.sidebar.warning("No hay archivos CSV en el sistema.")

# --- 3. SECCIÓN: BORRAR ARCHIVO (Con protección) ---
st.sidebar.header("🗑️ Eliminar archivo")
if archivo_seleccionado:
    confirmar_borrado = st.sidebar.checkbox(f"Confirmo que deseo borrar: {archivo_seleccionado}")
    
    if st.sidebar.button("Borrar archivo seleccionado"):
        if confirmar_borrado:
            ruta_borrar = os.path.join(DATA_DIR, archivo_seleccionado)
            os.remove(ruta_borrar)
            st.sidebar.success(f"Archivo {archivo_seleccionado} eliminado.")
            st.rerun()
        else:
            st.sidebar.error("Debes marcar la casilla de confirmación para borrar.")

# --- ÁREA PRINCIPAL (DASHBOARD) ---
st.title("📊 Laboratorio de Análisis de Datos con DuckDB")

if archivo_seleccionado:
    st.markdown(f"**Analizando el archivo:** `{archivo_seleccionado}`")
    
    con = get_connection()
    
    # Crear la vista temporal apuntando al CSV
    query_vista = f"CREATE OR REPLACE VIEW datos_actuales AS SELECT * FROM read_csv_auto('{os.path.join(DATA_DIR, archivo_seleccionado)}')"
    con.execute(query_vista)
    
    # AQUÍ SE CREAN LAS PESTAÑAS (Esto era lo que faltaba)
    tab1, tab2, tab3 = st.tabs(["🔎 Ficha Técnica", "📈 Gráficos Dinámicos", "📝 Hallazgos (Consejero)"])
    
    # --- PESTAÑA 1: FICHA TÉCNICA ---
    with tab1:
        st.subheader("Perfil de los Datos (SUMMARIZE)")
        if st.button("Generar Ficha Técnica"):
            df_summary = con.execute("SUMMARIZE datos_actuales").fetchdf()
            st.dataframe(df_summary)
            
    # --- PESTAÑA 2: GRÁFICOS ---
    with tab2:
        st.subheader("📈 Generador de Gráficos Estadísticos")
        
        info_columnas = con.execute("DESCRIBE datos_actuales").fetchdf()
        
        # Clasificar columnas por tipo
        columnas_numericas = info_columnas[info_columnas['column_type'].str.contains('INT|DOUBLE|FLOAT|DECIMAL|BIGINT|HUGEINT|SMALLINT|TINYINT|REAL')]['column_name'].tolist()
        columnas_texto = info_columnas[info_columnas['column_type'].str.contains('VARCHAR|CHAR|TEXT')]['column_name'].tolist()
        columnas_todas = info_columnas['column_name'].tolist()

        categoria_grafico = st.selectbox(
            "1. Selecciona la familia de gráfico:", 
            ["Cualitativos (Categorías)", "Cuantitativos (Distribuciones)", "Relaciones (Bivariante/Multivariante)", "Series Temporales"]
        )

        if categoria_grafico == "Cualitativos (Categorías)":
            tipo_grafico = st.selectbox("Tipo de gráfico:", ["Barras", "Torta (Pie)", "Anillo (Donut)", "Barras Apiladas", "Treemap", "Embudo (Funnel)", "Pareto"])
            var_x = st.selectbox("Variable categórica (Eje X):", columnas_texto if columnas_texto else columnas_todas)
            var_color = st.selectbox("Variable para agrupar (Opcional):", [None] + columnas_texto)
            
            if st.button("Generar Gráfico Cualitativo"):
                query = f"SELECT {var_x} {',' + var_color if var_color else ''}, COUNT(*) as Frecuencia FROM datos_actuales GROUP BY {var_x} {',' + var_color if var_color else ''}"
                df = con.execute(query).fetchdf()
                
                if tipo_grafico == "Barras":
                    fig = px.bar(df, x=var_x, y='Frecuencia', color=var_color)
                elif tipo_grafico == "Torta (Pie)":
                    fig = px.pie(df, names=var_x, values='Frecuencia')
                elif tipo_grafico == "Anillo (Donut)":
                    fig = px.pie(df, names=var_x, values='Frecuencia', hole=0.5)
                elif tipo_grafico == "Barras Apiladas":
                    fig = px.bar(df, x=var_x, y='Frecuencia', color=var_color, barmode='stack')
                elif tipo_grafico == "Treemap":
                    fig = px.treemap(df, path=[var_x], values='Frecuencia')
                elif tipo_grafico == "Embudo (Funnel)":
                    fig = px.funnel(df, x='Frecuencia', y=var_x)
                elif tipo_grafico == "Pareto":
                    df = df.sort_values('Frecuencia', ascending=False)
                    df['Acumulado'] = df['Frecuencia'].cumsum() / df['Frecuencia'].sum() * 100
                    fig = px.bar(df, x=var_x, y='Frecuencia')
                    fig.add_scatter(x=df[var_x], y=df['Acumulado'], name='% Acumulado', yaxis='y2')
                    fig.update_layout(yaxis2=dict(overlaying='y', side='right'))
                st.plotly_chart(fig, use_container_width=True)

        elif categoria_grafico == "Cuantitativos (Distribuciones)":
            tipo_grafico = st.selectbox("Tipo de gráfico:", ["Histograma", "Boxplot (Caja y bigotes)", "Violín", "Densidad (KDE)"])
            var_y = st.selectbox("Variable numérica:", columnas_numericas if columnas_numericas else columnas_todas)
            
            if st.button("Generar Gráfico Cuantitativo"):
                df = con.execute(f"SELECT {var_y} FROM datos_actuales WHERE {var_y} IS NOT NULL").fetchdf()
                
                if tipo_grafico == "Histograma":
                    fig = px.histogram(df, x=var_y, nbins=30)
                elif tipo_grafico == "Boxplot (Caja y bigotes)":
                    fig = px.box(df, y=var_y)
                elif tipo_grafico == "Violín":
                    fig = px.violin(df, y=var_y, box=True)
                elif tipo_grafico == "Densidad (KDE)":
                    fig = px.histogram(df, x=var_y, histnorm='density')
                st.plotly_chart(fig, use_container_width=True)

        elif categoria_grafico == "Relaciones (Bivariante/Multivariante)":
            tipo_grafico = st.selectbox("Tipo de gráfico:", ["Dispersión (Scatter)", "Burbujas", "Mapa de Calor (Correlación)", "Coordenadas Paralelas"])
            var_x = st.selectbox("Variable X (Numérica):", columnas_numericas if columnas_numericas else columnas_todas)
            var_y = st.selectbox("Variable Y (Numérica):", columnas_numericas if columnas_numericas else columnas_todas)
            var_color = st.selectbox("Color (Categórica, opcional):", [None] + columnas_texto)
            var_size = st.selectbox("Tamaño Burbuja (Numérica, opcional):", [None] + columnas_numericas)
            
            if st.button("Generar Gráfico de Relación"):
                df = con.execute(f"SELECT * FROM datos_actuales LIMIT 2000").fetchdf()
                
                if tipo_grafico == "Dispersión (Scatter)":
                    fig = px.scatter(df, x=var_x, y=var_y, color=var_color)
                elif tipo_grafico == "Burbujas":
                    fig = px.scatter(df, x=var_x, y=var_y, color=var_color, size=var_size)
                elif tipo_grafico == "Mapa de Calor (Correlación)":
                    if len(columnas_numericas) > 1:
                        fig = px.imshow(df[columnas_numericas].corr(), text_auto=True, aspect="auto")
                    else:
                        st.warning("Se necesitan al menos 2 variables numéricas para una matriz de correlación.")
                        fig = None
                elif tipo_grafico == "Coordenadas Paralelas":
                    fig = px.parallel_coordinates(df, color=var_color if var_color else columnas_numericas[0])
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        elif categoria_grafico == "Series Temporales":
            tipo_grafico = st.selectbox("Tipo de gráfico:", ["Líneas", "Áreas"])
            var_x_tiempo = st.selectbox("Variable de Fecha/Tiempo (Eje X):", columnas_todas)
            var_y_tiempo = st.selectbox("Variable a medir (Eje Y):", columnas_numericas if columnas_numericas else columnas_todas)
            
            if st.button("Generar Serie Temporal"):
                df = con.execute(f"SELECT {var_x_tiempo}, {var_y_tiempo} FROM datos_actuales ORDER BY {var_x_tiempo}").fetchdf()
                
                if tipo_grafico == "Líneas":
                    fig = px.line(df, x=var_x_tiempo, y=var_y_tiempo)
                elif tipo_grafico == "Áreas":
                    fig = px.area(df, x=var_x_tiempo, y=var_y_tiempo)
                st.plotly_chart(fig, use_container_width=True)

    # --- PESTAÑA 3: HALLAZGOS ---
    with tab3:
        st.subheader("🧠 Consejero Estadístico Inteligente")
        st.info("El consejero detectará automáticamente si tus datos son de una encuesta o de un estudio científico (ej. clima).")
        
        if st.button("Ejecutar Análisis de Hallazgos"):
            num_num = len(columnas_numericas)
            num_txt = len(columnas_texto)
            total = con.execute("SELECT COUNT(*) FROM datos_actuales").fetchone()[0]
            
            st.markdown("### 📋 Reporte de Hallazgos")
            
            if num_num > num_txt:
                st.warning("**Diagnóstico del Sistema:** He detectado un dataset de tipo **Científico / Continuo** (como el de Cambio Climático).")
                st.markdown(f"""
                *   **Total de registros analizados:** {total}
                *   **Interpretación:** Tienes {num_num} variables numéricas y {num_txt} categóricas. El enfoque ideal no es contar personas, sino **analizar tendencias**.
                *   **Recomendación:** Usa la pestaña de *Series Temporales* si tienes fechas, o el *Mapa de Calor* para ver qué variables están altamente correlacionadas. 
                """)
                
                st.markdown("**Búsqueda de Valores Atípicos (Outliers):**")
                for col in columnas_numericas[:3]: 
                    q = f"SELECT MAX({col}) as maximo, MIN({col}) as minimo, AVG({col}) as promedio FROM datos_actuales"
                    res = con.execute(q).fetchone()
                    if res[2] is not None:
                        st.write(f"- En `{col}`, el promedio es **{res[2]:.2f}**, con valores entre {res[1]:.2f} y {res[0]:.2f}.")
                    
            else:
                st.info("**Diagnóstico del Sistema:** He detectado un dataset de tipo **Encuesta / Cualitativo**.")
                df_nulos = con.execute(f"""
                    SELECT column_name, null_percentage 
                    FROM (SUMMARIZE datos_actuales) 
                    ORDER BY null_percentage DESC LIMIT 1
                """).fetchdf()
                
                col_nulos = df_nulos.iloc[0]['column_name']
                pct_nulos = df_nulos.iloc[0]['null_percentage']
                
                st.markdown(f"""
                *   **Total de encuestados analizados:** {total}
                *   **Alerta de calidad:** La variable `{col_nulos}` presenta un **{pct_nulos:.2f}%** de valores nulos. Revisa esa pregunta.
                *   **Recomendación metodológica:** Con una muestra de {total} casos, puedes calcular el margen de error para la encuesta general. Usa las gráficas de *Categorías* para ver la distribución de frecuencias.
                """)

    con.close()

else:
    st.info("👈 Por favor, sube un archivo CSV o selecciona uno existente en la barra lateral para comenzar.")
