"""
Visualize unconnected population to hazards.

Written by Ed Oughton.

May 4th 2022

"""
import os
import sys
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as cx
import geopy as gp
from math import ceil
import json

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')
REPORTS = os.path.join(BASE_PATH, '..', 'reports', 'images')



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


def plot_inunriver_uncovered(country, outline, dimensions,
    scenarios, models, return_periods):
    """
    Plot river uncovered population by region.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'riverine')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    for scenario in scenarios:
        for model in models:
            for rp in return_periods:

                fig, ax = plt.subplots(1, 1, figsize=dimensions)
                fig.subplots_adjust(hspace=.3, wspace=.1)
                fig.set_facecolor('gainsboro')

                minx, miny, maxx, maxy = outline.total_bounds
                buffer = 2
                ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
                ax.set_ylim(miny-0.1, maxy+.1)

                fig.set_facecolor('gainsboro')

                folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
                filename = 'inunriver_{}_{}_2080_{}.shp'.format(scenario, model, rp)
                path1 = os.path.join(folder, filename)
                if os.path.exists(path1):
                    hazard = gpd.read_file(path1, crs='epsg:3857')
                    hazard = hazard.to_crs(4326)
                    hazard.plot(color='black', linewidth=1.5, alpha=.5,
                        legend=True, edgecolor='black', ax=ax)
                    cx.add_basemap(ax, crs='epsg:4326')

                filename = 'core_edges_existing.shp'
                folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
                path_fiber = os.path.join(folder, filename)
                if os.path.exists(path_fiber):
                    fiber = gpd.read_file(path_fiber, crs='epsg:4326')
                    fiber.plot(color='orange', lw=1.5, ax=ax)

                filename = '{}.csv'.format(iso3)
                folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
                path_sites = os.path.join(folder, filename)
                sites = pd.read_csv(path_sites, encoding='latin-1')

                sites = gpd.GeoDataFrame(
                    sites,
                    geometry=gpd.points_from_xy(
                        sites.lon,
                        sites.lat
                    ), crs='epsg:4326'
                )

                sites = sites[['radio', 'geometry']]
                gsm = sites.loc[sites['radio'] == 'GSM']
                umts = sites.loc[sites['radio'] == 'UMTS']
                lte = sites.loc[sites['radio'] == 'LTE']
                nr = sites.loc[sites['radio'] == 'NR']

                gsm.plot(color='red', markersize=3, ax=ax, legend=True)
                umts.plot(color='blue', markersize=3, ax=ax, legend=True)
                lte.plot(color='yellow', markersize=3, ax=ax, legend=True)
                if len(nr) > 0:
                    nr.plot(color='black', markersize=3, ax=ax, legend=True)

                plt.legend(
                    ['Fiber', '2G GSM', '3G UMTS', '4G LTE', '5G NR' ],
                    loc='lower right',
                    title='Assets'
                )

                fig.tight_layout()

                main_title = 'Projected River Flooding: {}, {}, {}, {}, 2080'.format(name, scenario, model, rp)
                plt.suptitle(main_title, fontsize=20, y=1.03, wrap=True)

                path_out = os.path.join(folder_vis, 'inunriver_{}_{}_{}.png'.format(scenario, model, rp))

                plt.savefig(path_out,
                    pad_inches=0.4,
                    bbox_inches='tight',
                    dpi=600,
                )
                plt.close()


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

    return_periods = [
        'rp01000',
        'rp00500',
        'rp00100',
        'rp00050',
        'rp00025'
    ]

    filename = 'countries.csv'
    path = os.path.join(BASE_PATH, 'raw', filename)
    countries = pd.read_csv(path, encoding='latin-1')

    for idx, country in countries.iterrows():

        if not country['iso3'] in ['COD']:#, 'KEN']: #['KEN']
            continue

        print('processing rivers')
        process_inunriver(country, scenarios, models, return_periods) #river flooding

        print('extracting rivers')
        extract_inunriver(country, scenarios, models, return_periods)

        dimensions = (int(country['dimensions_y']), int(country['dimensions_x']))
        iso3 = country['iso3']
        country['figsize'] = (8,10)

        print('-- {} --'.format(iso3))

        folder_reports = os.path.join(REPORTS, iso3)
        if not os.path.exists(folder_reports):
            os.makedirs(folder_reports)

        filename = 'regions_{}_{}.shp'.format(country['gid_region'], iso3)
        path = os.path.join(DATA_PROCESSED, iso3, 'regions', filename)
        shapes = gpd.read_file(path, crs='epsg:4326')

        filename = 'national_outline.shp'
        path = os.path.join(DATA_PROCESSED, iso3, filename)
        outline = gpd.read_file(path, crs='epsg:4326')

        plot_inunriver_uncovered(country, outline, dimensions, scenarios, models, return_periods)
