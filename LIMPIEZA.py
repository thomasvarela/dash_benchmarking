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

                pivot_esa = pivot_df #ESA
                pivot_sg=pivot_df #SG
                pivot_knn=pivot_df #KNN
                pivot_mv=pivot_df #MEDIA MOVIL
                datos_crudos=pivot_df.copy() #DF CRUDO SIN INTERPOLAR

                # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                datos_crudos = datos_crudos[(datos_crudos['Date'] >= start_date) & (datos_crudos['Date'] <= end_date)]
                
                                

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

                
                # Crear una copia del DataFrame original para asegurarse de que los valores originales no se modifiquen
                #interpolated_df_esa = pivot_esa.copy()

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
                # Aplicar filtro de Savitzky-Golay para cada columna
                # Configuración del filtro de Savitzky-Golay
                window_size = 15  # Asegurarse de que el tamaño de la ventana sea un número impar
                poly_order = 3 # Orden del polinomio

                #Aplicar filtro de Savitzky-Golay para cada columna numérica
                for column in pivot_sg.columns:
                    if column not in ['Date']:
                        # Aplicar el filtro de Savitzky-Golay
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

                # Interpolar valores faltantes para cada columna numérica usando RBFInterpolator
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

                # Filtrar interpolated_df_sg para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                interpolated_df_sg = interpolated_df_sg[(interpolated_df_sg['Date'] >= start_date) & (interpolated_df_sg['Date'] <= end_date)]

                # Eliminar la columna 'DateNum' del DataFrame interpolado
                #interpolated_df_sg.drop(columns=['DateNum'], inplace=True)

                # Reiniciar índice y ajustar si es necesario
                interpolated_df_sg.reset_index(drop=True, inplace=True)

                # #######################################################################
                # #KNN

                # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
                min_date = pivot_knn['Date'].min()
                max_date = pivot_knn['Date'].max()
                all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

                # Convertir fechas a un formato numérico (número de días desde la primera fecha)
                pivot_knn['DateNum'] = (pivot_knn['Date'] - min_date) / np.timedelta64(1, 'D')
                date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

                # Imputación de datos faltantes usando la media
                imputer = SimpleImputer(strategy='mean')

                for column in pivot_knn.columns:
                    if column not in ['Date', 'DateNum']:
                        # Imputar valores faltantes con la media
                        pivot_knn[[column]] = imputer.fit_transform(pivot_knn[[column]])

                # Limpieza de datos utilizando KNN para cada lote
                lof = LocalOutlierFactor(n_neighbors=6, contamination=0.1)

                for column in pivot_knn.columns:
                    if column not in ['Date', 'DateNum']:
                        # Filtrar valores nulos y preparar datos para la interpolación
                        x = pivot_knn['DateNum'].values.reshape(-1, 1)
                        y = pivot_knn[column].values

                        if x.size == 0 or y.size == 0:
                            print(f"No hay datos suficientes para procesar en la columna: {column}")
                            continue

                        # Detectar outliers
                        outliers = lof.fit_predict(x)
                        # Reemplazar outliers por NaN en el DataFrame original
                        pivot_knn.loc[outliers == -1, column] = np.nan

                # Preparar un nuevo DataFrame para almacenar resultados interpolados
                interpolated_df_knn = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

                # Interpolar valores faltantes para cada columna numérica usando RBFInterpolator
                for column in pivot_knn.columns:
                    if column not in ['Date', 'DateNum']:
                        # Filtrar valores nulos y preparar datos para la interpolación
                        x = pivot_knn.loc[pivot_knn[column].notna(), 'DateNum']
                        y = pivot_knn.loc[pivot_knn[column].notna(), column]

                        if x.empty or y.empty:
                            print(f"No hay datos para interpolar en la columna: {column}")
                            continue

                        # Crear el interpolador RBF
                        rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

                        # Interpolar valores para todas las fechas en interpolated_df
                        y_interp = rbf(date_num_all.values[:, None])

                        # Almacenar resultados interpolados en el DataFrame
                        interpolated_df_knn[column] = y_interp

                # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                interpolated_df_knn = interpolated_df_knn[(interpolated_df_knn['Date'] >= start_date) & (interpolated_df_knn['Date'] <= end_date)]

                #if 'DateNum' in interpolated_df_knn.columns:
                    #interpolated_df_knn.drop(columns=['DateNum'], inplace=True)
                #else:
                    #print("La columna 'DateNum' no existe en el DataFrame interpolated_df_knn.")
                
                interpolated_df_knn.reset_index(drop=True, inplace=True)
                interpolated_df_knn.index += 1

                ########################################################################
                
                #SUAVIZADO CADA 15 DIAS - ESTE ESTABA FUNCIONANDO

                # Convertir la columna 'Date' a datetime
                pivot_mv['Date'] = pd.to_datetime(pivot_mv['Date'])

                # Aplicar suavizado por media móvil para cada columna
                window_size = 20 # Puedes ajustar el tamaño de la ventana según tus necesidades

                for column in pivot_mv.columns:
                    if column not in ['Date']:
                        pivot_mv[column] = pivot_mv[column].rolling(window=window_size, min_periods=1, center=True).mean()
                
                # Crear un rango completo de fechas desde el mínimo hasta el máximo extendido
                min_date = pivot_mv['Date'].min()
                max_date = pivot_mv['Date'].max()
                all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

                # Convertir fechas a un formato numérico (número de días desde la primera fecha)
                pivot_df['DateNum'] = (pivot_mv['Date'] - min_date) / np.timedelta64(1, 'D')
                date_num_all = (all_dates - min_date) / np.timedelta64(1, 'D')

                # Preparar un nuevo DataFrame para almacenar resultados interpolados
                interpolated_df_mv = pd.DataFrame({'Date': all_dates, 'DateNum': date_num_all})

                # Interpolar valores faltantes para cada columna numérica usando RBFInterpolator
                for column in pivot_mv.columns:
                    if column not in ['Date', 'DateNum']:
                        # Filtrar valores nulos y preparar datos para la interpolación
                        x = pivot_mv.loc[pivot_mv[column].notna(), 'DateNum']
                        y = pivot_mv.loc[pivot_mv[column].notna(), column]

                        if x.empty or y.empty:
                            print(f"No hay datos para interpolar en la columna: {column}")
                            continue

                        # Crear el interpolador RBF
                        rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

                        # Interpolar valores para todas las fechas en interpolated_df
                        y_interp = rbf(date_num_all.values[:, None])

                        # Almacenar resultados interpolados en el DataFrame
                        interpolated_df_mv[column] = y_interp


                # Filtrar interpolated_df para que solo incluya datos dentro del intervalo START_DATE y END_DATE
                start_date = filtered_df['START_DATE'].min()
                end_date = filtered_df['END_DATE'].max()
                interpolated_df_mv = interpolated_df_mv[(interpolated_df_mv['Date'] >= start_date) & (interpolated_df_mv['Date'] <= end_date)]

                # Eliminar la columna 'DateNum' del DataFrame interpolado
                interpolated_df_mv.drop(columns=['DateNum'], inplace=True)

                interpolated_df_mv.reset_index(drop=True, inplace=True)
                interpolated_df_mv.index += 1


                ############################################################################

                datos_crudos['limpieza'] = 'ESA'
                interpolated_df_esa['limpieza'] = 'ESA+INT'
                interpolated_df_sg['limpieza'] = 'SG'
                interpolated_df_knn['limpieza'] = 'KNN'
                interpolated_df_mv['limpieza'] = 'MV'

                # Lista de DataFrames que quieres unir
                dataframes = [datos_crudos, interpolated_df_esa, interpolated_df_sg,interpolated_df_knn,interpolated_df_mv]

                # Lista de DataFrames que quieres unir
                #dataframes = [datos_crudos, interpolated_df_mv]


                # Concatenar todos los DataFrames en uno solo
                combined_df = pd.concat(dataframes, ignore_index=True)

                combined_df.reset_index(drop=True, inplace=True)
                combined_df.index += 1

                ############################################################################
                #VISUALIZACIONES
                ############################################################################

                ############################################################################
                # TABLA RESUMEN LOTES
                
                # Eliminar la columna 'DateNum'
                if 'DateNum' in combined_df.columns:
                    combined_df = combined_df.drop(columns=['DateNum'])

                # Mostrar el DataFrame combinado usando Streamlit
                st.dataframe(combined_df)

                # Pivotar el DataFrame
                pivoted_df = combined_df.pivot_table(index='Date', columns='limpieza')

                st.dataframe(pivoted_df)

                
                ############################################################################
                
                # Mostrar la tabla con los datos finales NDVI interpolados

                st.markdown(f"<b>{translate('ndvi_results', lang)}</b>", unsafe_allow_html=True)
                st.markdown('')
                st.markdown('')

                
                ############################################################################
                
                #CUADRO NDVI POR FECHA Y LOTE

                # st.write(translate('ndvi_date', lang))

                # tab1, tab2 = st.tabs(["Crudo", "Savitzky–Golay "])

                # with tab1:

                #     #interpolated_df2=interpolated_df

                #     # Formatear la columna de fecha para mostrar solo año, mes y día
                #     interpolated_df_esa['Date'] = interpolated_df_esa['Date'].dt.strftime('%Y-%m-%d')

                #     # Usar st.markdown para insertar CSS personalizado
                #     st.markdown("""
                #         <style>
                #         .dataframe th, .dataframe td {
                #             text-align: center !important;
                #         }
                #         </style>
                #         """, unsafe_allow_html=True)            
                    
                #     st.dataframe(interpolated_df_esa,                        
                #                 width=100000)
                
                # with tab2:

                #     #interpolated_df2=interpolated_df

                #     # Formatear la columna de fecha para mostrar solo año, mes y día
                #     interpolated_df_sg['Date'] = interpolated_df_sg['Date'].dt.strftime('%Y-%m-%d')

                #     # Usar st.markdown para insertar CSS personalizado
                #     st.markdown("""
                #         <style>
                #         .dataframe th, .dataframe td {
                #             text-align: center !important;
                #         }
                #         </style>
                #         """, unsafe_allow_html=True)            
                    
                #     st.dataframe(interpolated_df_sg,                        
                #                 width=100000)
                
                # from streamlit_extras.dataframe_explorer import dataframe_explorer #DF que permite hacer filtrado

                # ndvi_df = dataframe_explorer(interpolated_df2, case=False)
                # st.dataframe(ndvi_df, use_container_width=True)
                
                ############################################################################

                #SERIE TEMPORAL NDVI

                st.markdown('')
                st.markdown('')
                st.write(translate('ndvi_serie', lang))

                # Calcular la media de las columnas NDVI (suponiendo que las columnas NDVI son todas excepto la primera columna 'Date')
                ndvi_columns = combined_df.columns[1:-1]  # Excluir la columna 'Date' y 'limpieza'
                
                # Crear un gráfico de líneas usando Plotly Express
                fig = go.Figure()

                # Añadir las líneas individuales para cada método de limpieza
                for method in combined_df['limpieza'].unique():
                    method_df = combined_df[combined_df['limpieza'] == method]
                    for column in ndvi_columns:
                        fig.add_trace(
                            go.Scatter(
                                x=method_df['Date'],
                                y=method_df[column],
                                mode='lines',
                                name=f'{column} ({method})',
                                line=dict(width=2),
                                showlegend=True
                            )
                        )

                # Personalizar el diseño
                fig.update_layout(
                    xaxis_title='Fecha',
                    yaxis_title='NDVI',
                    legend_title='Campo',
                    width=1400,
                    autosize=False,
                )

                
                # Mostrar el gráfico en Streamlit
                st.plotly_chart(fig, use_container_width=True)

                

                ############################################################################
                
                from sklearn.metrics import mean_squared_error, mean_absolute_error
                from scipy.stats import pearsonr

                def calculate_metrics(original_values, compared_values):
                    # Error Cuadrático Medio (MSE)
                    mse = mean_squared_error(original_values, compared_values)
                    
                    # Coeficiente de Correlación de Pearson
                    pearson_corr, _ = pearsonr(original_values, compared_values)
                    
                    # Error Absoluto Medio (MAE)
                    mae = mean_absolute_error(original_values, compared_values)
                    
                    # Índice de Concordancia de Lin (LC)
                    mu_x = np.mean(original_values)
                    mu_y = np.mean(compared_values)
                    sigma_x = np.std(original_values)
                    sigma_y = np.std(compared_values)
                    lc = (2 * pearson_corr * sigma_x * sigma_y) / (sigma_x**2 + sigma_y**2 + (mu_x - mu_y)**2)
                    
                    return mse, pearson_corr, mae, lc

                esa_values = interpolated_df_esa.iloc[:, 1].values
                sg_values = interpolated_df_sg.iloc[:, 1].values
                knn_values = interpolated_df_knn.iloc[:, 1].values
                mv_values = interpolated_df_mv.iloc[:, 1].values

                metrics = {
                    "SG": calculate_metrics(esa_values, sg_values),
                    "KNN": calculate_metrics(esa_values, knn_values),
                    "MV": calculate_metrics(esa_values, mv_values)
                }

                # Convertimos a un DataFrame para visualizar mejor
                metrics_df = pd.DataFrame(metrics, index=["MSE", "Pearson Correlation", "MAE", "Lin's Concordance"]).T
                st.dataframe(metrics_df)

if __name__ == "__main__":
    redirect_uri=" http://localhost:8501"
    #user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'test', 'domainId': 1, 'areaId': 1, 'workspaceId': 882, 'seasonId': 172, 'farmId': 2016} # TEST / GeoAgro / GeoAgro / TEST_BONELLI / 2021-22 / Lacau SA - Antares
    user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'prod', 'domainId': 1, 'areaId': 1, 'workspaceId': 65, 'seasonId': 3486, 'farmId': 11143} 
    st.session_state['user_info'] = user_info
    main_app(user_info)
