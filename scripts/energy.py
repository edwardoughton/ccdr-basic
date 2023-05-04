"""
Process energy.

"""
import os
import configparser
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping, MultiLineString
import fiona

from misc import get_countries

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def process_energy(country):
    """
    Load and process existing energy data.

    """
    iso3 = country['iso3']
    iso2 = country['iso2'].lower()

    folder = os.path.join(DATA_PROCESSED, iso3, 'energy')
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = 'power-lines-existing.shp'
    path_output = os.path.join(folder, filename)

    path = os.path.join(DATA_RAW, 'osm', country['iso3'], 'power-lines-existing.shp')
    data = gpd.read_file(path, crs='epsg:4326')

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


if __name__ == '__main__':

    countries = get_countries()

    for idx, country in countries.iterrows():

        # if country['iso3'] in ['KEN']:
        #     process_existing_fiber(country)

        if country['iso3'] in ['AZE']:
            process_energy(country)
