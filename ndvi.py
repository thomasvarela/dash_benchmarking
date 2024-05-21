import ee
import pandas as pd
from datetime import datetime

# # Leer el DataFrame
# filtered_df = pd.read_csv('filtered_df.csv')

# # Convertir las columnas de fecha a datetime
# filtered_df['start_date'] = pd.to_datetime(filtered_df['start_date'])
# filtered_df['end_date'] = pd.to_datetime(filtered_df['end_date'])

# # Inicializar las fechas
# fecha_de_inicio = filtered_df['start_date']
# fecha_de_finalizacion = filtered_df['end_date']

# # Convertir las fechas al formato correcto
# START_DATE = fecha_de_inicio.dt.strftime('%Y-%m-%d')
# END_DATE = fecha_de_finalizacion.dt.strftime('%Y-%m-%d')

# # Asegúrate de que sean strings, no series
# START_DATE = START_DATE.iloc[0]
# END_DATE = END_DATE.iloc[0]

CLOUD_FILTER = 60
CLD_PRB_THRESH = 40
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 2
BUFFER = 100

# filtered_df = pd.read_csv('filtered_df.csv')

# # Inicializar las fechas
# fecha_de_inicio = filtered_df['start_date']
# fecha_de_finalizacion = filtered_df['end_date']

# # Convertir las fechas al formato correcto
# START_DATE = fecha_de_inicio.strftime('%Y-%m-%d')
# END_DATE = fecha_de_finalizacion.strftime('%Y-%m-%d')
# CLOUD_FILTER = 60
# CLD_PRB_THRESH = 40
# NIR_DRK_THRESH = 0.15
# CLD_PRJ_DIST = 2
# BUFFER = 100

################################################################################
# Filtro de nubes
################################################################################

def get_s2_sr_cld_col(aoi, start_date, end_date):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))

def add_cloud_bands(img):
    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))

def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img.addBands(is_cld_shdw)

################################################################################

def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)

def extract_mean_ndvi_date(lote_gdf_filtrado,START_DATE,END_DATE):
    geom = lote_gdf_filtrado.geometry.iloc[0].__geo_interface__
    ee_geom = ee.Geometry(geom)
    AOI = ee.Geometry(geom)

    def add_ndvi(image):
        image = image.clip(ee_geom)
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)

    s2_sr_cld_col = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
    s2_sr_cld_col = (s2_sr_cld_col.map(add_cld_shdw_mask)
                                    .map(apply_cld_shdw_mask)
                                    .map(add_ndvi))

    def compute_mean(image):
        mean_value = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee_geom,
            scale=10,
            maxPixels=1e9,
            bestEffort=True
        ).get('NDVI')

        return ee.Feature(None, {'date': image.date().format(), 'mean_ndvi': mean_value})

    mean_features = s2_sr_cld_col.map(compute_mean)

    # Convertir la colección de características a una lista y obtener la información.
    info = mean_features.getInfo()['features']

    # Procesamiento final para crear el DataFrame
    records = [{
        'Date': feature['properties']['date'],
        'Mean_NDVI': feature['properties']['mean_ndvi']
    } for feature in info if 'mean_ndvi' in feature['properties']]

    print("Records:", records)

    df = pd.DataFrame(records)
    df['Mean_NDVI'] = df['Mean_NDVI'].apply(lambda x: round(x, 3) if x else None)
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

    return df
