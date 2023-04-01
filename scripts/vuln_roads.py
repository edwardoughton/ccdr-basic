"""
Intersection of road routes with hazard layers.

Written by Ed Oughton.

March 2023.

"""
import os
import sys
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
# from rasterio.mask import mask
# import matplotlib.pyplot as plt
# import seaborn as sns
# import contextily as cx
# import geopy as gp
# from math import ceil
import json

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def process_existing_roads(country):
    """
    Load and process existing fiber data.

    """
    iso3 = country['iso3']
    iso2 = country['iso2'].lower()
    gid_id = 'GID_{}'.format(country['gid_region'])

    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    filename = 'regions_{}_{}.shp'.format(country['gid_region'], iso3)
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')
    region_ids = regions[gid_id].unique()

    path_in = os.path.join(DATA_RAW, 'osm', iso3, 'gis_osm_roads_free_1.shp')
    folder_roads = os.path.join(DATA_PROCESSED, iso3, 'roads')
    if not os.path.exists(folder_roads):
        os.makedirs(folder_roads)

    roads = gpd.read_file(path_in, crs='epsg:4326')

    for region in region_ids:

        filename = '{}.shp'.format(region)
        path_output = os.path.join(folder_roads, filename)

        # if os.path.exists(path_output):
        #     return print('Existing road shape already processed')

        subset_region = regions[regions[gid_id] == region]

        #intersect fiber with hazard.
        roads_subset = roads.overlay(subset_region, how='intersection', keep_geom_type=True)

        if len(roads) == 0:
            continue

        roads_subset.to_file(path_output, crs='epsg:4326')

    return


def intersect_hazard(country, hazard_type):
    """
    Intersect infrastructure with hazards.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_id = 'GID_{}'.format(country['gid_region'])

    filename = 'regions_{}_{}.shp'.format(gid_region, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')
    region_ids = regions[gid_id].unique()

    folder_hazards = os.path.join(DATA_PROCESSED, iso3, 'hazards', hazard_type)
    hazard_filenames = os.listdir(folder_hazards)

    output = []

    for hazard_filename in hazard_filenames:

        if not ".shp" in hazard_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in hazard_filename:
        #     continue

        print("Working on {}, {}".format(hazard_filename, hazard_type))

        for region in region_ids:

            print("-- {}".format(region))

            filename = '{}.shp'.format(region)
            folder = os.path.join(DATA_PROCESSED, iso3, 'roads')
            path_roads = os.path.join(folder, filename)
            roads = gpd.read_file(path_roads, crs='epsg:4326')
            roads = roads[['geometry']]
            roads_length = roads.to_crs(3857)
            roads_length['length_m'] = roads_length['geometry'].length
            roads_length_m = round(roads_length['length_m'].sum())

            path_hazard = os.path.join(folder_hazards, hazard_filename)
            hazard_layer = gpd.read_file(path_hazard, crs='epsg:4326')

            #intersect roads with hazard.
            roads = roads.overlay(hazard_layer, how='intersection', keep_geom_type=True) #, make_valid=True

            #intersect roads with regional layer to provide GID id.
            roads = roads.overlay(regions, how='intersection', keep_geom_type=True) #, make_valid=True

            roads = roads.to_crs(3857)
            roads['length_m'] = roads['geometry'].length
            roads = roads.to_crs(4326)
            roads['total_m'] = roads_length_m

            results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'roads', 'shapes', hazard_filename.replace('.shp', ''))
            if not os.path.exists(results_folder):
                os.makedirs(results_folder)
            path_out = os.path.join(results_folder, region + "_" + hazard_filename)
            roads.to_file(path_out)

            to_csv = roads[['GID_1', 'length_m', 'total_m']]
            results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'roads', 'csv_files', hazard_filename.replace('.shp', ''))
            if not os.path.exists(results_folder):
                os.makedirs(results_folder)
            path_out = os.path.join(results_folder, region + "_" + hazard_filename.replace('.shp', '.csv'))
            to_csv.to_csv(path_out)

    return


def collect_data(country, hazard_type):
    """
    Collect data by region.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)
    gid_id = 'GID_{}'.format(country['gid_region'])

    # filename = 'regions_{}_{}.shp'.format(gid_region, iso3)
    # folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    # path_regions = os.path.join(folder, filename)
    # regions = gpd.read_file(path_regions, crs='epsg:4326')
    # region_ids = regions[gid_id].unique()

    filename = 'fragility_curve.csv'
    path_fragility = os.path.join(DATA_RAW, filename)
    low, baseline, high = load_f_curves(path_fragility)

    # scenarios = set()

    folder_in = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'roads', 'shapes')
    if not os.path.exists(folder_in):
        return
    scenario_folders = os.listdir(folder_in)

    for scenario in scenario_folders:

        print("Working on {}".format(scenario))

        road_shapes = os.listdir(os.path.join(folder_in, scenario))

        output = []

        for road_filename in road_shapes:

            if not ".shp" in road_filename:
                continue

            path_road = os.path.join(folder_in, scenario, road_filename)

            roads = gpd.read_file(path_road, crs='epsg:4326')

            for idx, road_row in roads.iterrows():

                damage_low = query_fragility_curve(low, road_row['value'])
                damage_baseline = query_fragility_curve(baseline, road_row['value'])
                damage_high = query_fragility_curve(high, road_row['value'])

                output.append({
                    gid_level: road_row[gid_level],
                    'depth_m': road_row['value'],
                    'length_m': road_row['length_m'],
                    'total_m': road_row['total_m'],
                    'damage_low': damage_low,
                    'damage_baseline': damage_baseline,
                    'damage_high': damage_high,
                    'cost_usd_low': round(road_row['length_m'] * country['fiber_cost_usd_m'] * damage_low),
                    'cost_usd_baseline':  round(road_row['length_m'] * country['fiber_cost_usd_m'] * damage_baseline),
                    'cost_usd_high':  round(road_row['length_m'] * country['fiber_cost_usd_m'] * damage_high),
                })

        if len(output) == 0:
            continue

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type,  'roads', 'long_form')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, scenario + '.csv')

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'roads', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, scenario + '.csv')
        output = output[[gid_level, "length_m", "total_m", "cost_usd_low", "cost_usd_baseline","cost_usd_high"]]
        output = output.groupby([gid_level], as_index=False).sum()
        output.to_csv(path_out, index=False)

    return


def load_f_curves(path_fragility):
    """
    Load depth-damage curves.

    """
    low = []
    baseline = []
    high = []

    f_curves = pd.read_csv(path_fragility)

    for idx, item in f_curves.iterrows():

        my_dict = {
            'depth_lower_m': item['depth_lower_m'],
            'depth_upper_m': item['depth_upper_m'],
            'damage': item['damage'],
        }

        if item['scenario'] == 'low':
            low.append(my_dict)
        elif item['scenario'] == 'baseline':
            baseline.append(my_dict)
        elif item['scenario'] == 'high':
            high.append(my_dict)

    return low, baseline, high


def query_fragility_curve(f_curve, depth):
    """
    Query the fragility curve.

    """
    if depth < 0:
        return 0

    for item in f_curve:
        if item['depth_lower_m'] <= depth < item['depth_upper_m']:
            return item['damage']
        else:
            continue

    if depth >= max([d['depth_upper_m'] for d in f_curve]):
        return 1

    print('fragility curve failure: {}'.format(depth))

    return 0


if __name__ == '__main__':

    filename = 'countries.csv'
    path = os.path.join(DATA_RAW, filename)
    countries = pd.read_csv(path, encoding='latin-1')

    hazard_types = [
        'inunriver',
        # 'inuncoast'
    ]

    for idx, country in countries.iterrows():

        if not country['iso3'] in ['AZE']:#, 'KEN']: #,'KEN']: #['KEN'] #
            continue

        # process_existing_roads(country)

        for hazard_type in hazard_types:

            print('-- {}: {} --'.format(country['iso3'], hazard_type))

            # intersect_hazard(country, hazard_type)

            collect_data(country, hazard_type)
