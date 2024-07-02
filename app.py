# Bibliotecas estándar de Python
import json

# Manipulación de datos y geometrías
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.integrate import trapz

#KNN
from sklearn.neighbors import LocalOutlierFactor
from sklearn.impute import SimpleImputer

from statsmodels.tsa.seasonal import seasonal_decompose

# Manejo de imágenes
from PIL import Image

# Integración web y aplicaciones interactivas
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.mandatory_date_range import date_range_picker
import streamlit_google_oauth as oauth
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt

# Manejo de geometrías
from shapely.geometry import shape, mapping, Point

# Earth Engine y mapeo avanzado
import ee
import geemap.foliumap as geemap
from shapely import wkt
import random 


# Interpolación, análisis espacial y NDVI
from ndvi import extract_mean_ndvi_date
from scipy.interpolate import RBFInterpolator

# Importar módulos o paquetes locales
from helper import translate, api_call_logo, api_call_fields_table, domains_areas_by_user
from secretManager import AWSSecret
import logging

# Manejo de Fechas
from datetime import datetime, timedelta

############################################################################
# Estilo
############################################################################

# Cargar la imagen
page_icon = Image.open("assets/favicon geoagro nuevo-13.png")

st.set_page_config(
    page_title="Tablero de Benckmarking",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://geoagro1.atlassian.net/servicedesk/customer/portal/5',
        'Report a bug': "https://geoagro1.atlassian.net/servicedesk/customer/portal/5",
        'About': "Dashboards. Powered by GeoAgro"
    }
)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


def main_app(user_info):

    #####################   API   #####################

    # Read the CSV file into a DataFrame
    marca_blanca = 'assets/GeoAgro_principal.png'

    ##################### USER INFO #####################
    user_info=st.session_state['user_info']

    print(st.session_state)
    language = user_info['language']
    email = user_info['email']
    env = user_info['env']
    st.session_state['env'] = env

    ##################### API DataFrame: helper.py -> api_call_fields_table #####################

    if env == 'test':
        secrets = json.loads(AWSSecret().get_secret(secret_name="test/apigraphql360", region_name="us-west-2"))
    elif env == 'prod':
        secrets = json.loads(AWSSecret().get_secret(secret_name="prod/apigraphql360-v2", region_name="us-west-2"))
    
    access_key_id = secrets['x-api-key']
    url = secrets['url']

    # Función para realizar la llamada a la API y cachear la respuesta
    @st.cache_data(show_spinner=False)
    def get_fields_table(user_info, access_key_id, url):
        df = api_call_fields_table(user_info, access_key_id, url)
        return df

    if env == 'test' or env == 'prod': # (env == 'prod' and user_info['domainId'] not in [1, 11178]):
        # Llamar a la función get_fields_table que está cacheada
        data, filtered_df = get_fields_table(user_info, access_key_id, url)

    ##################### API Logo Marca Blanca #####################
    # secrets = None
    # access_key_id = st.secrets["API_key"]
    if env == 'test':
        secrets = json.loads(AWSSecret().get_secret(secret_name="test/apigraphql360", region_name="us-west-2"))
    elif env == 'prod':
        secrets = json.loads(AWSSecret().get_secret(secret_name="prod/apigraphql360-v2", region_name="us-west-2"))

    access_key_id = secrets['x-api-key']
    url = secrets['url']
    
    @st.cache_data(show_spinner=False)
    def get_logo(user_info, access_key_id, url, default_logo_path):
        logo_image = api_call_logo(user_info, access_key_id,  url, default_logo_path)
        return logo_image

    logo_image = get_logo(user_info, access_key_id, url, default_logo_path='assets/GeoAgro_principal.png')
    st.session_state['logo_image'] = logo_image

    ##################### LANGUAGE  #####################

    c_1, c_2, c_3 = st.columns([1.5, 4.5, 1], gap="small")

    with c_1:
        st.image(logo_image)

    with c_3:   
        try:
            langs = ['es', 'en', 'pt']
            if language is not None:
                lang = st.selectbox(translate("language", language), label_visibility="hidden", options=langs, index=langs.index(language))
            else:  # from public link
                lang = st.selectbox(translate("es", language), label_visibility="hidden", options=langs)
            
            st.session_state['lang'] = lang
        except Exception as exception:
            lang = "es"
            st.session_state['lang'] = lang
            pass


    ##################### Titulo / solicitado por  #####################

    st.subheader(translate("title",lang), anchor=False)
    st.markdown(f'{translate("requested_by",lang)}<a style="color:blue;font-size:18px;">{""+email+""}</a> | <a style="color:blue;font-size:16px;" target="_self" href="/"> {translate("logout",lang)}</a>', unsafe_allow_html=True)

    if env == 'test' or env == 'prod': #(env == 'prod' and user_info['domainId'] not in [1, 11178]):
        with st.sidebar:
            
            ############################################################################
            # Area
            ############################################################################

            # Reemplaza valores en blanco o nulos en 'area_name' por '--'
            filtered_df['area_name'].fillna('--', inplace=True)

            # Luego continúa con el proceso como antes
            areas = sorted(filtered_df['area_name'].unique().tolist())

            container = st.container()
            select_all_areas = st.toggle(translate("select_all", lang), key='select_all_areas')

            if select_all_areas:
                selector_areas = container.multiselect(
                    translate("area", lang),
                    areas,
                    areas)  # Todos los workspaces están seleccionados por defecto
            else:
                default_area_name = filtered_df.loc[filtered_df['area_id'] == user_info['areaId'], 'area_name'].unique()
                selector_areas = container.multiselect(
                    translate("area", lang),
                    areas,
                    default=default_area_name,
                    placeholder=translate("choose_option", lang))

            ############################################################################
            # Workspace
            ############################################################################

            # Filtra el DataFrame basado en las áreas seleccionadas
            filtered_df = filtered_df[filtered_df['area_name'].isin(selector_areas)]

            # Obtén los nombres de los workspaces únicos del DataFrame filtrado
            workspaces = sorted(filtered_df['workspace_name'].unique().tolist())

            container = st.container()
            select_all = st.toggle(translate("select_all", lang))

            if select_all:
                selector_workspaces = container.multiselect(
                    translate("workspace", lang),
                    workspaces,
                    workspaces)  # Todos los workspaces están seleccionados por defecto
            else:
                default_workspace_name = filtered_df.loc[filtered_df['workspace_id'] == user_info['workspaceId'], 'workspace_name'].unique()
                selector_workspaces = container.multiselect(
                    translate("workspace", lang),
                    workspaces,
                    default=default_workspace_name,
                    placeholder=translate("choose_option", lang))

            ############################################################################
            # Season
            ############################################################################

            # Filtra el DataFrame basado en las áreas seleccionadas
            filtered_df = filtered_df[filtered_df['workspace_name'].isin(selector_workspaces)]

            # Obtén los nombres de los workspaces únicos del DataFrame filtrado
            seasons = sorted(filtered_df['season_name'].unique().tolist())

            container = st.container()
            select_all_seasons = st.toggle(translate("select_all", lang), key='select_all_seasons')

            if select_all_seasons:
                selector_seasons = container.multiselect(
                    translate("season", lang),
                    seasons,
                    seasons)  # Todos los workspaces están seleccionados por defecto
            else:
                default_season_name = filtered_df.loc[filtered_df['season_id'] == user_info['seasonId'], 'season_name'].unique()
                selector_seasons = container.multiselect(
                    translate("season", lang),
                    seasons,
                    default=default_season_name,
                    placeholder=translate("choose_option", lang)) 

            ############################################################################
            # Farm
            ############################################################################

            # Filtra el DataFrame basado en las áreas seleccionadas
            filtered_df = filtered_df[filtered_df['season_name'].isin(selector_seasons)]

            # Obtén los nombres de los workspaces únicos del DataFrame filtrado
            farms = sorted(filtered_df['farm_name'].unique().tolist())

            container = st.container()
            select_all_farms = st.toggle(translate("select_all", lang), key='select_all_farms')

            if select_all_farms:
                selector_farms = container.multiselect(
                    translate("farm", lang),
                    farms,
                    farms)  # Todos los workspaces están seleccionados por defecto
            else:
                default_farm_name = filtered_df.loc[filtered_df['farm_id'] == user_info['farmId'], 'farm_name'].unique()
                selector_farms = container.multiselect(
                    translate("farm", lang),
                    farms,
                    default=default_farm_name,
                    placeholder=translate("choose_option", lang)) 

            ############################################################################
            # Cultivos
            ############################################################################

            # Filtra el DataFrame basado en las áreas seleccionadas
            filtered_df = filtered_df[filtered_df['farm_name'].isin(selector_farms)]

            # No obtengas los nombres únicos, en su lugar, utiliza todos los nombres
            cultivos = sorted(filtered_df['crop'].unique().tolist())

            container = st.container()
            select_all_cultivos = st.toggle(translate("select_all", lang), value=True, key='select_all_cultivos')

            if select_all_cultivos:
                selector_cultivos = container.multiselect(
                    translate("crop", lang),
                    cultivos)  # Todos los cultivos están seleccionados por defecto
            else:
                selector_cultivos = container.multiselect(
                    translate("crop", lang),
                    cultivos,
                    placeholder=translate("choose_option", lang))
                
            ############################################################################
            # Híbridos / Variedades
            ############################################################################

            # Filtra el DataFrame basado en las áreas seleccionadas
            filtered_df = filtered_df[filtered_df['crop'].isin(selector_cultivos)]

            # No obtengas los nombres únicos, en su lugar, utiliza todos los nombres
            hibrido = sorted(filtered_df['hybrid'].unique().tolist())

            container = st.container()
            select_all_hibrido = st.toggle(translate("select_all", lang), value=True, key='select_all_hibrido')

            if select_all_hibrido:
                selector_hibrido = container.multiselect(
                    translate("hybrid_variety", lang),
                    hibrido,
                    hibrido)  # Todos los hibrido están seleccionados por defecto
            else:
                selector_hibrido = container.multiselect(
                    translate("hybrid_variety", lang),
                    hibrido,
                    placeholder=translate("choose_option", lang))
                                    
            ############################################################################
            # Field
            ############################################################################

            # Filtra el DataFrame basado en los híbridos seleccionados
            filtered_df = filtered_df[filtered_df['hybrid'].isin(selector_hibrido)]

            # Obtén los nombres de los fields únicos del DataFrame filtrado
            fields = sorted(filtered_df['field_name'].unique().tolist())

            container = st.container()
            select_all_fields = st.toggle(translate("select_all", lang), value=True, key='select_all_fields')

            if select_all_fields:
                selector_fields = container.multiselect(
                    translate("field", lang),
                    fields,
                    fields)  # Todos los fields están seleccionados por defecto
            else:
            # Establecer default_field_name basado en los híbridos seleccionados
                default_field_name = filtered_df.loc[filtered_df['hybrid'].isin(selector_hibrido), 'field_name'].unique().tolist()
                selector_fields = container.multiselect(
                    translate("field", lang),
                    fields,
                    default=default_field_name,
                    placeholder=translate("choose_option", lang))

            # Filtra el DataFrame basado en los fields seleccionados
            filtered_df = filtered_df[filtered_df['field_name'].isin(selector_fields)]

            # Reinicia el índice del DataFrame filtrado
            filtered_df.reset_index(drop=True, inplace=True)
            filtered_df.index += 1

            df_lotes_seleccionados=filtered_df
            ###########################################################################
            #Fecha
            ###########################################################################
            
            # Asegúrate de que start_date, end_date y crop_date están en formato datetime
            filtered_df['start_date'] = pd.to_datetime(filtered_df['start_date'], errors='coerce')
            filtered_df['end_date'] = pd.to_datetime(filtered_df['end_date'], errors='coerce')
            filtered_df['crop_date'] = pd.to_datetime(filtered_df['crop_date'], errors='coerce')

            # Establecer el rango de fechas fijo
            min_date = datetime(2017, 3, 28) #Primera imagen de Sentinel disponible.
            max_date = datetime.now()

            # Fijar default_start
            if filtered_df['crop_date'].notna().any():
                most_recent_crop_date = filtered_df['crop_date'].max()
                default_start = most_recent_crop_date - timedelta(days=60)
                if default_start < min_date:
                    default_start = min_date
            else:
                default_start = datetime.now() - timedelta(days=180)
                if default_start < min_date:
                    default_start = min_date

            # Fijar default_end
            days_diff = (datetime.now() - default_start).days
            if days_diff > 240:
                default_end = default_start + timedelta(days=240)
            else:
                default_end = datetime.now()

            # Asegurar que default_end no exceda max_date
            if default_end > max_date:
                default_end = max_date

            # Limitar el intervalo máximo de días a 240 entre default_start y default_end
            if (default_end - default_start).days > 240:
                default_end = default_start + timedelta(days=240)

            # Asegurar que default_end no es menor que default_start
            if default_end < default_start:
                default_end = default_start

            # Asegurar que default_start y default_end están dentro del rango permitido
            if default_start < min_date:
                default_start = min_date
            if default_start > max_date:
                default_start = max_date
            if default_end < min_date:
                default_end = min_date
            if default_end > max_date:
                default_end = max_date

            # Muestra el selector de rango de fechas
            #st.write(translate("select_date_range", lang))
            selected_date_range = st.date_input(
                translate("select_date_range", lang),
                value=(default_start.date(), default_end.date()),
                min_value=min_date.date(),
                max_value=max_date.date()
            )

            # Validar el rango de fechas seleccionado
            start_date, end_date = selected_date_range

            if start_date > end_date:
                st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
            elif (end_date - start_date).days > 240:
                st.error("El rango máximo permitido es de 240 días.")
            else:
                # Asignar las fechas seleccionadas a todas las filas de las columnas START_DATE y END_DATE
                filtered_df = filtered_df.assign(
                    START_DATE=start_date,
                    END_DATE=end_date
                )
            ###########################################################################
            #Tipo de limpieza
            ###########################################################################   
            
            # Configuración de las opciones
            options = [translate('cleaning_option',lang), translate('raw_data_option',lang)]
            default_option = translate('cleaning_option',lang)

            # Crear un contenedor
            container = st.container()

            # Agregar el selector al contenedor
            with container:
                selected_option = st.radio(translate('choose_option',lang), options, index=options.index(default_option))
            ############################################################################
            # Powered by GeoAgro Picture
            ############################################################################

            st.markdown(
                """
                <style>
                    div [data-testid=stImage]{
                        bottom:0;
                        display: flex;
                        margin-bottom:10px;
                    }
                </style>
                """, unsafe_allow_html=True
                )
                
            
            cI1,cI2,cI3=st.columns([1,4,1], gap="small")
            with cI1:
                pass
            with cI2:
                image = Image.open('assets/Powered by GeoAgro-01.png')
                new_image = image.resize((220, 35))
                st.image(new_image)
            with cI3:
                pass
            ############################################################################
        # Verifica si no hay lotes seleccionados
        if filtered_df.empty:
            st.warning(translate('select_warning',lang))
        else:    

            if selector_hibrido:

                st.divider()  # 👈 Draws a horizontal rule
                st.markdown('')
                st.markdown(f"<b>{translate('metrics', lang)}</b>", unsafe_allow_html=True)

                ############################################################################
                # Metricas
                ############################################################################

                col1, col2, col3, col4, col5 = st.columns(5)

                # Establecimientos
                col1.metric(
                    translate("farms", lang), 
                    len(filtered_df['farm_name'].unique())
                )

                # Lotes
                total_lotes = len(filtered_df['field_name'])
                col2.metric(
                    translate("fields", lang), 
                    total_lotes
                )

                # Hectáreas
                total_hectareas = sum(filtered_df['hectares'])  # Suma sin convertir a miles
                col3.metric(
                    translate("hectares", lang), 
                    f"{total_hectareas:,.0f}"  # Formatea con separadores de miles y sin decimales
                )

                # Cultivos
                col4.metric(
                    translate("crops", lang), 
                    len(filtered_df['crop'].unique())
                )

                # Híbridos
                col5.metric(
                    translate("hybrid_varieties", lang), 
                    len(filtered_df['hybrid'].unique())
                )

                # Agregar las métricas
                col1, col2, col3, col4, col5 = st.columns(5)

                style_metric_cards(border_left_color="#0e112c", box_shadow=False)
                        
            ############################################################################
            # INICIALIZA GEE Y CREA GDF
            ############################################################################

            # Crea una instancia de la clase AWSSecret y obtén el secreto para GEE
            gee_secrets = json.loads(AWSSecret().get_secret(secret_name="prod/streamlit/gee", region_name="us-east-1"))

            # Extrae client_email y la clave privada del secreto
            client_email = gee_secrets['client_email']
            private_key = gee_secrets['private_key']  # Asegúrate de que 'private_key' es el nombre correcto del campo en tu secreto

            # Configura las credenciales y inicializa Earth Engine
            credentials = ee.ServiceAccountCredentials(client_email, key_data=private_key)
            ee.Initialize(credentials)

            # Convertir la columna 'centroid' a objetos de geometría
            filtered_df['geometry'] = filtered_df['geom'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(filtered_df, geometry='geometry')
            
            ############################################################################
            # NDVI
            ############################################################################

            
            ###PARALELIZADO
            
            from concurrent.futures import ThreadPoolExecutor
            from scipy.signal import savgol_filter

                  

            final_df_list = []
            filtered_df['START_DATE'] = pd.to_datetime(filtered_df['START_DATE'])
            filtered_df['END_DATE'] = pd.to_datetime(filtered_df['END_DATE'])

            # Definir una función para procesar un índice dado y llamar a extract_mean_ndvi_date
            def process_index(index, row, days_before_start, days_after_end):
                lote_gdf_filtrado = pd.DataFrame([row])
                extended_start_date = row['START_DATE'] - timedelta(days=days_before_start)
                extended_end_date = row['END_DATE'] + timedelta(days=days_after_end)

                try:
                    df_temp = extract_mean_ndvi_date(
                        lote_gdf_filtrado,
                        extended_start_date.strftime('%Y-%m-%d'),
                        extended_end_date.strftime('%Y-%m-%d')
                    )
                except Exception as e:
                    print(f"Error procesando el índice {index}: {e}")
                    return None

                if df_temp.empty:
                    print(f"No se encontraron datos NDVI para el índice: {index}")
                    return None

                geom_name = row["field_name"]
                df_temp["Lote"] = geom_name

                return df_temp

            days_before_start = 30
            days_after_end = 30

            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(process_index, index, row, days_before_start, days_after_end)
                        for index, row in filtered_df.iterrows()]

                for future in futures:
                    result = future.result()
                    if result is not None and not result.empty:
                        final_df_list.append(result)

            if final_df_list:
                final_df = pd.concat(final_df_list, ignore_index=True)
            else:
                st.error("No se encontraron datos NDVI para ninguna geometría.")
                final_df = pd.DataFrame()

            # Continuar solo si final_df no está vacío
            if not final_df.empty:
                # Crear una tabla pivot con 'Date' como índice, 'Lote' como columnas y 'Mean_NDVI' como valores
                pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')
                pivot_df.reset_index(inplace=True)

                # Convertir la columna 'Date' a datetime
                pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

                pivot_esa = pivot_df
                pivot_sg=pivot_df

                #######################################################################
                #Solo filtro ESA + interpolacion

                # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
                min_date = pivot_esa['Date'].min()
                max_date = pivot_esa['Date'].max()
                all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

                # Convertir fechas a un formato numérico (número de días desde la primera fecha)
                pivot_esa['DateNum'] = (pivot_esa['Date'] - min_date) / np.timedelta64(1, 'D')
                date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

                # Preparar un nuevo DataFrame para almacenar resultados interpolados
                interpolated_df_esa = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

                # Interpolar valores faltantes para cada lote usando RBFInterpolator
                for column in pivot_esa.columns:
                    if column not in ['Date', 'DateNum']:
                        # Filtrar valores nulos y preparar datos para la interpolación
                        x = pivot_esa.loc[pivot_esa[column].notna(), 'DateNum']
                        y = pivot_esa.loc[pivot_esa[column].notna(), column]

                        if x.empty or y.empty:
                            print(f"No hay datos para interpolar en la columna: {column}")
                            continue

                        # Crear el interpolador RBF
                        rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

                        # Interpolar valores para todas las fechas en interpolated_df
                        y_interp = rbf(date_num_all.values[:, None])

                        # Almacenar resultados interpolados en el DataFrame
                        interpolated_df_esa[column] = y_interp

                # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                interpolated_df_esa = interpolated_df_esa[(interpolated_df_esa['Date'] >= start_date) & (interpolated_df_esa['Date'] <= end_date)]

                # Eliminar la columna 'DateNum' del DataFrame interpolado
                interpolated_df_esa.drop(columns=['DateNum'], inplace=True)

                interpolated_df_esa.reset_index(drop=True, inplace=True)
                interpolated_df_esa.index += 1

                #######################################################################
                #Savitzky–Golay 

                # Aplicar filtro de Savitzky–Golay para cada columna
                window_size = 20  # Tamaño de la ventana (debe ser un número impar)
                poly_order = 5    # Orden del polinomio

                for column in pivot_sg.columns:
                    if column not in ['Date']:
                        # Aplicar el filtro de Savitzky–Golay
                        pivot_sg[column] = savgol_filter(pivot_sg[column].interpolate(), window_length=window_size, polyorder=poly_order)

                # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
                min_date = pivot_sg['Date'].min()
                max_date = pivot_sg['Date'].max()
                all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

                # Convertir fechas a un formato numérico (número de días desde la primera fecha)
                pivot_sg['DateNum'] = (pivot_sg['Date'] - min_date) / np.timedelta64(1, 'D')
                date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

                # Preparar un nuevo DataFrame para almacenar resultados interpolados
                interpolated_df_sg = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

                # Interpolar valores faltantes para cada lote usando RBFInterpolator
                for column in pivot_sg.columns:
                    if column not in ['Date', 'DateNum']:
                        # Filtrar valores nulos y preparar datos para la interpolación
                        x = pivot_sg.loc[pivot_sg[column].notna(), 'DateNum']
                        y = pivot_sg.loc[pivot_sg[column].notna(), column]

                        if x.empty or y.empty:
                            print(f"No hay datos para interpolar en la columna: {column}")
                            continue

                        # Crear el interpolador RBF
                        rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

                        # Interpolar valores para todas las fechas en interpolated_df
                        y_interp = rbf(date_num_all.values[:, None])

                        # Almacenar resultados interpolados en el DataFrame
                        interpolated_df_sg[column] = y_interp

                # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                interpolated_df_sg = interpolated_df_sg[(interpolated_df_sg['Date'] >= start_date) & (interpolated_df_sg['Date'] <= end_date)]

                # Eliminar la columna 'DateNum' del DataFrame interpolado
                interpolated_df_sg.drop(columns=['DateNum'], inplace=True)

                interpolated_df_sg.reset_index(drop=True, inplace=True)
                interpolated_df_sg.index += 1

                ############################################################################
                #COLORES Y ORDEN DE LOS LOTES
                ############################################################################

                # Obtener la lista de lotes únicos y asignar colores
                lotes = sorted(filtered_df['field_name'].unique().tolist())
                selected_colors = px.colors.qualitative.T10

                # Crear un diccionario para asignar colores a cada lote
                color_map = {lote: {'color': selected_colors[i % len(selected_colors)], 'order': i} for i, lote in enumerate(lotes)}

                # Función para aplicar colores fijos a los gráficos
                def apply_colors(fig, data, color_column):
                    fig.for_each_trace(lambda t: t.update(marker_color=color_map.get(t.name, '#636efa')))
                    return fig
                
                def create_bar_chart(df, y_column, lotes, color_map):
                    data = []
                    for lot in lotes:
                        filtered_values = df[df['Lote'] == lot][y_column].values
                        if len(filtered_values) > 0:
                            data.append({
                                'x': lot,
                                'y': filtered_values[0],
                                'color': color_map.get(lot, '#4C78A8')  # Usar el color del color_map o un color por defecto
                            })
                        else:
                            data.append({
                                'x': lot,
                                'y': 0,
                                'color': color_map.get(lot, '#4C78A8')  # Usar el color del color_map o un color por defecto
                            })
                    
                    fig = go.Figure(data=[go.Bar(
                        x=[d['x'] for d in data],
                        y=[d['y'] for d in data],
                        marker_color=[d['color'] for d in data]
                    )])
                    
                    return fig

                

                ############################################################################
                #VISUALIZACIONES
                ############################################################################

                ############################################################################
                # TABLA RESUMEN LOTES
                
                st.divider()  # 👈 Draws a horizontal rule
                st.markdown('')
                st.markdown(f"<b>{translate('select_fields', lang)}</b>", unsafe_allow_html=True)

                # Agregar la columna de color al DataFrame
                df_lotes_seleccionados['color'] = df_lotes_seleccionados['field_name'].map(lambda x: color_map[x]['color'])
                df_lotes_seleccionados['order'] = df_lotes_seleccionados['field_name'].map(lambda x: color_map[x]['order'])

                # Ordenar el DataFrame por la columna 'order'
                df_lotes_seleccionados = df_lotes_seleccionados.sort_values(by='order')

                df_lotes_seleccionados.reset_index(drop=True, inplace=True)
                df_lotes_seleccionados.index += 1

                translations = {
                    'area_name': translate('area', lang),
                    'workspace_name': translate('workspace', lang),
                    'season_name': translate('season', lang),
                    'farm_name': translate('farm', lang),
                    'field_name': translate('field', lang),
                    'crop': translate('crop', lang),
                    'hybrid': translate('hybrid_varieties', lang),
                    'crop_date': translate('seeding_date', lang),  
                    'hectares': translate('hectares', lang),
                    'color_html': translate('colour', lang)
                    }  
                
                # Estilo CSS para ocupar todo el ancho de la pantalla
                st.markdown("""
                    <style>
                    .dataframe {
                        width: 100%;
                        table-layout: fixed;
                    }
                    .dataframe td, .dataframe th {
                        word-wrap: break-word;
                        text-align: center;
                        font-weight: normal;
                        font-size: 14px;  /* Ajusta el tamaño de la letra según sea necesario */
                    }
                    .dataframe th.index_name, .dataframe th.row_heading {
                        font-weight: normal;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                # Crear una función para mostrar el color como un cuadrado relleno
                def color_square_html(color):
                    return f'<div style="width:20px; height:20px; background-color:{color};"></div>'

                # Aplicar la función para generar la columna HTML
                df_lotes_seleccionados['color_html'] = df_lotes_seleccionados['color'].apply(color_square_html)

                # Renombrar las columnas en el DataFrame
                df_lotes_seleccionados.rename(columns=translations, inplace=True)   

                # Configurar Streamlit para mostrar el DataFrame con la columna de color HTML
                st.write(df_lotes_seleccionados.to_html(escape=False, columns=[
                    translations['area_name'], translations['workspace_name'], translations['season_name'],
                    translations['farm_name'], translations['field_name'], translations['crop'],
                    translations['hybrid'], translations['crop_date'], translations['hectares'], translations['color_html']
                ]), unsafe_allow_html=True)

                ##ORIGINAL
                # st.dataframe(df_lotes_seleccionados,
                #             column_config={
                #                 "area_id": None, #El valor None hace referencia a no mostrar la columna
                #                 "workspace_id": None,
                #                 "season_id": None,
                #                 "farm_id": None,
                #                 "field_id": None,
                #                 "geom": None,
                #                 "centroid": None,
                #                 "start_date": None,
                #                 "end_date": None,
                #                 "START_DATE": None,
                #                 "END_DATE": None,
                #                 "area_name": translate('area', lang), #Traducir a paritir del diccionario
                #                 "workspace_name": translate('workspace', lang),
                #                 "season_name": translate('season', lang),
                #                 "farm_name": translate('farm', lang),
                #                 "field_name": translate('field', lang),
                #                 "crop": translate('crop', lang),
                #                 "hybrid": translate('hybrid_varieties', lang),
                #                 "crop_date": translate('seeding_date', lang), #Revisar si crop date hace referencia a FS
                #                 "hectares": translate('hectares', lang)                        
                #             },
                #             width=100000) #Ancho del cuadro
                
                ############################################################################
                
                # MAPA
                st.divider()
                st.markdown('')
                st.markdown(f"<b>{translate('map_select_fields', lang)}</b>", unsafe_allow_html=True)

                # Centra el mapa en el centroide de las geometrías
                centroid_y_mean = gdf.geometry.centroid.y.mean()
                centroid_x_mean = gdf.geometry.centroid.x.mean()

                # Crea el mapa
                Map = geemap.Map(center=(centroid_y_mean, centroid_x_mean), zoom=14,plugin_Draw=False, search_control=False)

                # Convertir cualquier columna Timestamp a string
                timestamp_columns = ['crop_date', 'start_date', 'end_date', 'START_DATE', 'END_DATE']
                for col in timestamp_columns:
                    if col in gdf.columns:
                        gdf[col] = gdf[col].astype(str)
                        
                gdf.crs = "EPSG:4326"
                
                gdf.rename(columns={
                    'area_name': translate('area', lang),
                    'workspace_name': translate('workspace', lang),
                    'season_name': translate('season', lang),
                    'farm_name': translate('farm', lang),
                    'field_name': translate('field', lang),
                    'crop': translate('crop', lang),
                    'hybrid': translate('hybrid_varieties', lang),
                    'crop_date': translate('seeding_date', lang),  # Revisar si crop date hace referencia a FS
                    'hectares': translate('hectares', lang)
                }, inplace=True)

                # Columnas a excluir
                columns_to_exclude = [
                    'area_id', 'workspace_id', 'season_id', 'farm_id',
                    'field_id', 'geom', 'centroid', 'start_date', 'end_date','START_DATE','END_DATE'
                ]
                gdf.drop(columns=columns_to_exclude, inplace=True, errors='ignore')

                # Función para generar un color aleatorio en formato hex
                def random_color():
                    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

                # Crear un diccionario para los colores según 'farm_name'
                farm_names = gdf[translate('farm', lang)].unique()
                color_dict = {farm_name: random_color() for farm_name in farm_names}

                # Función para generar un color aleatorio en formato hex
                def random_color():
                    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

                # Crear un diccionario para los colores según 'field_name' usando color_map
                def get_field_color(field_name):
                    return color_map.get(field_name, random_color())['color']

                # Crear la función de estilo
                def style_function(feature):
                    field_name = feature['properties'][translate('field', lang)]
                    return {
                        'fillColor': get_field_color(field_name),
                        'color': 'black',
                        'weight': 1.5,
                        'fillOpacity': 0.6,
                    }
                
                # Añadir las geometrías al mapa
                
                Map.add_gdf(gdf, layer_name=translate("fields",lang), fields=[translate("field",lang)], style_function=style_function)

                Map.add_basemap("SATELLITE")

                Map.to_streamlit()

                ############################################################################
                
                st.divider()
                st.markdown('')
                ##################################################################################################
            
                ############################################################################
                
                # Mostrar la tabla con los datos finales NDVI interpolados

                st.markdown(f"<b>{translate('ndvi_results', lang)}</b>", unsafe_allow_html=True)
                st.markdown('')
                st.markdown('')

                
                ############################################################################
                
                #CUADRO NDVI POR FECHA Y LOTE

                st.write(translate('ndvi_date', lang))

                tab1, tab2 = st.tabs(["Crudo", "Savitzky–Golay "])

                with tab1:

                    #interpolated_df2=interpolated_df

                    # Formatear la columna de fecha para mostrar solo año, mes y día
                    interpolated_df_esa['Date'] = interpolated_df_esa['Date'].dt.strftime('%Y-%m-%d')

                    # Usar st.markdown para insertar CSS personalizado
                    st.markdown("""
                        <style>
                        .dataframe th, .dataframe td {
                            text-align: center !important;
                        }
                        </style>
                        """, unsafe_allow_html=True)            
                    
                    st.dataframe(interpolated_df_esa,                        
                                width=100000)
                
                with tab2:

                    #interpolated_df2=interpolated_df

                    # Formatear la columna de fecha para mostrar solo año, mes y día
                    interpolated_df_sg['Date'] = interpolated_df_sg['Date'].dt.strftime('%Y-%m-%d')

                    # Usar st.markdown para insertar CSS personalizado
                    st.markdown("""
                        <style>
                        .dataframe th, .dataframe td {
                            text-align: center !important;
                        }
                        </style>
                        """, unsafe_allow_html=True)            
                    
                    st.dataframe(interpolated_df_sg,                        
                                width=100000)
                
                # from streamlit_extras.dataframe_explorer import dataframe_explorer #DF que permite hacer filtrado

                # ndvi_df = dataframe_explorer(interpolated_df2, case=False)
                # st.dataframe(ndvi_df, use_container_width=True)
                
                ############################################################################

                #SERIE TEMPORAL NDVI

                st.markdown('')
                st.markdown('')
                st.write(translate('ndvi_serie', lang))

                tab1, tab2 = st.tabs(["Crudo", "Savitzky–Golay "])

                with tab1:

                    # Calcular la media de las columnas NDVI (suponiendo que las columnas NDVI son todas excepto la primera columna 'Date')
                    ndvi_columns = interpolated_df_esa.columns[1:]
                    color_map2 = {column: color_map[column]['color'] for column in ndvi_columns}
                    interpolated_df_esa['PROMEDIO'] = interpolated_df_esa[ndvi_columns].mean(axis=1)

                    # Crear un gráfico de líneas usando Plotly Express
                    fig = go.Figure()

                    # Añadir las líneas individuales para cada columna NDVI
                    for column in ndvi_columns:
                        fig.add_trace(
                            go.Scatter(
                                x=interpolated_df_esa['Date'],
                                y=interpolated_df_esa[column],
                                mode='lines',
                                name=column,
                                line=dict(color=color_map2[column], width=2),
                                showlegend=True  # Mostrar la leyenda para cada línea individual
                            )
                        )

                    # Añadir la curva promedio
                    fig.add_trace(
                        go.Scatter(
                            x=interpolated_df_esa['Date'], 
                            y=interpolated_df_esa['PROMEDIO'],
                            mode='lines',
                            name=translate('average', lang),
                            line=dict(color='firebrick', width=4, dash='dash'),
                            showlegend=True  # Mostrar la leyenda para la curva promedio
                        )
                    )

                    # Personalizar el diseño
                    fig.update_layout(
                        xaxis_title=translate('date2', lang),  # Cambiar el título del eje x si es necesario
                        yaxis_title='NDVI',  # Cambiar el título del eje y si es necesario
                        legend_title=translate('field', lang),  # Cambiar el título de la leyenda
                        width=1400,
                        autosize=False,
                    )

                    # Personalizar el tooltip
                    for column in ndvi_columns + ['PROMEDIO']:
                        fig.update_traces(
                            selector=dict(name=column),
                            hovertemplate=f'<b>Fecha:</b> %{{x}}<br><b>Lote:</b> {column}<br><b>NDVI:</b> %{{y}}'
                        )

                    st.plotly_chart(fig, use_container_width=True)

                    with tab2:

                        # Calcular la media de las columnas NDVI (suponiendo que las columnas NDVI son todas excepto la primera columna 'Date')
                        ndvi_columns = interpolated_df_sg.columns[1:]
                                                
                        interpolated_df_sg['PROMEDIO'] = interpolated_df_sg[ndvi_columns].mean(axis=1)

                        # Crear un gráfico de líneas usando Plotly Express
                        fig = go.Figure()

                        # Añadir las líneas individuales para cada columna NDVI
                        for column in ndvi_columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=interpolated_df_sg['Date'],
                                    y=interpolated_df_sg[column],
                                    mode='lines',
                                    name=column,
                                    line=dict(color=color_map2[column], width=2),
                                    showlegend=True  # Mostrar la leyenda para cada línea individual
                                )
                            )

                        # Añadir la curva promedio
                        fig.add_trace(
                            go.Scatter(
                                x=interpolated_df_sg['Date'], 
                                y=interpolated_df_sg['PROMEDIO'],
                                mode='lines',
                                name=translate('average', lang),
                                line=dict(color='firebrick', width=4, dash='dash'),
                                showlegend=True  # Mostrar la leyenda para la curva promedio
                            )
                        )

                        # Personalizar el diseño
                        fig.update_layout(
                            xaxis_title=translate('date2', lang),  # Cambiar el título del eje x si es necesario
                            yaxis_title='NDVI',  # Cambiar el título del eje y si es necesario
                            legend_title=translate('field', lang),  # Cambiar el título de la leyenda
                            width=1400,
                            autosize=False,
                        )

                        # Personalizar el tooltip
                        for column in ndvi_columns + ['PROMEDIO']:
                            fig.update_traces(
                                selector=dict(name=column),
                                hovertemplate=f'<b>Fecha:</b> %{{x}}<br><b>Lote:</b> {column}<br><b>NDVI:</b> %{{y}}'
                            )

                        st.plotly_chart(fig, use_container_width=True)
    
                ############################################################################

                # Asignar el DataFrame según la opción seleccionada
                if selected_option == translate('cleaning_option',lang):
                    interpolated_df = interpolated_df_sg
                else:
                    interpolated_df = interpolated_df_esa

                interpolated_df.drop('PROMEDIO', axis=1, inplace=True)

                #HEATMAP

                st.markdown('')
                st.markdown('')
                st.write(translate('ndvi_heatmap', lang))

                # Definir la paleta de colores personalizada basada en la imagen proporcionada
                custom_colorscale = [
                    [0.0, 'rgb(0, 0, 0)'],         # Negro
                    [0.05, 'rgb(160, 82, 45)'],    # A0522D - Marrón
                    [0.1, 'rgb(148, 114, 60)'],    # 94723C - Marrón claro
                    [0.15, 'rgb(164, 130, 76)'],   # a4824c - Marrón claro
                    [0.2, 'rgb(180, 150, 108)'],   # b4966c - Beige
                    [0.25, 'rgb(196, 186, 164)'],  # c4baa4 - Beige claro
                    [0.3, 'rgb(148, 182, 20)'],    # 94b614 - Verde claro
                    [0.35, 'rgb(128, 170, 17)'],   # 80aa11 - Verde
                    [0.4, 'rgb(108, 159, 14)'],    # 6c9f0e - Verde
                    [0.45, 'rgb(88, 147, 12)'],    # 58930c - Verde
                    [0.5, 'rgb(68, 136, 9)'],      # 448809 - Verde
                    [0.55, 'rgb(48, 125, 6)'],     # 307d06 - Verde
                    [0.6, 'rgb(28, 114, 4)'],      # 1c7204 - Verde
                    [0.65, 'rgb(70, 123, 45)'],    # 467b2d - Verde
                    [0.7, 'rgb(56, 132, 87)'],     # 388457 - Verde
                    [0.75, 'rgb(42, 142, 129)'],   # 2a8e81 - Verde azulado
                    [0.8, 'rgb(28, 151, 171)'],    # 1c97ab - Azul claro
                    [0.85, 'rgb(14, 160, 213)'],   # 0ea0d5 - Azul claro
                    [0.9, 'rgb(0, 170, 255)'],     # 00aaff - Azul
                    [0.95, 'rgb(21, 127, 223)'],   # 157fdf - Azul medio
                    [1.0, 'rgb(51, 67, 178)'],     # 3343b2 - Azul oscuro
                ]

                # Obtener los valores de las columnas de lotes (excluyendo la columna 'Date')
                lotes_values = interpolated_df.drop(columns='Date').values

                # Obtener las fechas
                fechas = interpolated_df['Date'].values

                # Crear una matriz z con ceros, con filas para cada lote y columnas para cada fecha
                z = np.zeros((len(lotes_values), len(fechas)))

                # Llenar la matriz z con los valores interpolados
                for i, lotes_value in enumerate(lotes_values.T):
                    z[i, :] = lotes_value

                # Crear el heatmap
                fig = go.Figure(data=go.Heatmap(
                    z=z,
                    x=fechas,
                    y=interpolated_df.columns[1:],  # Columnas de lotes
                    colorscale=custom_colorscale ))

                # Personalizar el diseño
                fig.update_layout(                
                    xaxis_title= translate("date2", lang),
                    yaxis_title= translate("field", lang),
                    autosize = True,
                    height=650)
                
                fig.update_traces(
                    hovertemplate=f'<b>{translate("date2", lang)}:</b> %{{x}}<br><b>{translate("field", lang)}:</b> {column}<br><b>NDVI:</b> %{{z}}<extra></extra>' #Traducir variables del cuadro interactivo
                    )

                # Mostrar el heatmap
                st.plotly_chart(fig, use_container_width=True)

                ############################################################################

                #BOXPLOT

                st.markdown('')
                st.markdown('')
                st.write(translate('ndvi_boxplot', lang))
                
                # Crear el boxplot horizontal
                fig = go.Figure()

                # Iterar sobre las columnas de 'interpolated_df' excepto la columna 'Date'
                for i, column in enumerate(ndvi_columns):
                    fig.add_trace(go.Box(
                        y=interpolated_df[column],
                        name=column,
                        marker_color=color_map2[column],  # Asignar color según el color_map
                        width=0.4  # Ajustar el ancho de las cajas según tu preferencia
                        )
                    )

                # Ajustar el layout del gráfico
                fig.update_layout(
                    yaxis_title="NDVI",
                    xaxis_title=translate("field", lang),
                    boxmode='group',
                    autosize=True,
                )

                fig.update_xaxes(tickangle=-45)

                st.plotly_chart(fig, use_container_width=True)

                ############################################################################
                #Ranking
                ############################################################################

                st.divider()
                st.markdown('')
                
                interpolated_df['Date'] = pd.to_datetime(interpolated_df['Date'])
                pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

                # Calcular la integral de la serie temporal NDVI para cada lote usando las fechas directamente
                integrals = {}
                for column in interpolated_df.columns:
                    if column not in ['Date']:
                        # Convertir las fechas a un formato numérico relativo para la integración
                        dates_numeric = (interpolated_df['Date'] - interpolated_df['Date'].min()).dt.days
                        integrals[column] = trapz(interpolated_df[column], dates_numeric)

                # Calcular la media y el desvío estándar para cada lote
                means = pivot_df.drop(columns=['Date']).mean()
                std_devs = pivot_df.drop(columns=['Date']).std()

                # Calcular el Coeficiente de Variación (CV) en porcentaje
                cvs = (std_devs / means) * 100

                # Asegurarse de que todos los lotes están presentes en ambas listas
                all_lots = set(integrals.keys()).union(set(std_devs.index))
                integral_values = [integrals.get(lot, np.nan) for lot in all_lots]
                std_dev_values = [std_devs.get(lot, np.nan) for lot in all_lots]
                cv_values = [cvs.get(lot, np.nan) for lot in all_lots]

                # Crear DataFrame para los rankings
                ranking_df = pd.DataFrame({
                    'Lote': list(all_lots),
                    'Integral_NDVI': integral_values,
                    'Desvio_Estandar': std_dev_values,
                    'CV_%': cv_values
                })

                # Ordenar por Integral de NDVI
                ranking_integral = ranking_df.sort_values(by='Integral_NDVI', ascending=False).reset_index(drop=True)
                # Ordenar por Desvío Estándar
                ranking_desvio = ranking_df.sort_values(by='Desvio_Estandar', ascending=False).reset_index(drop=True)
                # Ordenar por Coeficiente de Variación
                ranking_cv = ranking_df.sort_values(by='CV_%', ascending=False).reset_index(drop=True)

                
                ############################################################################

                #GRAFICOS DE RANKING

                # Verificar si 'DateNum' está presente como el primer elemento en la lista de lotes
                
                # Obtener el índice de la fila que contiene "DateNum"
                index_date_num = ranking_integral.index[-1]

                # Verificar si 'DateNum' está presente en la última posición del índice del DataFrame ranking_integral
                if ranking_integral['Lote'].iloc[index_date_num] == 'DateNum':
                    ranking_integral = ranking_integral.drop(index=index_date_num)

                if ranking_desvio['Lote'].iloc[0] == 'DateNum':
                    ranking_desvio = ranking_desvio.iloc[1:]

                if 'DateNum' in ranking_cv['Lote'].values:
                    ranking_cv = ranking_cv[ranking_cv['Lote'] != 'DateNum']

                ranking_df2 = ranking_df

                if ranking_df2['Lote'].iloc[index_date_num] == 'DateNum':
                        ranking_df2 = ranking_df.drop(index=index_date_num)

                # Obtener los nombres de los lotes según el orden del diccionario
                ordered_lotes = list(color_map.keys())

                # Convertir la columna 'Lote' en una categoría con el orden deseado
                ranking_df2['Lote'] = pd.Categorical(ranking_df2['Lote'], categories=ordered_lotes, ordered=True)

                # Ordenar el DataFrame por la columna 'Lote'
                ranking_df2 = ranking_df2.sort_values(by='Lote').reset_index(drop=True)

                lotes = ranking_df2['Lote'].unique()

                ############################################################################
                #GRAFICA DE INTEGRAL

                st.markdown(translate('ndvi_integral_rank', lang))

                
                tab1, tab2 = st.tabs(["Ranking", translate("field",lang)])

                with tab1:

                    st.markdown('')
                    st.markdown('')
                    st.markdown('')

                # Graficar los rankings con plotly.express

                    fig_integral = px.bar(ranking_integral, x='Lote', y='Integral_NDVI')
                    fig_integral.update_xaxes(title_text= translate('field', lang), tickangle=-45)  # Actualizar el título del eje x
                    fig_integral.update_yaxes(title_text= translate('ndvi_integral', lang))

                    
                    fig_integral.update_traces(
                        marker_color='#4C78A8',
                        hovertemplate=f'<b>{translate("field", lang)}:</b> %{{x}}<br><b>{translate("ndvi_integral", lang)}:</b> %{{y}}<extra></extra>' #Traducir variables del cuadro interactivo
                        )

                    st.plotly_chart(fig_integral, use_container_width=True)

                with tab2:
                    
                    fig_integral2 = create_bar_chart(ranking_df2, 'Integral_NDVI', lotes, color_map2)  # En función del Color_map

                    fig_integral2.update_xaxes(title_text= translate('field', lang), tickangle=-45)  # Actualizar el título del eje x
                    fig_integral2.update_yaxes(title_text= translate('ndvi_integral', lang))

                    fig_integral2.update_traces(
                        hovertemplate=f'<b>{translate("field", lang)}:</b> %{{x}}<br><b>{translate("ndvi_integral", lang)}:</b> %{{y}}<extra></extra>'  # Traducir variables del cuadro interactivo
                    )
                    
                    # Ajustar la altura del gráfico
                    # fig_integral2.update_layout(height=500) 

                    st.plotly_chart(fig_integral2, use_container_width=True)
                ############################################################################
                #GRAFICA SD

                st.write(translate('ndvi_sd_rank', lang))

                tab1, tab2 = st.tabs(["Ranking", translate("field",lang)])

                with tab1:

                    st.markdown('')
                    st.markdown('')
                    st.markdown('')

                # Graficar los rankings con plotly.express

                    fig_desvio = px.bar(ranking_desvio, x='Lote', y='Desvio_Estandar')
                    fig_desvio.update_xaxes(title_text= translate('field', lang), tickangle=-45)  # Actualizar el título del eje x
                    fig_desvio.update_yaxes(title_text= translate('ndvi_sd', lang))

                    
                    fig_desvio.update_traces(
                        marker_color='#4C78A8',
                        hovertemplate=f'<b>{translate("field", lang)}:</b> %{{x}}<br><b>{translate("ndvi_sd", lang)}:</b> %{{y}}<extra></extra>' #Traducir variables del cuadro interactivo
                        )

                    st.plotly_chart(fig_desvio, use_container_width=True)

                with tab2:
                    
                    fig_desvio2 = create_bar_chart(ranking_df2, 'Desvio_Estandar', lotes, color_map2) #En funcion del Color_map

                    fig_desvio2.update_xaxes(title_text= translate('field', lang), tickangle=-45)  # Actualizar el título del eje x
                    fig_desvio2.update_yaxes(title_text= translate('ndvi_sd', lang))

                    fig_desvio2.update_traces(
                        hovertemplate=f'<b>{translate("field", lang)}:</b> %{{x}}<br><b>{translate("ndvi_sd", lang)}:</b> %{{y}}<extra></extra>' #Traducir variables del cuadro interactivo
                        )
                    
                    # Ajustar la altura del gráfico
                    fig_desvio2.update_layout(height=500) 

                    st.plotly_chart(fig_desvio2, use_container_width=True)

                ############################################################################
                #GRAFICA SD Y CV
                
                # Crear la figura
                fig = go.Figure()

                # Añadir las barras del Desvío Estándar
                fig.add_trace(go.Bar(
                    x=ranking_desvio['Lote'],
                    y=ranking_desvio['Desvio_Estandar'],
                    name=translate('field', lang),
                    marker=dict(color='#4C78A8'),
                    yaxis='y1'
                ))

                # Añadir los puntos del Coeficiente de Variación
                fig.add_trace(go.Scatter(
                    x=ranking_cv['Lote'],
                    y=ranking_cv['CV_%'],
                    name=translate('cv', lang),
                    mode='markers',
                    marker=dict(color='#E45756', size=10),
                    yaxis='y2'
                ))

                # Actualizar las configuraciones del layout para incluir dos ejes Y
                fig.update_layout(
                    title=translate('cv_rank', lang),
                    xaxis=dict(
                        title=translate('field', lang),
                        tickfont_size=14,
                        tickangle=-45
                    ),
                    yaxis=dict(
                        title=translate('ndvi_sd', lang),
                        titlefont_size=16,
                        tickfont_size=14,
                        side='left',
                        range=[0, 1],  # Ajustar el rango del eje y1
                        showgrid=True
                    ),
                    yaxis2=dict(
                        title=translate('cv', lang),
                        titlefont_size=16,
                        tickfont_size=14,
                        side='right',
                        overlaying='y',
                        range=[0, 100],  # Ajustar el rango del eje y2
                        showgrid=False
                    ),
                    legend=dict(
                        x=0,
                        y=1.1,
                        bgcolor='rgba(255, 255, 255, 0)',
                        bordercolor='rgba(255, 255, 255, 0)'
                    ),
                    barmode='group',  # Agrupar las barras una al lado de la otra
                    bargap=0.15,      # Espacio entre barras de diferentes categorías
                    bargroupgap=0.1   # Espacio entre barras de la misma categoría
                )

                # Configurar hovertemplate para todas las trazas
                fig.update_traces(
                    hovertemplate=f'<b>{translate("field", lang)}:</b>%{x}<b>{translate("cv", lang)}:</b>%{y}<extra></extra>'
                )

                

                # Mostrar el gráfico en Streamlit
                st.plotly_chart(fig, use_container_width=True)
                
                
        ############################################################################
        
        st.divider()
        st.markdown('')

        ############################################################################
        st.caption("Powered by GeoAgro")

if __name__ == "__main__":
    redirect_uri=" http://localhost:8501"
    # user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'test', 'domainId': 1, 'areaId': 1, 'workspaceId': 882, 'seasonId': 172, 'farmId': 2016} # TEST / GeoAgro / GeoAgro / TEST_BONELLI / 2021-22 / Lacau SA - Antares
    user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'prod', 'domainId': 1, 'areaId': 1, 'workspaceId': 65, 'seasonId': 3486, 'farmId': 11143} 
    st.session_state['user_info'] = user_info
    main_app(user_info)


# if __name__ == "__main__":
#     redirect_uri = "https://dashboards.geoagro.com/"
#     user_info = None

#     try:
#         # Intentar obtener user_info de los tokens
#         token1 = st.query_params['token1']
#         token2 = st.query_params['token2']
#         user_info = decrypt_token(token1)  # Asumiendo que esta función existe y decodifica el token
#         st.session_state['user_info'] = user_info  # Guardar user_info en session_state
#     except Exception as e:
#         print(e)

#     if user_info is None:
#         # Intentar recuperar user_info de session_state si los tokens fallan
#         user_info = st.session_state.get('user_info')
#         print(user_info)

#         if user_info is None:
#             googleoauth_secrets = json.loads(AWSSecret().get_secret(secret_name="prod/streamlit-google-oauth", region_name="us-west-2"))
#             client_id = googleoauth_secrets['client_id']
#             client_secret = googleoauth_secrets['client_secret']

#             # Si user_info aún no está disponible, proceder con el flujo de login y usar la función domains_areas_by_user
#             login_info = oauth.login(
#                 client_id=client_id,
#                 client_secret=client_secret,
#                 redirect_uri=redirect_uri,
#             )
#             print('login_info: ', login_info)
            
#             if login_info:
#                 user_id, user_email = login_info
#                 user_info = {
#                     'email': user_email, 'language': 'es', 'env': 'test', 'domainId': None,
#                     'areaId': None, 'workspaceId': None, 'seasonId': None, 'farmId': None
#                 }

#                 secrets = json.loads(AWSSecret().get_secret(secret_name="test/apigraphql360", region_name="us-west-2"))
                
#                 access_key_id = secrets['x-api-key']
#                 url = secrets['url']

#                 # Usar la función domains_areas_by_user para obtener el domainID
#                 domains = domains_areas_by_user(user_email, access_key_id, url)
                
#                 if domains:
#                     user_info['domainId'] = domains[0]['id']  # Actualizar user_info con el primer domainID
#                     print('domain ID: ', user_info['domainId'])
#                     st.session_state['user_info'] = user_info  # Actualizar session_state
#                     print('user_info: ', user_info)
#             else:
#                 logging.error("Not logged")

#     if user_info:
#         main_app(user_info)  # Llamar a la función principal de la aplicación con user_info
#     else:
#         st.error("Error accessing Dashboards. Please contact an administrator.")