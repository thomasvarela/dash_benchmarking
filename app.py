# Bibliotecas estándar de Python
import json

# Manipulación de datos y geometrías
import pandas as pd
import geopandas as gpd
import numpy as np

# Manejo de imágenes
from PIL import Image

# Integración web y aplicaciones interactivas
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.mandatory_date_range import date_range_picker
import streamlit_google_oauth as oauth
from streamlit_vertical_slider import vertical_slider
import plotly.graph_objects as go
import plotly.express as px

# Manejo de geometrías
from shapely.geometry import shape, mapping, Point

# Earth Engine y mapeo avanzado
import ee
import geemap.foliumap as geemap

# Interpolación y análisis espacial
from scipy.interpolate import RBFInterpolator

# Importar módulos o paquetes locales
from helper import translate, api_call_logo, api_call_fields_table, domains_areas_by_user
from secretManager import AWSSecret
import logging

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
            # Selector de color
            ############################################################################
            st.markdown('')
            st.markdown('')


            # Obtener la lista de rampas de colores cualitativos
            # color_ramps = dir(px.colors.qualitative)
            # Filtrar los elementos que no son rampas de colores
            # color_ramps = [ramp for ramp in color_ramps if not ramp.startswith("__")]
            # Encontrar el índice de 'T10' en la lista de rampas de colores
            # default_index = color_ramps.index('T10') if 'T10' in color_ramps else 0

            # Selector para la rampa de colores con un valor predeterminado
            # selected_color_ramp = st.selectbox(translate("color_palette", lang), color_ramps, index=default_index)

            # Usa getattr para obtener la rampa de colores seleccionada
            # selected_colors = getattr(px.colors.qualitative, selected_color_ramp)

            #selected_colors = px.colors.qualitative.T10
            
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
                    cultivos,
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
                
            # # Filtra el DataFrame basado en las áreas seleccionadas
            # filtered_df = filtered_df[filtered_df['hybrid'].isin(selector_hibrido)]

            # filtered_df.reset_index(drop=True, inplace=True)
            # filtered_df.index += 1

            # filtered_df.to_csv('filtered_df.csv', index=False)
            
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
            ###########################################################################
            #Fecha
            ###########################################################################
            
            # Asegúrate de que start y end date está en formato datetime
            filtered_df['start_date'] = pd.to_datetime(filtered_df['start_date'], errors='coerce')
            filtered_df['end_date'] = pd.to_datetime(filtered_df['end_date'], errors='coerce')

            # Determinar el rango de fechas disponible
            min_date = filtered_df['start_date'].min()
            max_date = filtered_df['end_date'].max()

                        
            # Muestra el selector de rango de fechas
            
            selected_date_range = date_range_picker(translate("select_date_range", lang),
                                                    default_start=min_date.date() if min_date else None,
                                                    default_end=max_date.date() if max_date else None, 
                                                    min_date=min_date.date() if min_date else None, 
                                                    max_date=max_date.date() if max_date else None,
                                                    error_message=translate("error_message_date_picker", lang) 
                                                    )
            
           # Asignar las fechas seleccionadas a todas las filas de las columnas START_DATE y END_DATE
            filtered_df = filtered_df.assign(
                START_DATE=selected_date_range[0],
                END_DATE=selected_date_range[1]
            )
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
        st.divider()  # 👈 Draws a horizontal rule
        st.markdown('')
        st.markdown(f"<b>{translate('select_fields', lang)}</b>", unsafe_allow_html=True)

        ############################################################################
        # TABLA RESUMEN LOTES
        ############################################################################

        st.dataframe(filtered_df,
                     column_config={
                        "area_id": None, #El valor None hace referencia a no mostrar la columna
                        "workspace_id": None,
                        "season_id": None,
                        "farm_id": None,
                        "field_id": None,
                        "geom": None,
                        "centroid": None,
                        "start_date": None,
                        "end_date": None,
                        "START_DATE": None,
                        "END_DATE": None,
                        "area_name": translate('area', lang), #Traducir a paritir del diccionario
                        "workspace_name": translate('workspace', lang),
                        "season_name": translate('season', lang),
                        "farm_name": translate('farm', lang),
                        "field_name": translate('field', lang),
                        "crop": translate('crop', lang),
                        "hybrid": translate('hybrid_varieties', lang),
                        "crop_date": translate('seeding_date', lang), #Revisar si crop date hace referencia a FS
                        "hectares": translate('hectares', lang)                        
                    },
                    width=100000) #Ancho del cuadro
                    

        ############################################################################
        
        st.divider()
        st.markdown('')
        st.markdown(f"<b>{translate('map_select_fields', lang)}</b>", unsafe_allow_html=True)

        ############################################################################
        # MAPA
        ############################################################################
        from shapely import wkt
        import random

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

        # Centra el mapa en el centroide de las geometrías
        centroid_y_mean = gdf.geometry.centroid.y.mean()
        centroid_x_mean = gdf.geometry.centroid.x.mean()

        # Crea el mapa
        Map = geemap.Map(center=(centroid_y_mean, centroid_x_mean),zoom=14)
        
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

        # Crear la función de estilo
        def style_function(feature):
            farm_name = feature['properties'][translate('farm', lang)]
            return {
                'fillColor': color_dict[farm_name],
                'color': 'black',
                'weight': 1.5,
                'fillOpacity': 0.6,
            }
        
        # Añadir las geometrías al mapa
        Map.add_gdf(gdf, layer_name=translate("fields", lang), style_function=style_function)
        
        Map.add_basemap("SATELLITE")

        Map.to_streamlit()

        ############################################################################
        
        st.divider()
        st.markdown('')
        
        ############################################################################
        # NDVI
        ############################################################################

        from ndvi import extract_mean_ndvi_date
        
        # DataFrame final que almacenará los resultados
        final_df = pd.DataFrame()

        # for index, row in filtered_df.iterrows():
        #     # Extraer la geometría individual
        #     lote_gdf_filtrado = filtered_df.iloc[[index]]
            
        #     # Llamar a la función con la geometría actual
        #     df_temp = extract_mean_ndvi_date(lote_gdf_filtrado,START_DATE,END_DATE)
            
        #     # Obtener el nombre de la geometría
        #     geom_name = row[]
            
        #     # Agregar el nombre de la geometría como columna
        #     df_temp[translate("field", lang)] = geom_name
            
        #     # Agregar el DataFrame temporal al DataFrame final
        #     final_df = pd.concat([final_df, df_temp], ignore_index=True)

        #     # Asumiendo que tu DataFrame se llama df
        #     pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')

        #     # Opcionalmente, puedes resetear el índice si prefieres que la fecha sea una columna regular en lugar de el índice del DataFrame
        #     pivot_df.reset_index(inplace=True)

        # Convertir las columnas de fecha a datetime
        filtered_df['START_DATE'] = pd.to_datetime(filtered_df['START_DATE'])
        filtered_df['END_DATE'] = pd.to_datetime(filtered_df['END_DATE'])

        # Inicializar las fechas
        fecha_de_inicio = filtered_df['START_DATE']
        fecha_de_finalizacion = filtered_df['END_DATE']

        # Convertir las fechas al formato correcto
        START_DATE = fecha_de_inicio.dt.strftime('%Y-%m-%d')
        END_DATE = fecha_de_finalizacion.dt.strftime('%Y-%m-%d')

        # for index, row in filtered_df.iterrows():
        # # Extraer la geometría individual
        #     try:
        #         lote_gdf_filtrado = filtered_df.iloc[[index]]
        #         print(f"Procesando el índice: {index}")
        #         # Llamar a la función con la geometría actual
        #         df_temp = extract_mean_ndvi_date(lote_gdf_filtrado,row[START_DATE],row[END_DATE])
        #         if df_temp.empty:
        #             print(f"No se encontraron datos NDVI para el índice: {index}")
        #             continue
        # Procesar cada fila en el DataFrame filtrado
    # Procesar cada fila en el DataFrame filtrado
        for index, row in filtered_df.iterrows():
            try:
                # Extraer la geometría individual y asegurar que es un DataFrame
                lote_gdf_filtrado = pd.DataFrame([row])
                
                # Verificar que contiene geometría
                if 'geometry' not in lote_gdf_filtrado.columns or lote_gdf_filtrado['geometry'].iloc[0] is None:
                    print(f"Error: No se encontró geometría en lote_gdf_filtrado en el índice {index}")
                    continue

                print(f"Procesando el índice: {index}")

                # Llamar a la función con la geometría actual
                df_temp = extract_mean_ndvi_date(lote_gdf_filtrado, row['START_DATE'].strftime('%Y-%m-%d'), row['END_DATE'].strftime('%Y-%m-%d'))
                if df_temp.empty:
                    print(f"No se encontraron datos NDVI para el índice: {index}")
                    continue

                # Obtener el nombre de la geometría
                geom_name = row["field_name"]

                # Agregar el nombre de la geometría como columna
                df_temp["Lote"] = geom_name

                # Agregar el DataFrame temporal al DataFrame final
                final_df = pd.concat([final_df, df_temp], ignore_index=True)
            except Exception as e:
                print(f"Error procesando el índice {index}: {e}")
                continue

        # Verificar si el DataFrame final está vacío
        if final_df.empty:
            st.error("No se encontraron datos NDVI para ninguna geometría.")
        else:
            # Crear una tabla pivot con 'Date' como índice, 'Lote' como columnas y 'Mean_NDVI' como valores
            pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')
            pivot_df.reset_index(inplace=True)

            # Convertir la columna 'Date' a datetime
            pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

            # Convertir fechas a un formato numérico (número de días desde la primera fecha)
            pivot_df['DateNum'] = (pivot_df['Date'] - pivot_df['Date'].min()) / np.timedelta64(1, 'D')

            # Preparar un nuevo DataFrame para almacenar resultados interpolados
            interpolated_df = pd.DataFrame()
            interpolated_df['Date'] = pivot_df['Date']

            # Interpolar valores faltantes para cada lote usando RBFInterpolator
            for column in pivot_df.columns:
                if column not in ['Date', 'DateNum']:
                    # Filtrar valores nulos y preparar datos para la interpolación
                    x = pivot_df.loc[pivot_df[column].notna(), 'DateNum']
                    y = pivot_df.loc[pivot_df[column].notna(), column]

                    if x.empty or y.empty:
                        print(f"No hay datos para interpolar en la columna: {column}")
                        continue

                    # Crear el interpolador RBF
                    rbf = RBFInterpolator(x.values[:, None], y.values, kernel='thin_plate_spline')

                    # Interpolar valores para todas las fechas
                    y_interp = rbf(pivot_df['DateNum'].values[:, None])

                    # Almacenar resultados interpolados en el DataFrame
                    interpolated_df[column] = y_interp
            
            # Mostrar la tabla con los datos finales
            st.write("Datos NDVI interpolados por lote:")
            st.dataframe(pivot_df,
                        column_config={"DateNum":None},
                        width=100000)
            
            # Crear un gráfico de líneas usando Plotly Express
            fig = px.line(interpolated_df, x='Date', y=interpolated_df.columns[1:], title='NDVI Interpolado por Lotes')
            st.plotly_chart(fig)

            ############################################################################
        
        st.divider()
        st.markdown('')

        ############################################################################
        st.caption("Powered by GeoAgro")

if __name__ == "__main__":
    redirect_uri=" http://localhost:8501"
    user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'test', 'domainId': 1, 'areaId': 1, 'workspaceId': 882, 'seasonId': 172, 'farmId': 2277} # TEST / GeoAgro / GeoAgro / TEST_BONELLI / 2021-22 / Bellamar - Bellamar 
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