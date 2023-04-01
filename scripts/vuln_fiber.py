"""
Intersection of fiber routes with hazard layers.

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
import fiona
from shapely.geometry import MultiLineString, mapping
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


def process_existing_fiber(country):
    """
    Load and process existing fiber data.

    """
    iso3 = country['iso3']
    iso2 = country['iso2'].lower()

    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = 'core_edges_existing.shp'
    path_output = os.path.join(folder, filename)

    # if os.path.exists(path_output):
    #     return print('Existing fiber already processed')

    path = os.path.join(DATA_RAW, 'afterfiber', 'afterfiber.shp')

    shapes = fiona.open(path)

    data = []

    for item in shapes:
        if item['properties']['iso2'] == iso2:
            if item['geometry']['type'] == 'LineString':
                if int(item['properties']['live']) == 1:
                    data.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': item['geometry']['coordinates'],
                        },
                        'properties': {
                            'operators': item['properties']['operator'],
                            'source': 'existing'
                        }
                    })

            if item['geometry']['type'] == 'MultiLineString':
                if int(item['properties']['live']) == 1:

                    for line in list(MultiLineString(item['geometry']['coordinates']).geoms):
                        data.append({
                            'type': 'Feature',
                            'geometry': mapping(line),
                            'properties': {
                                'operators': item['properties']['operator'],
                                'source': 'existing'
                            }
                        })

    if len(data) == 0:
        return print('No existing infrastructure')

    data = gpd.GeoDataFrame.from_features(data)
    data.to_file(path_output, crs='epsg:4326')

    return


def process_itu_data(country):
    """
    Load and process existing fiber data.

    """
    iso3 = country['iso3']
    iso2 = country['iso2'].lower()

    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = 'core_edges_existing.shp'
    path_output = os.path.join(folder, filename)

    path = os.path.join(DATA_RAW, 'itu', 'trx_public_2023-02-26 trx_merged_4326.shp')
    data = gpd.read_file(path, crs='epsg:4326')

    data = data[data['country'] == country['country']]

    data.to_file(path_output, crs='epsg:4326')

    return


def intersect_hazard(country, hazard_type):
    """
    Intersect infrastructure with hazards.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']

    filename = 'regions_{}_{}.shp'.format(gid_region, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')

    folder_hazards = os.path.join(DATA_PROCESSED, iso3, 'hazards', hazard_type)
    hazard_filenames = os.listdir(folder_hazards)#[:5]

    for hazard_filename in hazard_filenames:

        if not ".shp" in hazard_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in hazard_filename:
        #     continue

        print("Working on {}, {}".format(hazard_filename, hazard_type))

        filename = 'core_edges_existing.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
        path_fiber = os.path.join(folder, filename)
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        fiber_length = fiber.to_crs(3857)
        fiber_length['length_m'] = fiber_length['geometry'].length

        path_hazard = os.path.join(folder_hazards, hazard_filename)
        hazard_layer = gpd.read_file(path_hazard, crs='epsg:4326')

        #intersect fiber with hazard.
        fiber = fiber.overlay(hazard_layer, how='intersection', keep_geom_type=True) #, make_valid=True

        #intersect fiber with regional layer to provide GID id.
        fiber = fiber.overlay(regions, how='intersection', keep_geom_type=True) #, make_valid=True

        fiber = fiber.to_crs(3857)
        fiber['length_m'] = fiber['geometry'].length

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'shapes')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, hazard_filename)
        fiber.to_file(path_out)

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber') #, 'csv_files'
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, "fiber_length.csv")
        if os.path.exists(path_out):
            continue
        to_csv = fiber_length[['length_m']] #'GID_1',
        to_csv.to_csv(path_out)

    return


def collect_data(country, hazard_type):
    """
    Collect data by region.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    filename = 'fragility_curve.csv'
    path_fragility = os.path.join(DATA_RAW, filename)
    low, baseline, high = load_f_curves(path_fragility)

    folder_shapes = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'shapes')
    if not os.path.exists(folder_shapes):
        return
    fiber_shapes = os.listdir(folder_shapes)

    for fiber_filename in fiber_shapes:

        if not ".shp" in fiber_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
        #     continue

        print("Working on {}".format(fiber_filename))

        output = []

        path_fiber = os.path.join(folder_shapes, fiber_filename)
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')#[:10]

        for idx, fiber_row in fiber.iterrows():

            damage_low = query_fragility_curve(low, fiber_row['value'])
            damage_baseline = query_fragility_curve(baseline, fiber_row['value'])
            damage_high = query_fragility_curve(high, fiber_row['value'])

            output.append({
                gid_level: fiber_row[gid_level],
                'depth_m': fiber_row['value'],
                'length_m': fiber_row['length_m'],
                # 'total_m': fiber_row['total_m'],
                'damage_low': damage_low,
                'damage_baseline': damage_baseline,
                'damage_high': damage_high,
                'cost_usd_low': round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_low),
                'cost_usd_baseline':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_baseline),
                'cost_usd_high':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_high),
            })

        if len(output) == 0:
            continue

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'csv_files', 'disaggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

        results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'csv_files', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))
        output = output[[gid_level, "length_m", "cost_usd_low", "cost_usd_baseline","cost_usd_high"]]
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


def aggregate_results(country): #, outline, dimensions, shapes):
    """
    Bar plot of river damage costs.

    """
    iso3 = country['iso3']
    name = country['country']
    gid_level = "GID_{}".format(country['gid_region'])

    filename = "fiber_length.csv"
    folder = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'fiber')
    path = os.path.join(folder, filename)
    fiber_length = pd.read_csv(path)
    total_fiber_km = round(fiber_length['length_m'].sum()/1e3)

    folder = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'fiber', 'csv_files', 'aggregated')
    filenames = os.listdir(folder)

    output = []

    for filename in filenames:

        path = os.path.join(folder, filename)

        data = pd.read_csv(path)

        fiber_at_risk_km = round(data['length_m'].sum()/1e3)
        fiber_at_risk_perc = round(fiber_at_risk_km / total_fiber_km * 100, 1)

        hazard_type = filename.split('_')[0]
        scenario = filename.split('_')[1]
        model = filename.split('_')[2]
        year = filename.split('_')[3]
        return_period = filename.split('_')[4]
        return_period = return_period.replace('.csv', '')

        output.append({
            'hazard_type': hazard_type,
            'scenario': scenario,
            'model': model,
            'year': year,
            'return_period': return_period,
            'filename': filename,
            'fiber_at_risk_km': fiber_at_risk_km,
            'total_fiber_km': total_fiber_km,
            'fiber_at_risk_perc': fiber_at_risk_perc
        })

    output = pd.DataFrame(output)

    filename = os.path.join('inunriver_aggregated_results.csv')
    folder = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'fiber', 'csv_files')
    path_out = os.path.join(folder, filename)
    output.to_csv(path_out, index=False)


if __name__ == '__main__':

    filename = 'countries.csv'
    path = os.path.join(DATA_RAW, filename)
    countries = pd.read_csv(path, encoding='latin-1')

    hazard_types = [
        'inunriver',
        # 'inuncoast'
    ]

    for idx, country in countries.iterrows():

        if not country['iso3'] in ['KEN']:#, 'KEN']: #,'KEN']: #['KEN'] #
            continue

        # if country['iso3'] in ['KEN']:
        #     process_existing_fiber(country)

        # if country['iso3'] in ['AZE']:
        #     process_itu_data(country)

        for hazard_type in hazard_types:

            print('-- {}: {} --'.format(country['iso3'], hazard_type))

            intersect_hazard(country, hazard_type)

            collect_data(country, hazard_type)

            aggregate_results(country) #outline, dimensions, shapes)
