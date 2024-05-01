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
import streamlit_google_oauth as oauth
from streamlit_vertical_slider import vertical_slider
import plotly.graph_objects as go
import plotly.express as px

# Manejo de geometrías
from shapely.geometry import shape, mapping, Point

# Interpolación y análisis espacial
from scipy.interpolate import RBFInterpolator

# Earth Engine y mapeo avanzado
import ee
import geemap.foliumap as geemap

# Módulos o paquetes locales
from helper import translate, api_call_logo, decrypt_token
from secretManager import AWSSecret
import logging



#########################################################################################################################
# Page Config y estilo
#########################################################################################################################

st.set_page_config(
    page_title="Tablero de Benchmarking de establecimientos",
    page_icon=Image.open("assets/favicon geoagro nuevo-13.png"),
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://geoagro1.atlassian.net/servicedesk/customer/portal/5',
        'Report a bug': "https://geoagro1.atlassian.net/servicedesk/customer/portal/5",
        'About': "Powered by GeoAgro"
    }
)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

##################### USER INFO #####################
user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'prod', 'domainId': None, 'areaId': None, 'workspaceId': None, 'seasonId': None, 'farmId': None}

language = user_info['language']
email = user_info['email']
env = user_info['env']
st.session_state['env'] = env

##################### API Logo Marca Blanca #####################
    
# secrets = None
# access_key_id = st.secrets["API_key"]
if env == 'test':
    secrets = json.loads(AWSSecret().get_secret(secret_name="test/apigraphql360", region_name="us-west-2"))
elif env == 'prod':
    secrets = json.loads(AWSSecret().get_secret(secret_name="prod/apigraphql360-v2", region_name="us-west-2"))

access_key_id = secrets['x-api-key']
url = secrets['url']

@st.cache_data
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

# st.subheader(translate("dashboards",lang), anchor=False)
st.markdown(f'{translate("requested_by",lang)}<a style="color:blue;font-size:18px;">{""+email+""}</a> | <a style="color:blue;font-size:16px;" target="_self" href="/"> {translate("logout",lang)}</a>', unsafe_allow_html=True)
st.markdown('')
st.markdown('')

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

selected_colors = px.colors.qualitative.T10

#############################
# API BY AREA
#############################
import requests

# Función para realizar la llamada a la API y cachear la respuesta
@st.cache_data
def api_call_data():
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

#access_key_id = st.secrets["API_key"] # Pedia secrets.toml -> en teoria si esta comentado no necesita autenticar.

# URL de tu API GraphQL y headers
url = 'https://lpul7iylefbdlepxbtbovin4zy.appsync-api.us-west-2.amazonaws.com/graphql'
headers = {
    'x-api-key': access_key_id,
    'Content-Type': 'application/json'
}

# Tu consulta GraphQL
query = f'''
query MyQuery {{
  get_field_table(domainId: {user_info['domainId']}, email: "{user_info['email']}", exportAllAsCsv: true, lang: "{user_info['language']}", withHectares: true, withCentroid: true, withGeom: true, delimiter: ";") {{
    csvUrl
  }}
}}
'''

# Llamar a la función api_call que está cacheada
data = api_call_data()

@st.cache_data  # 👈 Add the caching decorator
def load_data(url):
    df = pd.read_csv(url, delimiter=";")
    return df

# Verificar y manejar la respuesta
if data:
    csv_url = data['data']['get_field_table']['csvUrl']
    filtered_df = load_data(csv_url)
    # Eliminar filas donde 'hectares' es NaN
    filtered_df = filtered_df.dropna(subset=['hectares'])

    # Eliminar filas donde 'hectares' es igual a 0
    filtered_df = filtered_df[filtered_df['hectares'] != 0]

    # Guardar el DataFrame filtrado en un archivo CSV
    filtered_df.to_csv('filtered_df.csv', index=False)

    # Procesar filtered_df
else:
    st.error("No se pudo obtener datos de la API.")

filtered_df = pd.read_csv('filtered_df.csv')
############################################################################
# Area
############################################################################

areas = sorted(filtered_df['area_name'].unique().tolist())

container = st.container()
select_all_areas = st.toggle(translate("select_all", lang), key='select_all_areas')

if select_all_areas:
    selector_areas = container.multiselect(
        translate("area", lang),
        areas,
        areas)  # Todos los workspaces están seleccionados por defecto
else:
    selector_areas = container.multiselect(
        translate("area", lang),
        areas,
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
    selector_workspaces = container.multiselect(
        translate("workspace", lang),
        workspaces,
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
    selector_seasons = container.multiselect(
        translate("season", lang),
        seasons,
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
    selector_farms = container.multiselect(
        translate("farm", lang),
        farms,
        placeholder=translate("choose_option", lang)) 

############################################################################
# Cultivo
############################################################################

# Filtra el DataFrame basado en las áreas seleccionadas
filtered_df = filtered_df[filtered_df['farm_name'].isin(selector_farms)]

# Obtén los nombres de los workspaces únicos del DataFrame filtrado
crop = sorted(filtered_df['crop'].unique().tolist())

container = st.container()
select_all_crop = st.toggle(translate("select_all", lang), key='select_all_crop')

if select_all_crop:
    selector_crop = container.multiselect(
        translate("crop", lang),
        crop,
        crop)  # Todos los workspaces están seleccionados por defecto
else:
    selector_crop = container.multiselect(
        translate("crop", lang),
        crop,
        placeholder=translate("choose_option", lang)) 

############################################################################
# Híbrido
############################################################################

# Filtra el DataFrame basado en las áreas seleccionadas
filtered_df = filtered_df[filtered_df['crop'].isin(selector_crop)]

# Obtén los nombres de los workspaces únicos del DataFrame filtrado
hybridos = sorted(filtered_df['hybrid'].unique().tolist())

container = st.container()
select_all_hybrid = st.toggle(translate("select_all", lang), key='select_all_hybrid')

if select_all_hybrid:
    selector_hybrid = container.multiselect(
        translate("hybrid_variety", lang),
        hybridos,
        hybridos)  # Todos los workspaces están seleccionados por defecto
else:
    selector_hybrid = container.multiselect(
        translate("hybrid_variety", lang),
        hybridos,
        placeholder=translate("choose_option", lang)) 
    ############################################################################
    # Powered by GeoAgro Picture
    ############################################################################
    st.markdown('')
    st.markdown('')
    st.markdown('')

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
    # Mapa
    ############################################################################

    ################ Titulo ################

    # Organizar los widgets en dos columnas
    col1, col2, col3 = st.columns([4, 0.1, 2], gap="small")

    # Columna 1: Markdowns
    with col1:
        st.markdown('')
        st.markdown('')
        
    ############################################################################
    import ee  # Import the Earth Engine module

    # Crea una instancia de la clase AWSSecret y obtén el secreto para GEE
    gee_secrets = json.loads(AWSSecret().get_secret(secret_name="prod/streamlit/gee", region_name="us-east-1"))

    # Extrae client_email y la clave privada del secreto
    client_email = gee_secrets['client_email']
    private_key = gee_secrets['private_key']  # Asegúrate de que 'private_key' es el nombre correcto del campo en tu secreto

    # Configura las credenciales y inicializa Earth Engine
    credentials = ee.ServiceAccountCredentials(client_email, key_data=private_key)
    ee.Initialize(credentials)

    # Crea el mapa
    Map = geemap.Map(center=(gdf_poly.geometry.centroid.y.mean(), gdf_poly.geometry.centroid.x.mean()), zoom=14)
    
    gdf_poly.crs = "EPSG:4326"
    Map.add_gdf(gdf_poly, layer_name=translate("fields",lang), fields=[translate("field",lang)])
                
    Map.to_streamlit()

############################################################################
# MAIN
############################################################################
                    
# if __name__ == "__main__":
#     redirect_uri=" http://localhost:8501"
#     user_info = {'email': "tvarela@geoagro.com", 'language': 'es', 'env': 'prod', 'domainId': 1, 'areaId': 0, 'workspaceId': 65, 'seasonId': 1045, 'farmId': 72}
#     main_app(user_info)


# if __name__ == "__main__":
#     redirect_uri = "https://dem.geoagro.com/"
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
#                     'email': user_email, 'language': 'es', 'env': 'prod', 'domainId': None,
#                     'areaId': None, 'workspaceId': None, 'seasonId': None, 'farmId': None
#                 }

#             else:
#                 logging.error("Not logged")

#     if user_info:
#         main_app(user_info)  # Llamar a la función principal de la aplicación con user_info
#     else:
#         st.error("Error accessing the app. Please contact an administrator.")