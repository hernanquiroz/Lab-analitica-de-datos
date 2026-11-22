# ... (código anterior de la pestaña 1) ...

with tab2:
    st.subheader("📈 Generador de Gráficos Estadísticos")
    
    # Obtener tipos de datos reales usando DuckDB
    info_columnas = con.execute("DESCRIBE datos_actuales").fetchdf()
    
    # Clasificar columnas
    columnas_numericas = info_columnas[info_columnas['column_type'].str.contains('INT|DOUBLE|FLOAT|DECIMAL|BIGINT')]['column_name'].tolist()
    columnas_texto = info_columnas[info_columnas['column_type'].str.contains('VARCHAR')]['column_name'].tolist()
    columnas_todas = info_columnas['column_name'].tolist()

    # --- MENÚ DE GRÁFICOS ---
    categoria_grafico = st.selectbox(
        "1. Selecciona la familia de gráfico:", 
        ["Cualitativos (Categorías)", "Cuantitativos (Distribuciones)", "Relaciones (Bivariante/Multivariante)", "Series Temporales"]
    )

    if categoria_grafico == "Cualitativos (Categorías)":
        tipo_grafico = st.selectbox("Tipo de gráfico:", ["Barras", "Torta (Pie)", "Anillo (Donut)", "Barras Apiladas", "Treemap", "Embudo (Funnel)", "Pareto"])
        var_x = st.selectbox("Variable categórica (Eje X):", columnas_texto)
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
        var_y = st.selectbox("Variable numérica:", columnas_numericas)
        
        if st.button("Generar Gráfico Cuantitativo"):
            # Cargamos los datos a un DataFrame de pandas para graficar
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
        var_x = st.selectbox("Variable X (Numérica):", columnas_numericas)
        var_y = st.selectbox("Variable Y (Numérica):", columnas_numericas)
        var_color = st.selectbox("Color (Categórica, opcional):", [None] + columnas_texto)
        var_size = st.selectbox("Tamaño Burbuja (Numérica, opcional):", [None] + columnas_numericas)
        
        if st.button("Generar Gráfico de Relación"):
            df = con.execute(f"SELECT * FROM datos_actuales LIMIT 1000").fetchdf() # Límite para no saturar
            
            if tipo_grafico == "Dispersión (Scatter)":
                fig = px.scatter(df, x=var_x, y=var_y, color=var_color)
            elif tipo_grafico == "Burbujas":
                fig = px.scatter(df, x=var_x, y=var_y, color=var_color, size=var_size)
            elif tipo_grafico == "Mapa de Calor (Correlación)":
                # DuckDB calcula la matriz de correlación
                cols_corr = ", ".join([f"CORR({c1}, {c2}) as {c1}_{c2}" for c1 in columnas_numericas for c2 in columnas_numericas])
                # (Nota: Para simplificar, Plotly puede hacer la matriz directo si le pasas el DataFrame)
                fig = px.imshow(df[columnas_numericas].corr(), text_auto=True, aspect="auto")
            elif tipo_grafico == "Coordenadas Paralelas":
                fig = px.parallel_coordinates(df, color=var_color if var_color else columnas_numericas[0])
            st.plotly_chart(fig, use_container_width=True)

    elif categoria_grafico == "Series Temporales":
        tipo_grafico = st.selectbox("Tipo de gráfico:", ["Líneas", "Áreas"])
        var_x_tiempo = st.selectbox("Variable de Fecha/Tiempo:", columnas_todas)
        var_y_tiempo = st.selectbox("Variable a medir:", columnas_numericas)
        
        if st.button("Generar Serie Temporal"):
            # En DuckDB ordenamos por tiempo
            df = con.execute(f"SELECT {var_x_tiempo}, {var_y_tiempo} FROM datos_actuales ORDER BY {var_x_tiempo}").fetchdf()
            
            if tipo_grafico == "Líneas":
                fig = px.line(df, x=var_x_tiempo, y=var_y_tiempo)
            elif tipo_grafico == "Áreas":
                fig = px.area(df, x=var_x_tiempo, y=var_y_tiempo)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("🧠 Consejero Estadístico Inteligente")
    st.info("El consejero detectará automáticamente si tus datos son de una encuesta o de un estudio científico (ej. clima).")
    
    if st.button("Ejecutar Análisis de Hallazgos"):
        # 1. Clasificar el dataset basándonos en tipos de datos
        num_num = len(columnas_numericas)
        num_txt = len(columnas_texto)
        total = con.execute("SELECT COUNT(*) FROM datos_actuales").fetchone()[0]
        
        # 2. Lógica del consejero
        st.markdown("### 📋 Reporte de Hallazgos")
        
        if num_num > num_txt:
            st.warning("**Diagnóstico del Sistema:** He detectado un dataset de tipo **Científico / Continuo** (como el de Cambio Climático).")
            st.markdown(f"""
            *   **Total de registros analizados:** {total}
            *   **Interpretación:** Tienes {num_num} variables numéricas (variables continuas) y {num_txt} categóricas. El enfoque ideal no es contar personas, sino **analizar tendencias**.
            *   **Recomendación:** Usa la pestaña de *Series Temporales* si tienes fechas, o el *Mapa de Calor* para ver qué variables (ej. Temperatura y CO2) están altamente correlacionadas. 
            """)
            
            # Alerta extra: buscar atípicos
            st.markdown("**Búsqueda de Valores Atípicos (Outliers):**")
            for col in columnas_numericas[:3]: # Revisar las primeras 3 columnas numéricas
                q = f"SELECT MAX({col}) as maximo, MIN({col}) as minimo, AVG({col}) as promedio FROM datos_actuales"
                res = con.execute(q).fetchone()
                st.write(f"- En `{col}`, el promedio es **{res[2]:.2f}**, con valores entre {res[1]:.2f} y {res[0]:.2f}.")
                
        else:
            st.info("**Diagnóstico del Sistema:** He detectado un dataset de tipo **Encuesta / Cualitativo**.")
            # Buscar la columna con más nulos
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
