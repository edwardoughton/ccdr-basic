"""
Preprocess sites data.

Ed Oughton

February 2022

"""
import sys
import os
import configparser
import json
import pandas as pd
import geopandas as gpd
import pyproj
from shapely.ops import transform
from shapely.geometry import Point, box, LineString
import rasterio
from rasterio.mask import mask
from tqdm import tqdm
import numpy as np

from misc import get_countries, process_country_shapes, process_regions, get_regions, get_scenarios
from fiber import process_fiber

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__),'..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def run_preprocessing(country):
    """
    Meta function for running preprocessing.

    """
    iso3 = country['iso3']
    regional_level = int(country['gid_region'])

    print('Working on create_national_sites_csv')
    create_national_sites_csv(country)

    print('Working on process_country_shapes')
    process_country_shapes(iso3)

    print('Working on process_regions')
    process_regions(iso3, regional_level)

    print('Working on create_national_sites_shp')
    create_national_sites_shp(iso3)

    print('Working on process_flooding_layers')
    process_flooding_layers(country)

    # print('Working on process_fiber')
    # process_fiber(iso3)
    
    regions_df = get_regions(country, regional_level)#[:1]#[::-1]

    print('Working on regional disaggregation')
    for idx, region in regions_df.iterrows():

        region = region['GID_{}'.format(regional_level)]

        # if not region == 'COD.1_1':
        #    continue

        if regional_level == 1:

            #print('Working on segment_by_gid_1')
            segment_by_gid_1(iso3, 1, region)

            #print('Working on create_regional_sites_layer')
            create_regional_sites_layer(iso3, 1, region)

        if regional_level == 2:

            gid_1 = get_gid_1(region)

            #print('Working on segment_by_gid_1')
            segment_by_gid_1(iso3, 1, gid_1)

            #print('Working on create_regional_sites_layer')
            create_regional_sites_layer(iso3, 1, gid_1)

            #print('Working on segment_by_gid_2')
            segment_by_gid_2(iso3, 2, region, gid_1)

            #print('Working on create_regional_sites_layer')
            create_regional_sites_layer(iso3, 2, region)

    gid_id = "GID_{}".format(regional_level)
    region_ids = regions_df[gid_id].unique()
    print("processing regional flood layers")
    for region in region_ids:
        # print(region)
        # region = region['GID_{}'.format(regional_level)]
        process_regional_flooding_layers(country, region)

    #     polygon = regions_df[regions_df[gid_id] == region]

    #     if not len(polygon) > 0:
    #         continue

    #     # if not region == 'AZE.1_1':
    #     #    continue

    #     create_sites_layer(country, regional_level, region, polygon)

    return


def create_national_sites_csv(country):
    """
    Create a national sites csv layer for a selected country.

    """
    iso3 = country['iso3']#.values[0]

    filename = "mobile_codes.csv"
    path = os.path.join(DATA_RAW, filename)
    mobile_codes = pd.read_csv(path)
    mobile_codes = mobile_codes[['iso3', 'mcc', 'mnc']].drop_duplicates()
    all_mobile_codes = mobile_codes[mobile_codes['iso3'] == iso3]
    all_mobile_codes = all_mobile_codes.to_dict('records')

    output = []

    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path_csv = os.path.join(folder, filename)

    ### Produce national sites data layers
    if os.path.exists(path_csv):
        return

    print('-site.csv data does not exist')
    print('-Subsetting site data for {}'.format(iso3))

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = "cell_towers_2022-12-24.csv"
    path = os.path.join(DATA_RAW, filename)

    for row in all_mobile_codes:

        # if not row['mnc'] in [10,2,11,33,34,20,94,30,31,32,27,15,91,89]:
        #     continue

        mcc = row['mcc']
        seen = set()
        chunksize = 10 ** 6
        for idx, chunk in enumerate(pd.read_csv(path, chunksize=chunksize)):

            country_data = chunk.loc[chunk['mcc'] == mcc]#[:1]

            country_data = country_data.to_dict('records')

            for site in country_data:

                # if not -4 > site['lon'] > -6:
                #     continue

                # if not 49.8 < site['lat'] < 52:
                #     continue

                if site['cell'] in seen:
                    continue

                seen.add(site['cell'])

                output.append({
                    'radio': site['radio'],
                    'mcc': site['mcc'],
                    'net': site['net'],
                    'area': site['area'],
                    'cell': site['cell'],
                    'unit': site['unit'],
                    'lon': site['lon'],
                    'lat': site['lat'],
                    # 'range': site['range'],
                    # 'samples': site['samples'],
                    # 'changeable': site['changeable'],
                    # 'created': site['created'],
                    # 'updated': site['updated'],
                    # 'averageSignal': site['averageSignal']
                })
            # if len(output) > 0:
            #     break

    if len(output) == 0:
        return

    output = pd.DataFrame(output)
    output.to_csv(path_csv, index=False)

    return


def create_national_sites_shp(iso3):
    """
    Create a national sites csv layer for a selected country.

    """
    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path_csv = os.path.join(folder, filename)

    filename = '{}.shp'.format(iso3)
    path_shp = os.path.join(folder, filename)

    if not os.path.exists(path_shp):

        print('-Writing site shapefile data for {}'.format(iso3))

        country_data = pd.read_csv(path_csv)#[:10]

        output = []

        for idx, row in country_data.iterrows():
            output.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['lon'],row['lat']]
                },
                'properties': {
                    'radio': row['radio'],
                    'mcc': row['mcc'],
                    'net': row['net'],
                    'area': row['area'],
                    'cell': row['cell'],
                }
            })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        output.to_file(path_shp)


def process_flooding_layers(country):
    """
    Loop to process all flood layers.

    """
    scenarios = get_scenarios()
    iso3 = country['iso3']
    name = country['country']

    hazard_dir = os.path.join(DATA_RAW, 'flood_hazard')

    failures = []

    for scenario in scenarios:

        #if 'river' in scenario:
        #    continue

        # if not os.path.basename(scenario) == 'inunriver_rcp4p5_0000HadGEM2-ES_2050_rp00500.tif':
        #    continue

        filename = os.path.basename(scenario).replace('.tif','')
        path_in = os.path.join(hazard_dir, filename + '.tif')

        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'flooding')
        if not os.path.exists(folder):
            os.makedirs(folder)
        path_out = os.path.join(folder, filename + '.tif')

        if os.path.exists(path_out):
            continue

        print('--{}: {}'.format(name, filename))

        if not os.path.exists(folder):
            os.makedirs(folder)

        try:
            process_flood_layer(country, path_in, path_out)
        except:
            print('{} failed: {}'.format(country['iso3'], scenario))
            failures.append({
                 'iso3': country['iso3'],
                 'filename': filename
            })
            continue

    return


def process_flood_layer(country, path_in, path_out):
    """
    Clip the hazard layer to the chosen country boundary
    and place in desired country folder.

    Parameters
    ----------
    country : dict
        Contains all desired country information.
    path_in : string
        The path for the chosen global hazard file to be processed.
    path_out : string
        The path to write the clipped hazard file.

    """
    iso3 = country['iso3']
    regional_level = country['gid_region']

    hazard = rasterio.open(path_in, 'r+', BIGTIFF='YES')

    hazard.nodata = 255
    hazard.crs.from_epsg(4326)

    iso3 = country['iso3']
    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')

    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        print('Must generate national_outline.shp first' )

    # if os.path.exists(path_out):
    #     return

    geo = gpd.GeoDataFrame()

    geo = gpd.GeoDataFrame({'geometry': country['geometry']})

    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(hazard, coords, crop=True)

    depths = []

    for idx, row in enumerate(out_img[0]):
        for idx2, i in enumerate(row):
            if i > 0.001 and i < 150:
                depths.append(i)
            else:
                continue
    if sum(depths) < 0.01:
        return

    out_meta = hazard.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326',
                    "compress": 'lzw'})

    with rasterio.open(path_out, "w", **out_meta) as dest:
            dest.write(out_img)

    return


# def segment_by_gid_1(iso3, level):
#     """
#     Segment sites by gid_1 bounding box.

#     """
#     gid_id = 'GID_{}'.format(level)

#     filename = '{}.csv'.format(iso3)
#     folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
#     path = os.path.join(folder, filename)
#     if not os.path.exists(path):
#         return
#     sites = pd.read_csv(path)#[:100]
#     # print(len(sites))
#     filename = 'regions_{}_{}.shp'.format(level, iso3)
#     folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
#     path = os.path.join(folder, filename)
#     regions = gpd.read_file(path, crs='epsg:4326')#[:1]

#     region = regions.iloc[-1]
#     gid_id = region['GID_{}'.format(level)]
#     filename = '{}.shp'.format(gid_id)
#     folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
#     path = os.path.join(folder, filename)
#     if os.path.exists(path):
#         return

#     for idx, region in tqdm(regions.iterrows(), total=regions.shape[0]):

#         gid_level = 'GID_{}'.format(level)

#         gid_id = region[gid_level]

#         filename = '{}.csv'.format(gid_id)
#         folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
#         if not os.path.exists(folder):
#             os.makedirs(folder)
#         path = os.path.join(folder, filename)

#         if os.path.exists(path):
#             continue

#         if idx == 0:
#             print('-Working on GID_{} regional site layer'.format(level))

#         xmin, ymin, xmax, ymax = region['geometry'].bounds

#         output = []

#         for idx, site in sites.iterrows():

#             x, y = site['lon'], site['lat']

#             if not xmin <= x <= xmax:
#                 continue

#             if not ymin <= y <= ymax:
#                 continue

#             output.append({
#                 'radio': site['radio'],
#                 'mcc': site['mcc'],
#                 'net': site['net'],
#                 'area': site['area'],
#                 'cell': site['cell'],
#                 'unit': site['unit'],
#                 'lon': site['lon'],
#                 'lat': site['lat'],
#                 'range': site['range'],
#                 'samples': site['samples'],
#                 'changeable': site['changeable'],
#                 'created': site['created'],
#                 'updated': site['updated'],
#                 'averageSignal': site['averageSignal']
#             })

#         if len(output) > 0:

#             output = pd.DataFrame(output)
#             output.to_csv(path, index=False)

#         else:
#             continue

#     return


# def segment_by_gid_2(iso3, level):
#     """
#     Segment sites by gid_2 bounding box.

#     """
#     gid_id = 'GID_{}'.format(level)

#     filename = 'regions_{}_{}.shp'.format(level, iso3)
#     folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
#     path = os.path.join(folder, filename)
#     regions = gpd.read_file(path, crs='epsg:4326')#[:1]

#     for idx, region in tqdm(regions.iterrows(), total=regions.shape[0]):

#         gid_level = 'GID_{}'.format(level)
#         gid_id = region[gid_level]

#         filename = '{}.shp'.format(region['GID_1'])
#         folder_out = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
#         if not os.path.exists(folder_out):
#             os.makedirs(folder_out)
#         path = os.path.join(folder_out, filename)
#         if os.path.exists(path):
#             return

#         filename = '{}.csv'.format(region['GID_1'])
#         folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
#         path_out = os.path.join(folder, filename)

#         if os.path.exists(path_out):
#             continue

#         if idx == 0:
#             print('-Working on GID_{} regional site layer'.format(level))

#         xmin, ymin, xmax, ymax = region['geometry'].bounds

#         filename = '{}.csv'.format(region['GID_1'])
#         folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
#         path = os.path.join(folder, filename)
#         if not os.path.exists(path):
#             continue
#         sites = pd.read_csv(path)

#         output = []

#         for idx, site in sites.iterrows():

#             x, y = site['lon'], site['lat']

#             if not xmin < x < xmax:
#                 continue

#             if not ymin < y < ymax:
#                 continue

#             output.append({
#                 'radio': site['radio'],
#                 'mcc': site['mcc'],
#                 'net': site['net'],
#                 'area': site['area'],
#                 'cell': site['cell'],
#                 'unit': site['unit'],
#                 'lon': site['lon'],
#                 'lat': site['lat'],
#                 'range': site['range'],
#                 'samples': site['samples'],
#                 'changeable': site['changeable'],
#                 'created': site['created'],
#                 'updated': site['updated'],
#                 'averageSignal': site['averageSignal']
#             })

#         if len(output) > 0:

#             output = pd.DataFrame(output)

#             filename = '{}.csv'.format(gid_id)
#             folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
#             path_out = os.path.join(folder, filename)
#             output.to_csv(path_out, index=False)

#         else:
#             continue

#     return


def get_gid_1(region):
    """
    Get gid_1 handle from gid_2
    """
    split = region.split('.')
    iso3 = split[0]
    item1 = split[1]
    item2 = split[2]
    item3 = split[2].split('_')[1]

    gid_2 = "{}.{}_{}".format(iso3, item1, item3)

    return gid_2


def segment_by_gid_1(iso3, level, region):
    """
    Segment sites by gid_1 bounding box.

    """
    gid_level = 'GID_1'#.format(level)
    # if level == 2:
    #     gid_1 = get_gid_1(region)
    # else:
    #     gid_1 = region

    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path = os.path.join(folder, filename)
    sites = pd.read_csv(path)#[:100]

    filename = 'regions_{}_{}.shp'.format(1, iso3)

    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')#[:1]
    region_df = regions[regions[gid_level] == region]['geometry'].values[0]

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_out = os.path.join(folder, filename)
    if os.path.exists(path_out):
        return

    xmin, ymin, xmax, ymax = region_df.bounds

    output = []

    for idx, site in sites.iterrows():

        x, y = site['lon'], site['lat']

        if not xmin <= x <= xmax:
            continue

        if not ymin <= y <= ymax:
            continue

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'unit': site['unit'],
            'lon': site['lon'],
            'lat': site['lat'],
            # 'range': site['range'],
            # 'samples': site['samples'],
            # 'changeable': site['changeable'],
            # 'created': site['created'],
            # 'updated': site['updated'],
            # 'averageSignal': site['averageSignal']
        })

    if len(output) > 0:
        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)
    else:
        return

    return


def segment_by_gid_2(iso3, level, region, gid_1):
    """
    Segment sites by gid_2 bounding box.

    """
    gid_level = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')#[:1]

    region_df = regions[regions[gid_level] == region]
    region_df = region_df['geometry'].values[0]

    # filename = '{}.shp'.format(region['GID_1'])
    folder_out = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)
    # path = os.path.join(folder_out, filename)
    #if os.path.exists(path):
    #    return

    filename = '{}.csv'.format(region)
    path_out = os.path.join(folder_out, filename)

    if os.path.exists(path_out):
        return

    try:
        xmin, ymin, xmax, ymax = region_df.bounds
    except:
        return

    filename = '{}.csv'.format(gid_1)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return
    sites = pd.read_csv(path)

    output = []

    for idx, site in sites.iterrows():

        x, y = site['lon'], site['lat']

        if not xmin < x < xmax:
            continue

        if not ymin < y < ymax:
            continue

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'unit': site['unit'],
            'lon': site['lon'],
            'lat': site['lat'],
            # 'range': site['range'],
            # 'samples': site['samples'],
            # 'changeable': site['changeable'],
            # 'created': site['created'],
            # 'updated': site['updated'],
            # 'averageSignal': site['averageSignal']
        })

    if len(output) > 0:

        output = pd.DataFrame(output)

        filename = '{}.csv'.format(region)
        folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
        path_out = os.path.join(folder, filename)
        output.to_csv(path_out, index=False)

    else:
        return

    return


def create_regional_sites_layer(iso3, level, region):
    """
    Create regional site layers.

    """
    project = pyproj.Transformer.from_proj(
        pyproj.Proj('epsg:4326'), # source coordinate system
        pyproj.Proj('epsg:3857')) # destination coordinate system

    gid_level = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')#[:1]
    region_df = regions[regions[gid_level] == region]
    region_df = region_df['geometry'].values[0]

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower())
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    # if os.path.exists(path_out):
    #     return

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower(), 'interim')
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return
    sites = pd.read_csv(path)

    filename = '{}.shp'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'surface_water', 'regions')
    path_in = os.path.join(folder, filename)
    on_water = 0
    surface_water = []
    if os.path.exists(path_in):
        surface_water = gpd.read_file(path_in, crs='epsg:4326')
        surface_water = surface_water.unary_union

    output = []

    for idx, site in sites.iterrows():

        geom = Point(site['lon'], site['lat'])

        if not geom.intersects(region_df):
            continue

        if not type(surface_water) == list:
            try:
                surface_water_results = surface_water.contains(geom)
                if surface_water_results.any():
                    on_water = 1
            except:
                on_water = 0

        geom_4326 = geom

        geom_3857 = transform(project.transform, geom_4326)

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'gid_level': gid_level,
            'gid_id': region,
            'cellid4326': '{}_{}'.format(
                round(geom_4326.coords.xy[0][0],6),
                round(geom_4326.coords.xy[1][0],6)
            ),
            'cellid3857': '{}_{}'.format(
                round(geom_3857.coords.xy[0][0],6),
                round(geom_3857.coords.xy[1][0],6)
            ),
            'on_water': on_water
        })

    if len(output) > 0:

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

    else:
        return

    return


def process_surface_water(country, region):
    """
    Load in intersecting raster layers, and export large
    water bodies as .shp.

    Parameters
    ----------
    country : string
        Country parameters.

    """
    level = country['gid_region']
    gid_id = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, country['iso3'])
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')
    polygon = regions[regions[gid_id] == region]

    filename = '{}.shp'.format(region)
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'surface_water', 'regions')
    path_out = os.path.join(folder, filename)
    if not os.path.exists(folder):
        os.makedirs(folder)

    poly_bounds = polygon['geometry'].total_bounds
    poly_bbox = box(*poly_bounds, ccw = False)

    path_lc = os.path.join(DATA_RAW, 'global_surface_water', 'chopped')

    surface_files = [
        os.path.abspath(os.path.join(path_lc, f)
        ) for f in os.listdir(path_lc) if f.endswith('.tif')
    ]

    output = []

    for surface_file in surface_files:

        # print(os.path.basename(surface_file))
        # if not os.path.basename(surface_file) in [
        #     # 'occurrence_20E_0Nv1_3_2020.tif',
        #     'occurrence_30E_0Nv1_3_2020_0_0.tif'
        #     ]:
        #     continue

        path = os.path.join(path_lc, surface_file)

        src = rasterio.open(path, 'r+')

        tiff_bounds = src.bounds
        tiff_bbox = box(*tiff_bounds)

        if tiff_bbox.intersects(poly_bbox):

            print('-Working on {}'.format(surface_file))

            data = src.read()
            data[data < 10] = 0
            data[data >= 10] = 1
            polygons = rasterio.features.shapes(data, transform=src.transform)

            for poly, value in polygons:
                if value > 0:
                    output.append({
                        'geometry': poly,
                        'properties': {
                            'value': value
                        }
                    })

    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    #folder = os.path.join(DATA_PROCESSED, country['iso3'], 'surface_water', 'regions')
    #output.to_file(os.path.join(folder, 'test.shp'), crs='epsg:4326')

    mask = output.area > .0001 #country['threshold']
    output = output.loc[mask]

    output = gpd.overlay(output, polygon, how='intersection')

    output['geometry'] = output.apply(remove_small_shapes, axis=1)

    mask = output.area > .0001 #country['threshold']
    output = output.loc[mask]

    output.to_file(path_out, crs='epsg:4326')

    return


def process_regional_flooding_layers(country, region):
    """
    Process each flooding layer at the regional level.

    """
    scenarios = get_scenarios()
    iso3 = country['iso3']
    name = country['country']

    hazard_dir = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'flooding')

    for scenario in scenarios:

        #if 'river' in scenario:
        #    continue

        #if not os.path.basename(scenario) == 'inuncoast_rcp8p5_wtsub_2080_rp1000_0.tif':
        #    continue

        filename = os.path.basename(scenario).replace('.tif','')
        path_in = os.path.join(hazard_dir, filename + '.tif')

        if not os.path.exists(path_in):
            continue

        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'flooding', 'regional')
        if not os.path.exists(folder):
            os.makedirs(folder)
        path_out = os.path.join(folder, region + '_' + filename + '.tif')

        if os.path.exists(path_out):
            continue

        print('--{}: {}'.format(region, filename))

        if not os.path.exists(folder):
            os.makedirs(folder)

        try:
            process_regional_flood_layer(country, region, path_in, path_out)
        except:
            print('{} failed: {}'.format(country['iso3'], scenario))
            continue

    return


def process_regional_flood_layer(country, region, path_in, path_out):
    """
    Clip the hazard layer to the chosen country boundary
    and place in desired country folder.

    Parameters
    ----------
    country : dict
        Contains all desired country information.
    path_in : string
        The path for the chosen global hazard file to be processed.
    path_out : string
        The path to write the clipped hazard file.

    """
    iso3 = country['iso3']
    regional_level = country['gid_region']
    gid_level = 'GID_{}'.format(regional_level)

    hazard = rasterio.open(path_in, 'r+', BIGTIFF='YES')
    hazard.nodata = 255
    hazard.crs.from_epsg(4326)

    iso3 = country['iso3']
    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    path_country = os.path.join(DATA_PROCESSED, iso3, 'regions', filename)

    if os.path.exists(path_country):
        regions = gpd.read_file(path_country)
        region = regions[regions[gid_level] == region]
    else:
        print('Must generate national_outline.shp first' )
        return

    geo = gpd.GeoDataFrame()

    geo = gpd.GeoDataFrame({'geometry': region['geometry']})

    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(hazard, coords, crop=True)

    depths = []
    for idx, row in enumerate(out_img[0]):
        for idx2, i in enumerate(row):
            if i > 0.001 and i < 150:
                # coords = raster.transform * (idx2, idx)
                depths.append(i)
            else:
                continue

    if sum(depths) < 0.01:
        return

    out_meta = hazard.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})
    #print(path_out)
    with rasterio.open(path_out, "w", **out_meta) as dest:
            dest.write(out_img)

    return


def create_sites_layer(country, regional_level, region, polygon):
    """
    Process cell estimates into an estimated site layer.

    """
    gid_level = "gid_{}".format(regional_level)
    filename = "{}.csv".format(region)
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'sites', gid_level)
    path = os.path.join(folder, filename)

    if not os.path.join(path):
        return

    data = pd.read_csv(path)

    data = convert_to_gpd_df(data)

    data = gpd.overlay(data, polygon, how='intersection')

    data['cell_id'] = round(data['cell'] / 256)
    unique_operators = data['net'].unique()
    unique_cell_ids = data['cell_id'].unique()
    unique_radios = data['radio'].unique()

    output = []

    for unique_operator in unique_operators:
        for unique_cell_id in unique_cell_ids:
            for unique_radio in unique_radios:

                if unique_radio in ["LTE", "NR"]:

                    latitudes = []
                    longitudes = []

                    for idx, row in data.iterrows():

                        if not unique_operator == row['net']:
                            continue

                        if not unique_cell_id == row['cell_id']:
                            continue

                        if not unique_radio == row['radio']:
                            continue

                        lon, lat = row['cellid4326'].split("_")
                        latitudes.append(float(lat))
                        longitudes.append(float(lon))

                    if len(latitudes) == 0:
                        continue
                    latitude = sum(latitudes) / len(latitudes)

                    if len(longitudes) == 0:
                        continue
                    longitude = sum(longitudes) / len(longitudes)

                    output.append({
                        "radio": unique_radio,
                        "net": unique_operator,
                        "cell_id": unique_cell_id,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cellid4326": "{}_{}".format(latitude, longitude)
                    })

                else:

                    for idx, row in data.iterrows():

                        if not unique_operator == row['net']:
                            continue

                        if not unique_cell_id == row['cell_id']:
                            continue

                        if not unique_radio == row['radio']:
                            continue

                        longitude, latitude = row['cellid4326'].split("_")

                        output.append({
                            "radio": unique_radio,
                            "net": unique_operator,
                            "cell_id": unique_cell_id,
                            "latitude": latitude,
                            "longitude": longitude,
                            "cellid4326": "{}_{}".format(latitude, longitude)
                        })

    if len(output) == 0:
        return

    output = pd.DataFrame(output)

    filename = "{}_unique.csv".format(region)
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'sites', gid_level)
    path_out = os.path.join(folder, filename)
    output.to_csv(path_out, index=False)

    return


def convert_to_gpd_df(data):
    """
    Convert pandas df to geopandas df.

    """

    lon = data['cellid4326'].str.split("_", n = 1, expand = True)#[0]
    lat = data['cellid4326'].str.split("_", n = 1, expand = True)#[1]

    data['lon'] = lon[0]
    data['lat'] = lat[1]

    data['lon'] = pd.to_numeric(data['lon'])
    data['lat'] = pd.to_numeric(data['lat'])

    data = gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data.lon, data.lat), crs='epsg:4326'
    )

    return data


def preprocess_supply_data():
    """
    
    """
    preprocess_kenya_huduma_data()

    preprocess_kenya_wifi_data()

    return


def preprocess_kenya_huduma_data():
    """
    
    """
    filename = "Huduma Centres Locations and Coordinates.csv"
    folder = os.path.join(BASE_PATH,'raw', 'kenya_supply_data')
    path_in = os.path.join(folder, filename)
    data = pd.read_csv(path_in)
    data = data[['GPS COORDINATES','HUDUMA KENYA SITES','PHYSICAL LOCATIONS']]
    data = data.dropna()
    data = data.to_dict('records')

    output = []

    for item in data:

        x1, y1 = item['GPS COORDINATES'].split(',')
        
        geom = Point(float(y1),float(x1))
        
        output.append({
            'geometry': geom,
            'properties': {
                'sites': item['HUDUMA KENYA SITES'],
                'locations': item['PHYSICAL LOCATIONS']
            }
        })

    output = gpd.GeoDataFrame.from_features(output)

    filename = 'huduma_centers_locations.shp'
    folder = os.path.join(DATA_PROCESSED, 'KEN', 'network_existing')
    path_out = os.path.join(folder, filename)
    output.to_file(path_out)

    return


def preprocess_kenya_wifi_data():
    """
    
    """
    filename = "PUBLIC WI-FI 10 SITES PER COUNTY FINAL.xlsx"
    folder = os.path.join(BASE_PATH,'raw', 'kenya_supply_data')
    path_in = os.path.join(folder, filename)
    data = pd.read_excel(path_in,sheet_name = None, header = 1)
    sheet_names = [i for i in data]

    data = pd.read_excel(path_in, sheet_name=sheet_names, header=1)
    data = pd.concat(data.values(), ignore_index=True)

    data = data[['Proposed Public WIFI site', 'Coordinates', 
                 'Nearest NOFBI Node', 'Coordinates.1']]
    # data = data.dropna()

    data = data.to_dict('records')

    output = []

    for item in data:

        coords1 = str(item['Coordinates']).replace('(','').replace(')','')
        coords2 = str(item['Coordinates.1']).replace('(','').replace(')','')

        try:
            x1, y1 = coords1.split(',')
            x1, y1 = float(x1), float(y1)
        except:
            continue
        try:
            x2, y2 = coords2.split(',')
            x2, y2 = float(x2), float(y2)
        except:
            x2, y2 = 0, 0

        output.append({
            'geometry': Point(float(y1),float(x1)),
            'nofbi_site': Point(float(y2),float(x2)),
            'properties': {
                'proposed_public_site': item['Proposed Public WIFI site'],
                'nearest_nofbi_site': item['Nearest NOFBI Node'],
            }
        })

    output = gpd.GeoDataFrame.from_features(output)

    filename = 'public_wifi_sites.shp'
    folder = os.path.join(DATA_PROCESSED, 'KEN', 'network_existing')
    path_out = os.path.join(folder, filename)
    output.to_file(path_out)

    return


if __name__ == "__main__":

    filename = "countries.csv"
    path = os.path.join(BASE_PATH, 'raw', filename)

    countries = pd.read_csv(path, encoding='latin-1')

    for idx, country in countries.iterrows():

        if not country['iso3'] in [#'KEN', 
                                #    'ETH', 'DJI', 'SOM', 
                                   'SSD',
                                #    'MDG'
                                   ]: 
            continue

        run_preprocessing(country)
    
        if country['iso3'] == 'KEN':
            preprocess_supply_data()
