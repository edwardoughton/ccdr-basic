"""
Process hazard layers.

Written by Ed Oughton.

May 4th 2022

"""
import os
import configparser
import json
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape
from misc import get_countries, process_country_shapes, process_regions 

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def process_inuncoast(country, scenarios, return_periods):
    """
    Process coastal flooding.

    """
    iso3 = country['iso3']

    for scenario in scenarios:
        for rp in return_periods:

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inuncoast')
            if not os.path.exists(folder):
                os.mkdir(folder)
            filename = 'inuncoast_{}_wtsub_2080_{}_0.tif'.format(scenario, rp)
            path_out = os.path.join(folder, filename)

            if os.path.exists(path_out):
                continue

            path = os.path.join(BASE_PATH,'..', '..','open-rigbi','data','raw','flood_hazard', filename)

            hazard = rasterio.open(path, 'r+')
            hazard.nodata = 255
            hazard.crs.from_epsg(4326)

            path_country = os.path.join(DATA_PROCESSED, iso3,
                'national_outline.shp')

            if os.path.exists(path_country):
                country = gpd.read_file(path_country)
            else:
                print('Must generate national_outline.shp first' )

            geo = gpd.GeoDataFrame({'geometry': country.geometry})
            coords = [json.loads(geo.to_json())['features'][0]['geometry']]

            out_img, out_transform = mask(hazard, coords, crop=True)
            out_meta = hazard.meta.copy()
            out_meta.update({"driver": "GTiff",
                            "height": out_img.shape[1],
                            "width": out_img.shape[2],
                            "transform": out_transform,
                            "crs": 'epsg:4326'})

            with rasterio.open(path_out, "w", **out_meta) as dest:
                    dest.write(out_img)

    return


def extract_inuncoast(country, scenarios, return_periods):
    """
    Extract coastal flooding.

    """
    iso3 = country['iso3']

    for scenario in scenarios:
        for rp in return_periods:

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inuncoast')
            if not os.path.exists(folder):
                os.mkdir(folder)
            filename = 'inuncoast_{}_wtsub_2080_{}_0.shp'.format(scenario, rp)
            path_out = os.path.join(folder, filename)

            # if os.path.exists(path_out):
            #     continue

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inuncoast')
            if not os.path.exists(folder):
                os.mkdir(folder)
            filename = 'inuncoast_{}_wtsub_2080_{}_0.tif'.format(scenario, rp)
            path_in = os.path.join(folder, filename)

            with rasterio.open(path_in) as src:

                affine = src.transform
                array = src.read(1)#[:1]

                output = []

                for vec in rasterio.features.shapes(array):

                    if vec[1] > 0 and not vec[1] == 255:

                        coordinates = [i for i in vec[0]['coordinates'][0]]

                        coords = []

                        for i in coordinates:

                            x = i[0]
                            y = i[1]

                            x2, y2 = src.transform * (x, y)

                            coords.append((x2, y2))

                        output.append({
                            'type': vec[0]['type'],
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords],
                            },
                            'properties': {
                                'value': vec[1],
                            }
                        })

            if len(output) == 0:
                continue

            output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')
            output.to_file(path_out, driver='ESRI Shapefile')

    return


def process_cyclones(country):
    """
    Process cyclone tracks.

    """
    iso3 = country['iso3']

    filename = 'IBTrACS.since1980.list.v04r00.lines.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'cyclones')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_out = os.path.join(folder, filename)

    if os.path.exists(path_out):
        return

    filename = 'IBTrACS.since1980.list.v04r00.lines.shp'
    folder = os.path.join(DATA_RAW, 'noaa_cyclones', 'IBTrACS.since1980.list.v04r00.lines')
    path = os.path.join(folder, filename)
    hazard = gpd.read_file(path, crs='epsg:4326')

    filename = 'national_outline.shp'
    folder = os.path.join(DATA_PROCESSED, iso3)
    path = os.path.join(folder, filename)
    national_outline = gpd.read_file(path, crs='epsg:4326')
    national_outline['geometry'] = national_outline['geometry'].buffer(2)

    try:
        hazard = gpd.overlay(hazard, national_outline, how='intersection')
        if len(hazard) == 0:
            print('No historical cyclone tracks intersect {}!'.format(iso3))
    except:
        print('Cyclone overlay was not carried out')
        return

    if len(hazard) > 0:
        hazard.to_file(path_out, crs='epsg:4326')

    return


def process_droughts(country):
    """
    Process drought / water stress.

    """
    iso3 = country['iso3']

    filename = 'aqueduct_projections_20150309.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'droughts')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    if os.path.exists(path_out):
        return

    filename = 'aqueduct_projections_20150309.shp'
    folder = os.path.join(DATA_RAW, 'aquaduct_water_stress')
    path = os.path.join(folder, filename)
    hazard = gpd.read_file(path, crs='epsg:4326')

    filename = 'national_outline.shp'
    folder = os.path.join(DATA_PROCESSED, iso3)
    path = os.path.join(folder, filename)
    national_outline = gpd.read_file(path, crs='epsg:4326')

    hazard = gpd.overlay(hazard, national_outline, how='intersection')

    if len(hazard) > 0:
        hazard.to_file(path_out, crs='epsg:4326')

    return


def process_landslides(country):
    """
    Process river flooding.

    """
    iso3 = country['iso3']

    filename = 'ls_arup.tif'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    # if os.path.exists(path_out):
    #     return

    path = os.path.join(DATA_RAW, 'global_landslide_hazard', filename)

    hazard = rasterio.open(path, 'r+')
    hazard.nodata = 255
    hazard.crs.from_epsg(4326)

    iso3 = country['iso3']
    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')

    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        print('Must generate national_outline.shp first' )

    geo = gpd.GeoDataFrame({'geometry': country.geometry})
    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(hazard, coords, crop=True)
    out_meta = hazard.meta.copy()
    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})

    with rasterio.open(path_out, "w", **out_meta) as dest:
            dest.write(out_img)

    return


def extract_landslides(country):
    """
    Extract coastal flooding.

    """
    iso3 = country['iso3']

    filename = 'ls_arup.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    # if os.path.exists(path_out):
    #     return

    filename = 'national_outline.shp'
    folder = os.path.join(DATA_PROCESSED, iso3)
    path = os.path.join(folder, filename)
    national_outline = gpd.read_file(path, crs='epsg:4326')

    filename = 'ls_arup.tif'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path = os.path.join(folder, filename)

    with rasterio.open(path) as src:

        affine = src.transform
        array = src.read(1)#[:1]

        output = []

        for vec in rasterio.features.shapes(array):

            if not vec[1] == 255: #vec[1] >= 3 and 

                coordinates = [i for i in vec[0]['coordinates'][0]]

                coords = []

                for i in coordinates:

                    x = i[0]
                    y = i[1]

                    x2, y2 = src.transform * (x, y)

                    coords.append((x2, y2))

                output.append({
                    'type': vec[0]['type'],
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [coords],
                    },
                    'properties': {
                        'Risk': str(vec[1]),
                    }
                })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')
        output.to_file(path_out, driver='ESRI Shapefile')

    return


def process_inunriver(country, scenarios, models, return_periods):
    """
    Process river flooding.

    """
    iso3 = country['iso3']

    for scenario in scenarios:
        for model in models:
            for rp in return_periods:

                folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
                if not os.path.exists(folder):
                    os.mkdir(folder)
                filename = 'inunriver_{}_{}_2080_{}.tif'.format(scenario, model, rp)
                path_out = os.path.join(folder, filename)

                if os.path.exists(path_out):
                    continue

                path = os.path.join(DATA_RAW, 'flood_hazard', filename)

                hazard = rasterio.open(path, 'r+')
                hazard.nodata = 255
                hazard.crs.from_epsg(4326)

                path_country = os.path.join(DATA_PROCESSED, iso3,
                    'national_outline.shp')

                if os.path.exists(path_country):
                    country = gpd.read_file(path_country)
                else:
                    print('Must generate national_outline.shp first' )

                geo = gpd.GeoDataFrame({'geometry': country.geometry})
                coords = [json.loads(geo.to_json())['features'][0]['geometry']]

                out_img, out_transform = mask(hazard, coords, crop=True)
                out_meta = hazard.meta.copy()
                out_meta.update({"driver": "GTiff",
                                "height": out_img.shape[1],
                                "width": out_img.shape[2],
                                "transform": out_transform,
                                "crs": 'epsg:4326'})

                with rasterio.open(path_out, "w", **out_meta) as dest:
                        dest.write(out_img)

    return


def extract_inunriver(country, scenarios, models, return_periods):
    """
    Extract river flooding.

    """
    iso3 = country['iso3']

    for scenario in scenarios:
        for model in models:
            for rp in return_periods:

                folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
                if not os.path.exists(folder):
                    os.mkdir(folder)
                filename = 'inunriver_{}_{}_2080_{}.shp'.format(scenario, model, rp)
                path_out = os.path.join(folder, filename)

                if os.path.exists(path_out):
                    continue

                folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
                if not os.path.exists(folder):
                    os.mkdir(folder)
                filename = 'inunriver_{}_{}_2080_{}.tif'.format(scenario, model, rp)
                path_in = os.path.join(folder, filename)

                with rasterio.open(path_in) as src:

                    affine = src.transform
                    array = src.read(1)#[:1]

                    output = []

                    for vec in rasterio.features.shapes(array):

                        if vec[1] > 0 and not vec[1] == 255:

                            coordinates = [i for i in vec[0]['coordinates'][0]]

                            coords = []

                            for i in coordinates:

                                x = i[0]
                                y = i[1]

                                x2, y2 = src.transform * (x, y)

                                coords.append((x2, y2))

                            output.append({
                                'type': vec[0]['type'],
                                'geometry': {
                                    'type': 'Polygon',
                                    'coordinates': [coords],
                                },
                                'properties': {
                                    'value': vec[1],
                                }
                            })

                output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')
                output.to_file(path_out, driver='ESRI Shapefile')

    return


def process_wildfires(country):
    """
    Process wildfires.

    """
    iso3 = country['iso3']

    filename = 'hazard__csiro_wf_max_fwi_rp30.tif'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'wildfires')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    # if os.path.exists(path_out):
    #     return

    path = os.path.join(DATA_RAW,'wildfire', filename)

    hazard = rasterio.open(path, 'r+')
    hazard.nodata = 255
    hazard.crs.from_epsg(4326)

    iso3 = country['iso3']
    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')

    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        print('Must generate national_outline.shp first' )

    # country['geometry'] = country['geometry'].buffer(.1)
    # bbox = country.envelope

    geo = gpd.GeoDataFrame({'geometry': country.geometry})
    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(hazard, coords, crop=True)
    out_meta = hazard.meta.copy()
    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})

    with rasterio.open(path_out, "w", **out_meta) as dest:
            dest.write(out_img)

    return


def extract_wildfires(country):
    """
    Extract wildfires.

    """
    iso3 = country['iso3']

    filename = 'hazard__csiro_wf_max_fwi_rp30.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'wildfires')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    # if os.path.exists(path_out):
    #     return

    filename = 'national_outline.shp'
    folder = os.path.join(DATA_PROCESSED, iso3)
    path = os.path.join(folder, filename)
    national_outline = gpd.read_file(path, crs='epsg:4326')

    filename = 'hazard__csiro_wf_max_fwi_rp30.tif'
    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'wildfires')
    if not os.path.exists(folder):
        os.mkdir(folder)
    path = os.path.join(folder, filename)

    with rasterio.open(path) as src:

        affine = src.transform
        array = src.read(1)#[:1]

        output = []

        for vec in rasterio.features.shapes(array):

            if vec[1] > 100 and not vec[1] == 255:

                coordinates = [i for i in vec[0]['coordinates'][0]]

                coords = []

                for i in coordinates:

                    x = i[0]
                    y = i[1]

                    x2, y2 = src.transform * (x, y)

                    coords.append((x2, y2))

                output.append({
                    'type': vec[0]['type'],
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [coords],
                    },
                    'properties': {
                        'value': vec[1],
                    }
                })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')
        output = gpd.overlay(output, national_outline, how='intersection')
        output.to_file(path_out, driver='ESRI Shapefile')

    return


if __name__ == '__main__':

    scenarios = [
        'rcp4p5',
        'rcp8p5'
    ]

    models = [
        '00000NorESM1-M',
        '0000GFDL-ESM2M',
        '0000HadGEM2-ES',
        '00IPSL-CM5A-LR',
        'MIROC-ESM-CHEM',
    ]

    return_periods_coastal = [
        'rp1000',
        'rp0500',
        'rp0100',
        'rp0050',
        'rp0025'
    ]

    return_periods_riverine = [
        'rp01000',
        'rp00500',
        'rp00100',
        'rp00050',
        'rp00025'
    ]

    countries = get_countries()

    for idx, country in countries.iterrows():

        if not country['iso3'] in ['KEN']: #,'AZE']: 'AZE', 'KEN'
            continue

        print('processing process_country_shapes')
        process_country_shapes(country['iso3'])

        print('processing process_regions')
        process_regions(country['iso3'], country['gid_region'])

        print('processing coastal')
        process_inuncoast(country, scenarios, return_periods_coastal)

        print('extracting coastal')
        extract_inuncoast(country, scenarios, return_periods_coastal)

        print('processing cyclones')
        process_cyclones(country) #cyclones

        print('processing droughts')
        process_droughts(country) #drought flooding

        print('processing landslides')
        process_landslides(country) #landslides

        print('extracting landslides')
        extract_landslides(country)

        print('processing rivers')
        process_inunriver(country, scenarios, models, return_periods_riverine) #river flooding

        print('extracting rivers')
        extract_inunriver(country, scenarios, models, return_periods_riverine)

        print('processing wildfires')
        process_wildfires(country) #wildfires

        print('extracting wildfires')
        extract_wildfires(country)
