 ############################################################################
        # NDVI
        ############################################################################

        # #NDVI SOLO CON INTERPOLACION DIARIA

        # # DataFrame final que almacenará los resultados
        # final_df_list = []

        # # Convertir las columnas de fecha a datetime
        # filtered_df['START_DATE'] = pd.to_datetime(filtered_df['START_DATE'])
        # filtered_df['END_DATE'] = pd.to_datetime(filtered_df['END_DATE'])

        # # Filtrar las filas con geometría válida
        # filtered_df = filtered_df[filtered_df['geometry'].notnull()]

        # # Cantidad de días antes de START_DATE y después de END_DATE que quieres incluir
        # days_before_start = 30
        # days_after_end = 30

        # for index, row in filtered_df.iterrows():
        #     # Extraer la geometría individual y asegurar que es un DataFrame
        #     lote_gdf_filtrado = pd.DataFrame([row])

        #     print(f"Procesando el índice: {index}")

        #     # Calcular la fecha de inicio extendida y la fecha de fin extendida
        #     extended_start_date = row['START_DATE'] - timedelta(days=days_before_start)
        #     extended_end_date = row['END_DATE'] + timedelta(days=days_after_end)

        #     # Llamar a la función con la geometría actual y las fechas extendidas
        #     try:
        #         df_temp = extract_mean_ndvi_date(
        #             lote_gdf_filtrado,
        #             extended_start_date.strftime('%Y-%m-%d'),
        #             extended_end_date.strftime('%Y-%m-%d')
        #         )
        #     except Exception as e:
        #         print(f"Error procesando el índice {index}: {e}")
        #         continue

        #     if df_temp.empty:
        #         print(f"No se encontraron datos NDVI para el índice: {index}")
        #         continue

        #     # Obtener el nombre de la geometría
        #     geom_name = row["field_name"]

        #     # Agregar el nombre de la geometría como columna
        #     df_temp["Lote"] = geom_name

        #     # Agregar el DataFrame temporal a la lista
        #     final_df_list.append(df_temp)

        # # Concatenar todos los DataFrames temporales en el DataFrame final
        # if final_df_list:
        #     final_df = pd.concat(final_df_list, ignore_index=True)
        # else:
        #     st.error("No se encontraron datos NDVI para ninguna geometría.")
        #     final_df = pd.DataFrame()

        # # Continuar solo si final_df no está vacío
        # if not final_df.empty:
        #     # Crear una tabla pivot con 'Date' como índice, 'Lote' como columnas y 'Mean_NDVI' como valores
        #     pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')
        #     pivot_df.reset_index(inplace=True)

        #     # Convertir la columna 'Date' a datetime
        #     pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

        #     # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
        #     min_date = pivot_df['Date'].min()
        #     max_date = pivot_df['Date'].max()
        #     all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

        #     # Convertir fechas a un formato numérico (número de días desde la primera fecha)
        #     pivot_df['DateNum'] = (pivot_df['Date'] - min_date) / np.timedelta64(1, 'D')
        #     date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

        #     # Preparar un nuevo DataFrame para almacenar resultados interpolados
        #     interpolated_df = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

        #     # Interpolar valores faltantes para cada lote usando RBFInterpolator
        #     for column in pivot_df.columns:
        #         if column not in ['Date', 'DateNum']:
        #             # Filtrar valores nulos y preparar datos para la interpolación
        #             x = pivot_df.loc[pivot_df[column].notna(), 'DateNum']
        #             y = pivot_df.loc[pivot_df[column].notna(), column]

        #             if x.empty or y.empty:
        #                 print(f"No hay datos para interpolar en la columna: {column}")
        #                 continue

        #             # Crear el interpolador RBF
        #             rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

        #             # Interpolar valores para todas las fechas en interpolated_df
        #             y_interp = rbf(date_num_all.values[:, None])

        #             # Almacenar resultados interpolados en el DataFrame
        #             interpolated_df[column] = y_interp

        #     # DataFrame de resultados interpolados antes del filtrado por fecha
        #     datos_interpolados = interpolated_df.copy()

        #     # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
        #     start_date = filtered_df['START_DATE'].min()
        #     end_date = filtered_df['END_DATE'].max()
        #     interpolated_df = interpolated_df[(interpolated_df['Date'] >= start_date) & (interpolated_df['Date'] <= end_date)]

        #     # Eliminar la columna 'DateNum' del DataFrame interpolado
        #     interpolated_df.drop(columns=['DateNum'], inplace=True)

        #     interpolated_df.reset_index(drop=True, inplace=True)
        #     interpolated_df.index += 1

            # st.write("Datos Interpolados:")
            # st.write(datos_interpolados)
            # st.write(interpolated_df)
        ############################################################

        # PRUEBA KNN

        # # DataFrame final que almacenará los resultados
        # final_df_list = []

        # # Convertir las columnas de fecha a datetime
        # filtered_df['START_DATE'] = pd.to_datetime(filtered_df['START_DATE'])
        # filtered_df['END_DATE'] = pd.to_datetime(filtered_df['END_DATE'])

        # # Filtrar las filas con geometría válida
        # filtered_df = filtered_df[filtered_df['geometry'].notnull()]

        # # Cantidad de días antes de START_DATE y después de END_DATE que quieres incluir
        # days_before_start = 30
        # days_after_end = 30

        # for index, row in filtered_df.iterrows():
        #     # Extraer la geometría individual y asegurar que es un DataFrame
        #     lote_gdf_filtrado = pd.DataFrame([row])

        #     print(f"Procesando el índice: {index}")

        #     # Calcular la fecha de inicio extendida y la fecha de fin extendida
        #     extended_start_date = row['START_DATE'] - timedelta(days=days_before_start)
        #     extended_end_date = row['END_DATE'] + timedelta(days=days_after_end)

        #     # Llamar a la función con la geometría actual y las fechas extendidas
        #     try:
        #         df_temp = extract_mean_ndvi_date(
        #             lote_gdf_filtrado,
        #             extended_start_date.strftime('%Y-%m-%d'),
        #             extended_end_date.strftime('%Y-%m-%d')
        #         )
        #     except Exception as e:
        #         print(f"Error procesando el índice {index}: {e}")
        #         continue

        #     if df_temp.empty:
        #         print(f"No se encontraron datos NDVI para el índice: {index}")
        #         continue

        #     # Obtener el nombre de la geometría
        #     geom_name = row["field_name"]

        #     # Agregar el nombre de la geometría como columna
        #     df_temp["Lote"] = geom_name

        #     # Agregar el DataFrame temporal a la lista
        #     final_df_list.append(df_temp)

        # # Concatenar todos los DataFrames temporales en el DataFrame final
        # if final_df_list:
        #     final_df = pd.concat(final_df_list, ignore_index=True)
        # else:
        #     st.error("No se encontraron datos NDVI para ninguna geometría.")
        #     final_df = pd.DataFrame()

        # # Continuar solo si final_df no está vacío
        # if not final_df.empty:
        #     # Crear una tabla pivot con 'Date' como índice, 'Lote' como columnas y 'Mean_NDVI' como valores
        #     pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')
        #     pivot_df.reset_index(inplace=True)

        #     # Convertir la columna 'Date' a datetime
        #     pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

        #     # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
        #     min_date = pivot_df['Date'].min()
        #     max_date = pivot_df['Date'].max()
        #     all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

        #     # Convertir fechas a un formato numérico (número de días desde la primera fecha)
        #     pivot_df['DateNum'] = (pivot_df['Date'] - min_date) / np.timedelta64(1, 'D')
        #     date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

        #     # Imputación de datos faltantes usando la media
        #     imputer = SimpleImputer(strategy='mean')

        #     for column in pivot_df.columns:
        #         if column not in ['Date', 'DateNum']:
        #             # Imputar valores faltantes con la media
        #             pivot_df[[column]] = imputer.fit_transform(pivot_df[[column]])

        #     # Limpieza de datos utilizando KNN para cada lote
        #     lof = LocalOutlierFactor(n_neighbors=20, contamination=0.1)

        #     for column in pivot_df.columns:
        #         if column not in ['Date', 'DateNum']:
        #             # Filtrar valores nulos y preparar datos para la interpolación
        #             x = pivot_df['DateNum'].values.reshape(-1, 1)
        #             y = pivot_df[column].values

        #             if x.size == 0 or y.size == 0:
        #                 print(f"No hay datos suficientes para procesar en la columna: {column}")
        #                 continue

        #             # Detectar outliers
        #             outliers = lof.fit_predict(x)
        #             # Reemplazar outliers por NaN en el DataFrame original
        #             pivot_df.loc[outliers == -1, column] = np.nan

        #     # Preparar un nuevo DataFrame para almacenar resultados interpolados
        #     interpolated_df = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

        #     # Interpolar valores faltantes para cada lote usando RBFInterpolator
        #     for column in pivot_df.columns:
        #         if column not in ['Date', 'DateNum']:
        #             # Filtrar valores nulos y preparar datos para la interpolación
        #             x = pivot_df.loc[pivot_df[column].notna(), 'DateNum']
        #             y = pivot_df.loc[pivot_df[column].notna(), column]

        #             if x.empty or y.empty:
        #                 print(f"No hay datos para interpolar en la columna: {column}")
        #                 continue

        #             # Crear el interpolador RBF
        #             rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

        #             # Interpolar valores para todas las fechas en interpolated_df
        #             y_interp = rbf(date_num_all.values[:, None])

        #             # Almacenar resultados interpolados en el DataFrame
        #             interpolated_df[column] = y_interp

        #     # DataFrame de resultados interpolados antes del filtrado por fecha
        #     datos_interpolados = interpolated_df.copy()

        #     # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
        #     start_date = filtered_df['START_DATE'].min()
        #     end_date = filtered_df['END_DATE'].max()
        #     interpolated_df = interpolated_df[(interpolated_df['Date'] >= start_date) & (interpolated_df['Date'] <= end_date)]

        #     # Eliminar la columna 'DateNum' del DataFrame interpolado
        #     interpolated_df.drop(columns=['DateNum'], inplace=True)

        #     interpolated_df.reset_index(drop=True, inplace=True)
        #     interpolated_df.index += 1

        ###################################################################

        #Suavizado de media movil como limpieza con ventana diaria cada 5 dias, revisita de sentinel

        # # DataFrame final que almacenará los resultados
        # final_df_list = []

        # # Convertir las columnas de fecha a datetime
        # filtered_df['START_DATE'] = pd.to_datetime(filtered_df['START_DATE'])
        # filtered_df['END_DATE'] = pd.to_datetime(filtered_df['END_DATE'])

        # # Filtrar las filas con geometría válida
        # filtered_df = filtered_df[filtered_df['geometry'].notnull()]

        # # Cantidad de días antes de START_DATE y después de END_DATE que quieres incluir
        # days_before_start = 30
        # days_after_end = 30

        # for index, row in filtered_df.iterrows():
        #     # Extraer la geometría individual y asegurar que es un DataFrame
        #     lote_gdf_filtrado = pd.DataFrame([row])

        #     print(f"Procesando el índice: {index}")

        #     # Calcular la fecha de inicio extendida y la fecha de fin extendida
        #     extended_start_date = row['START_DATE'] - timedelta(days=days_before_start)
        #     extended_end_date = row['END_DATE'] + timedelta(days=days_after_end)

        #     # Llamar a la función con la geometría actual y las fechas extendidas
        #     try:
        #         df_temp = extract_mean_ndvi_date(
        #             lote_gdf_filtrado,
        #             extended_start_date.strftime('%Y-%m-%d'),
        #             extended_end_date.strftime('%Y-%m-%d')
        #         )
        #     except Exception as e:
        #         print(f"Error procesando el índice {index}: {e}")
        #         continue

        #     if df_temp.empty:
        #         print(f"No se encontraron datos NDVI para el índice: {index}")
        #         continue

        #     # Obtener el nombre de la geometría
        #     geom_name = row["field_name"]

        #     # Agregar el nombre de la geometría como columna
        #     df_temp["Lote"] = geom_name

        #     # Agregar el DataFrame temporal a la lista
        #     final_df_list.append(df_temp)

        # # Concatenar todos los DataFrames temporales en el DataFrame final
        # if final_df_list:
        #     final_df = pd.concat(final_df_list, ignore_index=True)
        # else:
        #     st.error("No se encontraron datos NDVI para ninguna geometría.")
        #     final_df = pd.DataFrame()

        # # Continuar solo si final_df no está vacío
        # if not final_df.empty:
        #     # Crear una tabla pivot con 'Date' como índice, 'Lote' como columnas y 'Mean_NDVI' como valores
        #     pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')
        #     pivot_df.reset_index(inplace=True)

        #     # Convertir la columna 'Date' a datetime
        #     pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

        #     # Aplicar suavizado por media móvil para cada columna
        #     window_size = 5  # Puedes ajustar el tamaño de la ventana según tus necesidades
        #     for column in pivot_df.columns:
        #         if column not in ['Date']:
        #             pivot_df[column] = pivot_df[column].rolling(window=window_size, min_periods=1, center=True).mean()

        #     # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
        #     min_date = pivot_df['Date'].min()
        #     max_date = pivot_df['Date'].max()
        #     all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

        #     # Convertir fechas a un formato numérico (número de días desde la primera fecha)
        #     pivot_df['DateNum'] = (pivot_df['Date'] - min_date) / np.timedelta64(1, 'D')
        #     date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

        #     # Preparar un nuevo DataFrame para almacenar resultados interpolados
        #     interpolated_df = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

        #     # Interpolar valores faltantes para cada lote usando RBFInterpolator
        #     for column in pivot_df.columns:
        #         if column not in ['Date', 'DateNum']:
        #             # Filtrar valores nulos y preparar datos para la interpolación
        #             x = pivot_df.loc[pivot_df[column].notna(), 'DateNum']
        #             y = pivot_df.loc[pivot_df[column].notna(), column]

        #             if x.empty or y.empty:
        #                 print(f"No hay datos para interpolar en la columna: {column}")
        #                 continue

        #             # Crear el interpolador RBF
        #             rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

        #             # Interpolar valores para todas las fechas en interpolated_df
        #             y_interp = rbf(date_num_all.values[:, None])

        #             # Almacenar resultados interpolados en el DataFrame
        #             interpolated_df[column] = y_interp

        #     # DataFrame de resultados interpolados antes del filtrado por fecha
        #     datos_interpolados = interpolated_df.copy()

        #     # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
        #     start_date = filtered_df['START_DATE'].min()
        #     end_date = filtered_df['END_DATE'].max()
        #     interpolated_df = interpolated_df[(interpolated_df['Date'] >= start_date) & (interpolated_df['Date'] <= end_date)]

        #     # Eliminar la columna 'DateNum' del DataFrame interpolado
        #     interpolated_df.drop(columns=['DateNum'], inplace=True)

        #     interpolated_df.reset_index(drop=True, inplace=True)
        #     interpolated_df.index += 1