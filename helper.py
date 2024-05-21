#############################
# TRANSLATIONS 
#############################

from language import translate_dict

def translate(string, language):

    try:
        return translate_dict[string][language]
    except:
        return "Unknown"
    
#############################
# API CALL LOGO MARCA BLANCA 
#############################
    
import requests  
from PIL import Image, UnidentifiedImageError
import base64
import io
import binascii
    
def api_call_logo(user_info, url, access_key_id, default_logo='assets/GeoAgro_principal.png'):
    try:
        headers = {
            'x-api-key': access_key_id,
            'Content-Type': 'application/json'
        }

        query = f'''
        query MyQuery {{
        get_domain(domainId: {user_info['domainId']}, getBase64Logo: true) {{
            base64Logo
            hasLogo
        }}
        }}
        '''
        response = requests.post(url, json={'query': query}, headers=headers)

        if response.status_code != 200:
            logo_image = Image.open(default_logo)
            return logo_image

        # Convertir el contenido de la respuesta de JSON a un diccionario
        data = response.json()

        if data and data['data']['get_domain']["hasLogo"]:
            base64_logo = data['data']['get_domain']['base64Logo']
            
            # Dividir en la coma y usar lo que sigue, si es necesario
            if ',' in base64_logo:
                base64_logo = base64_logo.split(',', 1)[1]

            # Añadir padding si es necesario
            padding = 4 - len(base64_logo) % 4
            if padding:
                base64_logo += "=" * padding

            try:
                # Decodificar el string base64
                logo_bytes = base64.b64decode(base64_logo)
                logo_image = Image.open(io.BytesIO(logo_bytes))
                return logo_image
            except (binascii.Error, UnidentifiedImageError) as e:
                print(f"Error al manejar la imagen: {e}")

        return Image.open(default_logo)
    except: 
        return Image.open(default_logo)

#############################
# API CALL FIELDS TABLE 
#############################

import requests
import pandas as pd

def api_call_fields_table(user_info, access_key_id, url):
    #url = 'https://lpul7iylefbdlepxbtbovin4zy.appsync-api.us-west-2.amazonaws.com/graphql'
    headers = {
        'x-api-key': access_key_id,
        'Content-Type': 'application/json'
    }
    query = f'''
    query MyQuery {{
      get_field_table(domainId: {user_info['domainId']}, email: "{user_info['email']}", exportAllAsCsv: true, lang: "{user_info['language']}", withHectares: true, withCentroid: true, withGeom: true, delimiter: "@") {{
        csvUrl
      }}
    }}
    '''
    response = requests.post(url, json={'query': query}, headers=headers)

    if response.status_code != 200:
        return None
    else:
        data = response.json()
        csv_url = data['data']['get_field_table']['csvUrl']

        df = pd.read_csv(csv_url, delimiter="@")
        # Eliminar filas donde 'hectares' es NaN
        df = df.dropna(subset=['hectares'])

        # Eliminar filas donde 'hectares' es igual a 0
        df = df[df['hectares'] != 0]

        return data, df

#############################
# DECRYPT 
#############################

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
from secretManager import AWSSecret

def get_private_key() -> str:
    secret = json.loads(AWSSecret().get_secret(secret_name="prod/crypt/rsa", region_name="us-west-2"))
    raw_private_key = secret['api_private_rsa_4096']
    pem_private_key = "-----BEGIN RSA PRIVATE KEY-----\n{0}\n-----END RSA PRIVATE KEY-----".format(raw_private_key)
    return pem_private_key

def decrypt_token(token_string: str) -> dict:
    pem_private_key = get_private_key()

    private_key = serialization.load_pem_private_key(
        pem_private_key.encode(),
        password=None,
        backend=default_backend()
    )
    decrypted = private_key.decrypt(
        base64.urlsafe_b64decode(token_string + '=' * (4-len(token_string)%4)),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return json.loads(str(decrypted, 'utf-8'))

#############################
# API CALL DOMAIN BY USER 
#############################

import requests

def domains_areas_by_user(user_email, access_key_id, url):
    headers = {
        'x-api-key': access_key_id,
        'Content-Type': 'application/json'
    }
    query = f'''
    query MyQuery {{
      domains_areas_by_user(email: "{user_email}") {{
        id
        name
      }}
    }}
    '''
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code != 200:
        return None
    else:
        data = response.json()
        return data['data']['domains_areas_by_user']