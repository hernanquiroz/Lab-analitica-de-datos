import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
import scipy.stats as stats
import statsmodels.api as sm

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Laboratorio de Análisis", page_icon="📊", layout="wide")
DB_PATH = 'data/02_processed/laboratorio.duckdb'
DATA_DIR = 'data/01_raw/'
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs('data/02_processed/', exist_ok=True)

def get_connection():
    return duckdb.connect(DB_PATH)

# --- BARRA LATERAL ---
st.sidebar.markdown("---")
st.sidebar.markdown("<div style='text-align: center; color: gray;'><small>Diseño Vibe coding por:<br><b>Ing. Hernan Quiroz</b></small></div>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 1. Subir archivo
st.sidebar.header("📤 Subir nuevo CSV")
uploaded_file = st.sidebar.file_uploader("Selecciona un archivo CSV", type=["csv"])
if uploaded_file is not None:
    with open(os.path.join(DATA_DIR, uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Archivo guardado: {uploaded_file.name}")

# 2. Seleccionar archivo
st.sidebar.header("🔍 Archivo en análisis")
archivos_disponibles = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
if archivos_disponibles:
    archivo_seleccionado = st.sidebar.selectbox("Selecciona archivo:", archivos_disponibles)
else:
    archivo_seleccionado = None
    st.sidebar.warning("No hay archivos CSV.")

# 3. Borrar archivo
st.sidebar.header("🗑️ Eliminar archivo")
if archivo_seleccionado:
    if st.sidebar.checkbox(f"Confirmo borrar: {archivo_seleccionado}"):
        if st.sidebar.button("Borrar archivo"):
            os.remove(os.path.join(DATA_DIR, archivo_seleccionado))
            st.sidebar.success("Archivo eliminado.")
            st.rerun()

# --- ÁREA PRINCIPAL ---
st.title("📊 Laboratorio de Ciclo de Vida del Dato")
con = get_connection()

if archivo_seleccionado:
    ruta_csv = os.path.join(DATA_DIR, archivo_seleccionado)
    con.execute(f"CREATE OR REPLACE VIEW datos_raw AS SELECT * FROM read_csv_auto('{ruta_csv}')")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧹 1. Limpieza", "🔎 2. Ficha Técnica", "📈 3. Gráficos Estadísticos", "📥 4. Exportar"
    ])

    # ==========================================
    # PESTAÑA 1: LIMPIEZA
    # ==========================================
    with tab1:
        st.subheader("Fase de Calidad y Limpieza de Datos")
        info_cols = con.execute("DESCRIBE datos_raw").fetchdf()
        todas_cols = info_cols['column_name'].tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            eliminar_duplicados = st.checkbox("Eliminar filas duplicadas", value=True)
            accion_nulos = st.selectbox("Tratamiento de nulos:", ["Mantener", "Eliminar filas", "Rellenar con 0 (Numéricos)"])
        with col2:
            cols_texto = info_cols[info_cols['column_type'].str.contains('VARCHAR')]['column_name'].tolist()
            cols_a_limpiar = st.multiselect("Estandarizar texto (Mayúsculas y sin espacios):", cols_texto)
            
        st.markdown("---")
        nueva_col_nombre = st.text_input("Nueva variable (Nombre):")
        nueva_col_formula = st.text_input("Fórmula SQL (ej. columna_a / columna_b):")
        
        if st.button("🚀 Ejecutar Limpieza", type="primary"):
            query = "SELECT "
            if nueva_col_nombre and nueva_col_formula:
                query += f"({nueva_col_formula}) AS {nueva_col_nombre}, "
            for c in todas_cols:
                if c in cols_a_limpiar:
                    query += f"UPPER(TRIM({c})) AS {c}, "
                else:
                    query += f"{c}, "
            query = query.rstrip(", ") + f" FROM datos_raw"
            
            if eliminar_duplicados:
                query = f"SELECT DISTINCT * FROM ({query})"
                
            try:
                con.execute(f"CREATE OR REPLACE TABLE datos_limpios AS {query}")
                st.success("¡Limpieza ejecutada! Tabla 'datos_limpios' creada.")
                st.dataframe(con.execute("SELECT * FROM datos_limpios LIMIT 5").fetchdf())
            except Exception as e:
                st.error(f"Error: {e}")

    # ==========================================
    # PESTAÑA 2: FICHA TÉCNICA
    # ==========================================
    with tab2:
        st.subheader("Perfil Estadístico")
        tabla = "datos_limpios" if "datos_limpios" in [t[0] for t in con.execute("SHOW TABLES").fetchall()] else "datos_raw"
        st.info(f"Mostrando ficha de: **{tabla}**")
        if st.button("Generar Ficha Técnica"):
            st.dataframe(con.execute(f"SUMMARIZE {tabla}").fetchdf())

    # ==========================================
    # PESTAÑA 3: CATÁLOGO COMPLETO DE GRÁFICOS
    # ==========================================
    with tab3:
        st.subheader("📈 Catálogo de Visualización Estadística")
        
        # Detectar tabla a usar
        try:
            con.execute("SELECT 1 FROM datos_limpios LIMIT 1")
            tabla = "datos_limpios"
        except:
            tabla = "datos_raw"
            
        info_grafico = con.execute(f"DESCRIBE {tabla}").fetchdf()
        cols_num = info_grafico[info_grafico['column_type'].str.contains('INT|DOUBLE|FLOAT|DECIMAL')]['column_name'].tolist()
        cols_txt = info_grafico[info_grafico['column_type'].str.contains('VARCHAR')]['column_name'].tolist()
        cols_todas = info_grafico['column_name'].tolist()

        st.markdown("### 1. Selecciona el propósito del análisis")
        categoria = st.selectbox("Familias Estadísticas:", [
            "1. Variables Cualitativas y Proporciones",
            "2. Variables Cuantitativas y Distribuciones",
            "3. Relaciones Bivariantes y Multivariantes",
            "4. Series Temporales",
            "5. Gráficos Especializados"
        ])

        # --- 1. CUALITATIVOS ---
        if categoria == "1. Variables Cualitativas y Proporciones":
            tipo = st.selectbox("Gráfico:", ["Barras", "Barras Apiladas", "Barras 100% Apiladas", "Pie / Anillo", "Treemap", "Embudo (Funnel)", "Pareto"])
            var_x = st.selectbox("Variable Categórica Principal:", cols_txt)
            var_color = st.selectbox("Variable de Agrupación (Opcional):", [None] + cols_txt)
            
            if st.button("Generar Gráfico"):
                df = con.execute(f"SELECT {var_x} {',' + var_color if var_color else ''}, COUNT(*) as Frecuencia FROM {tabla} GROUP BY 1 {',' + var_color if var_color else ''}").fetchdf()
                
                if tipo == "Barras": fig = px.bar(df, x=var_x, y='Frecuencia', color=var_color)
                elif tipo == "Barras Apiladas": fig = px.bar(df, x=var_x, y='Frecuencia', color=var_color, barmode='stack')
                elif tipo == "Barras 100% Apiladas": fig = px.bar(df, x=var_x, y='Frecuencia', color=var_color, barmode='group', text_auto=True).update_layout(barmode='relative')
                elif tipo == "Pie / Anillo": fig = px.pie(df, names=var_x, values='Frecuencia', hole=0.4 if "Anillo" in tipo else 0)
                elif tipo == "Treemap": fig = px.treemap(df, path=[var_x], values='Frecuencia')
                elif tipo == "Embudo (Funnel)": fig = px.funnel(df, x='Frecuencia', y=var_x)
                elif tipo == "Pareto":
                    df = df.sort_values('Frecuencia', ascending=False)
                    df['Acumulado'] = df['Frecuencia'].cumsum() / df['Frecuencia'].sum() * 100
                    fig = px.bar(df, x=var_x, y='Frecuencia')
                    fig.add_scatter(x=df[var_x], y=df['Acumulado'], name='% Acumulado', yaxis='y2')
                    fig.update_layout(yaxis2=dict(overlaying='y', side='right'))
                st.plotly_chart(fig, use_container_width=True)

        # --- 2. CUANTITATIVOS ---
        elif categoria == "2. Variables Cuantitativas y Distribuciones":
            tipo = st.selectbox("Gráfico:", ["Histograma", "Polígono / Ojiva", "Tallo y Hojas", "Boxplot", "Violín", "Densidad (KDE)", "Q-Q (Normalidad)", "Puntos (Dot Plot)", "Cascada"])
            var_y = st.selectbox("Variable Numérica:", cols_num)
            
            if st.button("Generar Gráfico"):
                df = con.execute(f"SELECT {var_y} FROM {tabla} WHERE {var_y} IS NOT NULL").fetchdf()
                
                if tipo == "Histograma": fig = px.histogram(df, x=var_y, nbins=30)
                elif tipo == "Polígono / Ojiva":
                    counts, bins = np.histogram(df[var_y], bins=20)
                    mids = (bins[:-1] + bins[1:]) / 2
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=mids, y=counts, mode='lines+markers', name='Polígono'))
                    fig.add_trace(go.Scatter(x=bins[1:], y=np.cumsum(counts), mode='lines', name='Ojiva (Acumulado)', yaxis='y2'))
                elif tipo == "Tallo y Hojas":
                    st.write("Representación de Tallo y Hojas (Textual):")
                    st.text(sm.graphics.plot_stem_and_leaf(df[var_y], plot=False))
                    fig = None
                elif tipo == "Boxplot": fig = px.box(df, y=var_y)
                elif tipo == "Violín": fig = px.violin(df, y=var_y, box=True)
                elif tipo == "Densidad (KDE)": fig = px.histogram(df, x=var_y, histnorm='density').update_traces(line_shape='spline')
                elif tipo == "Q-Q (Normalidad)":
                    qq = sm.qqplot(df[var_y], line='45', fit=True)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=qq.gca().lines[0].get_xdata(), y=qq.gca().lines[0].get_ydata(), mode='markers', name='Datos'))
                    fig.add_trace(go.Scatter(x=qq.gca().lines[1].get_xdata(), y=qq.gca().lines[1].get_ydata(), mode='lines', name='Ajuste Normal'))
                elif tipo == "Puntos (Dot Plot)": fig = px.strip(df, y=var_y)
                elif tipo == "Cascada":
                    df_agg = df.groupby(var_y).size().reset_index(name='Frecuencia').head(10)
                    fig = px.bar(df_agg, x=var_y, y='Frecuencia').update_traces(marker_color='blue')
                    fig.update_layout(title="Cascada de Frecuencias (Top 10 valores)")
                if fig: st.plotly_chart(fig, use_container_width=True)

        # --- 3. RELACIONES ---
        elif categoria == "3. Relaciones Bivariantes y Multivariantes":
            tipo = st.selectbox("Gráfico:", ["Dispersión (Scatter)", "Burbujas", "Matriz de Dispersión", "Mapa de Calor (Correlación)", "Coordenadas Paralelas", "Radar"])
            var_x = st.selectbox("Variable X:", cols_num)
            var_y = st.selectbox("Variable Y:", cols_num)
            var_color = st.selectbox("Color:", [None] + cols_txt)
            
            if st.button("Generar Gráfico"):
                df = con.execute(f"SELECT * FROM {tabla} LIMIT 3000").fetchdf()
                
                if tipo == "Dispersión (Scatter)": fig = px.scatter(df, x=var_x, y=var_y, color=var_color)
                elif tipo == "Burbujas": 
                    var_size = st.selectbox("Tamaño:", cols_num)
                    fig = px.scatter(df, x=var_x, y=var_y, size=var_size, color=var_color)
                elif tipo == "Matriz de Dispersión": fig = px.scatter_matrix(df, dimensions=cols_num[:4], color=var_color)
                elif tipo == "Mapa de Calor (Correlación)": fig = px.imshow(df[cols_num].corr(), text_auto=True, aspect="auto")
                elif tipo == "Coordenadas Paralelas": fig = px.parallel_coordinates(df, color=var_color if var_color else cols_num[0])
                elif tipo == "Radar":
                    df_radar = df.head(5) # Solo 5 filas para no saturar
                    fig = px.line_polar(df_radar.melt(id_vars=[var_x]), r='value', theta='variable', line_close=True)
                st.plotly_chart(fig, use_container_width=True)

        # --- 4. SERIES TEMPORALES ---
        elif categoria == "4. Series Temporales":
            tipo = st.selectbox("Gráfico:", ["Líneas", "Áreas", "Autocorrelación (ACF)", "Control Estadístico (Shewhart)"])
            var_tiempo = st.selectbox("Eje de Tiempo:", cols_todas)
            var_y = st.selectbox("Variable a medir:", cols_num)
            
            if st.button("Generar Gráfico"):
                df = con.execute(f"SELECT {var_tiempo}, {var_y} FROM {tabla} ORDER BY {var_tiempo}").fetchdf()
                
                if tipo == "Líneas": fig = px.line(df, x=var_tiempo, y=var_y)
                elif tipo == "Áreas": fig = px.area(df, x=var_tiempo, y=var_y)
                elif tipo == "Autocorrelación (ACF)":
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=sm.tsa.acf(df[var_y], nlags=40), y=range(41), mode='markers'))
                    fig.update_layout(title="ACF (Autocorrelación)")
                elif tipo == "Control Estadístico (Shewhart)":
                    media = df[var_y].mean()
                    std = df[var_y].std()
                    fig = px.line(df, x=var_tiempo, y=var_y)
                    fig.add_hline(y=media, line_dash="dash", line_color="green", annotation_text="Media")
                    fig.add_hline(y=media + 3*std, line_dash="dot", line_color="red", annotation_text="LSC (+3σ)")
                    fig.add_hline(y=media - 3*std, line_dash="dot", line_color="red", annotation_text="LIC (-3σ)")
                st.plotly_chart(fig, use_container_width=True)

        # --- 5. ESPECIALIZADOS ---
        elif categoria == "5. Gráficos Especializados":
            st.warning("⚠️ Nota: Gráficos como Curva ROC o Supervivencia (Kaplan-Meier) requieren una variable objetivo o de estado. Para este laboratorio, se implementan aproximaciones generales.")
            tipo = st.selectbox("Gráfico Especializado:", ["Curva ROC (Simulada)", "Gráfico de Bosque (Forest Plot)", "Diagrama de Sankey (Flujos)"])
            
            if tipo == "Curva ROC (Simulada)":
                var_y = st.selectbox("Variable numérica para umbral:", cols_num)
                if st.button("Generar ROC"):
                    df = con.execute(f"SELECT {var_y} FROM {tabla} WHERE {var_y} IS NOT NULL").fetchdf()
                    # Simulamos un target binario basado en la mediana para el ejemplo
                    y_true = (df[var_y] > df[var_y].median()).astype(int)
                    y_scores = df[var_y]
                    fpr, tpr, _ = sm.roc_curve(y_true, y_scores)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines', name='ROC Curve'))
                    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line_dash='dash', name='Aleatorio'))
                    fig.update_layout(xaxis_title='False Positive Rate', yaxis_title='True Positive Rate')
                    st.plotly_chart(fig, use_container_width=True)
            
            elif tipo == "Diagrama de Sankey (Flujos)":
                if len(cols_txt) >= 2:
                    var_origen = st.selectbox("Origen (Categórica):", cols_txt)
                    var_destino = st.selectbox("Destino (Categórica):", cols_txt)
                    if st.button("Generar Sankey"):
                        df = con.execute(f"SELECT {var_origen}, {var_destino}, COUNT(*) as value FROM {tabla} GROUP BY 1, 2").fetchdf()
                        labels = list(pd.concat([df[var_origen], df[var_destino]]).unique())
                        source = df[var_origen].apply(lambda x: labels.index(x)).tolist()
                        target = df[var_destino].apply(lambda x: labels.index(x)).tolist()
                        fig = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels), link=dict(source=source, target=target, value=df['value']))])
                        st.plotly_chart(fig, use_container_width=True)
                else: st.error("Se necesitan al menos 2 columnas categóricas para Sankey.")

    # ==========================================
    # PESTAÑA 4: EXPORTAR
    # ==========================================
    with tab4:
        st.subheader("📥 Descargar Datos Procesados")
        try:
            con.execute("SELECT 1 FROM datos_limpios LIMIT 1")
            total = con.execute("SELECT COUNT(*) FROM datos_limpios").fetchone()[0]
            st.success(f"✅ Datos limpios disponibles: **{total} filas**.")
            df_limpio = con.execute("SELECT * FROM datos_limpios").fetchdf()
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📄 Descargar CSV", df_limpio.to_csv(index=False).encode('utf-8'), f"limpio_{archivo_seleccionado}", "text/csv", type="primary")
            with col2:
                parquet_path = "data/02_processed/datos_limpios.parquet"
                con.execute(f"COPY datos_limpios TO '{parquet_path}' (FORMAT PARQUET)")
                with open(parquet_path, "rb") as f:
                    st.download_button("⚡ Descargar Parquet", f, "datos_limpios.parquet", "application/octet-stream")
        except:
            st.warning("⚠️ Aún no has ejecutado la limpieza en la Pestaña 1.")
            
    con.close()
else:
    st.info("👈 Sube un archivo CSV o selecciona uno de la lista para iniciar.")
