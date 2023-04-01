"""


"""
import os
import configparser
import pandas as pd
import geopandas as gpd
import pyproj
from shapely.ops import transform
from shapely.geometry import shape, Point, mapping, LineString, MultiPolygon
from tqdm import tqdm

from misc import get_countries, get_scenarios, get_regions

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def query_hazard_layers(country, region, scenarios, regional_level):
    """
    Query each hazard layer and estimate fragility.

    """
    iso3 = country['iso3']
    name = country['country']
    gid_level = 'GID_{}'.format(regional_level) #regional_level
    region = region[gid_level]

    for scenario in scenarios: #tqdm(scenarios):

        print('Working on {}'.format(scenario))

        output = []

        scenario_name = os.path.basename(scenario).replace('.tif', '')

        filename = '{}_{}.csv'.format(region, scenario_name)
        folder_out = os.path.join(DATA_PROCESSED, iso3, 'regional_data', region, 'flood_scenarios')
        path_output = os.path.join(folder_out, filename)

        if os.path.exists(path_output):
           continue

        filename = '{}.csv'.format(region)
        folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower())
        path = os.path.join(folder, filename)

        if not os.path.exists(path):
            print('path did not exist: {}'.format(path))
            continue

        sites = pd.read_csv(path)#[:10]

        failures = 0

        for idx, site in sites.iterrows():

            x = float(site['cellid4326'].split('_')[0])
            y = float(site['cellid4326'].split('_')[1])

            with rasterio.open(scenario) as src:

                src.kwargs = {'nodata':255}

                coords = [(x, y)]

                depth = [sample[0] for sample in src.sample(coords)][0]

                if depth < 0:
                    depth = 0

                output.append({
                    'radio': site['radio'],
                    'mcc': site['mcc'],
                    'net': site['net'],
                    'area': site['area'],
                    'cell': site['cell'],
                    'gid_level': gid_level,
                    'gid_id': region,
                    'cellid4326': site['cellid4326'],
                    'cellid3857': site['cellid3857'],
                    'depth': depth,
                })

        if len(output) == 0:
            return

        if not os.path.exists(folder_out):
            os.makedirs(folder_out)

        output = pd.DataFrame(output)

        output.to_csv(path_output, index=False)

    return



if __name__ == "__main__":

    crs = 'epsg:4326'

    countries = get_countries()
    scenarios = get_scenarios()#[:10]

    failed = []

    for idx, country in countries.iterrows():

        # if not country['iso3'] in ['IRL']:
        #     continue
        print('-- {}'.format(country['country']))

        query_hazard_layers(country, get_regions(country, 1), scenarios)


    print('--Complete')
