"""
Visualize at risk infrastructure.

Written by Ed Oughton.

April 2023.

"""
import os
import sys
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
# import rasterio
# from rasterio.mask import mask
import matplotlib.pyplot as plt
# import seaborn as sns
import contextily as cx
# import geopy as gp
# from math import ceil
# import json

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')


def plot_fiber_at_risk(country, outline, dimensions, shapes):
    """
    Plot fiber at risk.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'riverine', 'fiber')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    folder_shapes = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'fiber', 'shapes')
    filenames = os.listdir(folder_shapes)

    for filename in filenames:

        if not ".shp" in filename:
            continue

        print('Working on {}'.format(filename))

        hazard_name = filename.split('_')[0]
        scenario = filename.split('_')[1] #'inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000.shp'
        model = filename.split('_')[2]
        year = filename.split('_')[3]
        probability = filename.split('_')[4].replace('.shp','')

        filename_fiber = 'core_edges_existing.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
        path_fiber = os.path.join(folder, filename_fiber)
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        fiber = fiber[['geometry']]
        fiber_length = fiber.to_crs(3857)
        fiber_length['length_m'] = fiber_length['geometry'].length
        fiber_length_km = round(fiber_length['length_m'].sum()/1e3,0)

        path_at_risk = os.path.join(folder_shapes, filename)
        fiber_at_risk = gpd.read_file(path_at_risk, crs='epsg:3857')
        fiber_at_risk = fiber_at_risk[['geometry']]
        fiber_at_risk = fiber_at_risk.to_crs(4326)
        flooded_length_km = fiber_at_risk.to_crs(3857)
        flooded_length_km['length_m'] = flooded_length_km['geometry'].length
        flooded_length_km = int(round(flooded_length_km['length_m'].sum()/1e3,0))

        # filename = 'inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
        path_hazard = os.path.join(folder, filename)
        hazard = gpd.read_file(path_hazard, crs='epsg:3857')
        hazard = hazard[['geometry']]

        fig, ax = plt.subplots(1, 1, figsize=dimensions)
        fig.subplots_adjust(hspace=.3, wspace=.1)
        fig.set_facecolor('gainsboro')

        minx, miny, maxx, maxy = outline.total_bounds
        buffer = 2
        ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
        ax.set_ylim(miny-0.1, maxy+.1)

        fig.set_facecolor('gainsboro')

        fiber.plot(color='black',ax=ax, linewidth=1, alpha=1, legend=True)

        fiber_at_risk.plot(color='red', ax=ax, linewidth=1.2, alpha=1, legend=True)

        hazard.plot(color='blue', ax=ax, linewidth=1, alpha=.5, legend=True)

        outline.plot(facecolor="none", edgecolor='grey', lw=1, ax=ax)

        cx.add_basemap(ax, crs='epsg:4326')

        fig.tight_layout()
        flooded_length_perc = round(flooded_length_km / fiber_length_km * 100, 2)
        main_title = 'Fiber At Risk: {}, {}, {}, {}, 2080. ({} percent affected - {} km)'.format(name, hazard_name, scenario, probability, flooded_length_perc, flooded_length_km)
        plt.suptitle(main_title, fontsize=14, y=1.02, wrap=True)

        path_out = os.path.join(folder_vis, filename.replace('.shp','.png'))

        plt.savefig(path_out,
            pad_inches=0.4,
            bbox_inches='tight',
            dpi=600,
        )
        plt.close()


def plot_roads_at_risk(country, outline, dimensions, shapes):
    """
    Plot roads at risk.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'riverine', 'roads')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    folder_scenarios = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'roads', 'shapes')
    scenarios = os.listdir(folder_scenarios)

    for scenario in scenarios:

        print('Working on {}'.format(scenario))

        folder_shapes = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'roads', 'shapes', scenario)
        filenames = os.listdir(folder_shapes)#[:5]

        roads_at_risk = pd.DataFrame()

        for filename in filenames:

            if not ".shp" in filename:
                continue

            hazard_name = filename.split('_')[0]
            climate_scenario = filename.split('_')[1] #'inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000.shp'
            model = filename.split('_')[2]
            year = filename.split('_')[3]
            probability = filename.split('_')[4].replace('.shp','')

            # filename_fiber = 'core_edges_existing.shp'
            # folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
            # path_fiber = os.path.join(folder, filename_fiber)
            # fiber = gpd.read_file(path_fiber, crs='epsg:4326')
            # fiber = fiber[['geometry']]
            # fiber_length = fiber.to_crs(3857)
            # fiber_length['length_m'] = fiber_length['geometry'].length
            # fiber_length_km = round(fiber_length['length_m'].sum()/1e3,0)

            path_at_risk = os.path.join(folder_shapes, filename)
            data = gpd.read_file(path_at_risk, crs='epsg:3857')
            data = data[['geometry']]
            data = data.to_crs(4326)
            roads_at_risk = pd.concat([roads_at_risk, data])

        flooded_length_km = roads_at_risk.to_crs(3857)
        flooded_length_km['length_m'] = flooded_length_km['geometry'].length
        flooded_length_km = int(round(flooded_length_km['length_m'].sum()/1e3,0))

        # filename = 'inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
        path_hazard = os.path.join(folder, scenario + '.shp')
        hazard = gpd.read_file(path_hazard, crs='epsg:3857')
        hazard = hazard[['geometry']]

        fig, ax = plt.subplots(1, 1, figsize=dimensions)
        fig.subplots_adjust(hspace=.3, wspace=.1)
        fig.set_facecolor('gainsboro')

        minx, miny, maxx, maxy = outline.total_bounds
        buffer = 2
        ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
        ax.set_ylim(miny-0.1, maxy+.1)

        fig.set_facecolor('gainsboro')

        # fiber.plot(color='black',ax=ax, linewidth=1, alpha=1, legend=True)

        roads_at_risk.plot(color='red', ax=ax, linewidth=1.2, alpha=1, legend=True)

        hazard.plot(color='blue', ax=ax, linewidth=1, alpha=.5, legend=True)

        outline.plot(facecolor="none", edgecolor='grey', lw=1, ax=ax)

        cx.add_basemap(ax, crs='epsg:4326')

        fig.tight_layout()

        road_length_km = 133608
        flooded_length_perc = round(flooded_length_km / road_length_km * 100, 2)
        main_title = 'Roads At Risk: {}, {}, {}, {}, 2080. ({} percent affected - {} km)'.format(name, hazard_name, climate_scenario, probability, flooded_length_perc, flooded_length_km)
        plt.suptitle(main_title, fontsize=14, y=1.02, wrap=True)

        filename_out = "{}_{}_{}_{}_{}.png".format(hazard_name, climate_scenario, model, year, probability)
        path_out = os.path.join(folder_vis, filename_out)

        plt.savefig(path_out,
            pad_inches=0.4,
            bbox_inches='tight',
            dpi=600,
        )
        plt.close()


def plot_cells_at_risk(country, outline, dimensions, shapes):
    """
    Plot cells at risk.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'riverine', 'cells')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    folder_cells = os.path.join(DATA_PROCESSED, iso3, 'results', 'inunriver', 'cells', 'step1')
    filenames = os.listdir(folder_cells)

    for filename in filenames:

        print('Working on {}'.format(filename))

        hazard_name = filename.split('_')[0]
        climate_scenario = filename.split('_')[1]
        model = filename.split('_')[2]
        year = filename.split('_')[3]
        probability = filename.split('_')[4].replace('.csv','')

        # filename_fiber = 'core_edges_existing.shp'
        # folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
        # path_fiber = os.path.join(folder, filename_fiber)
        # fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        # fiber = fiber[['geometry']]
        # fiber_length = fiber.to_crs(3857)
        # fiber_length['length_m'] = fiber_length['geometry'].length
        # fiber_length_km = round(fiber_length['length_m'].sum()/1e3,0)

        path_at_risk = os.path.join(folder_cells, filename)
        all_data = pd.read_csv(path_at_risk)#[:10]

        cells_at_risk = []

        for idx, row in all_data.iterrows():

            x, y = row['cellid4326'].split('_')

            cells_at_risk.append({
                'geometry': {
                    'type': 'Point',
                    'coordinates': (float(x), float(y))
                },
                'properties': {
                    'radio': row['radio']
                }
            })

        cells_at_risk = gpd.GeoDataFrame.from_features(cells_at_risk, crs='epsg:4326')

        # filename = 'inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
        path_hazard = os.path.join(folder, filename.replace('.csv', '') + '.shp')
        hazard = gpd.read_file(path_hazard, crs='epsg:3857')
        hazard = hazard[['geometry']]

        fig, ax = plt.subplots(1, 1, figsize=dimensions)
        fig.subplots_adjust(hspace=.3, wspace=.1)
        fig.set_facecolor('gainsboro')

        minx, miny, maxx, maxy = outline.total_bounds
        buffer = 2
        ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
        ax.set_ylim(miny-0.1, maxy+.1)

        fig.set_facecolor('gainsboro')

        # # fiber.plot(color='black',ax=ax, linewidth=1, alpha=1, legend=True)

        cells_at_risk.plot(color='red', ax=ax, linewidth=.2, alpha=1, legend=True)

        hazard.plot(color='blue', ax=ax, linewidth=1, alpha=.5, legend=True)

        outline.plot(facecolor="none", edgecolor='grey', lw=1, ax=ax)

        cx.add_basemap(ax, crs='epsg:4326')

        fig.tight_layout()

        cell_count = country['cell_count']
        cells_at_risk_perc = round(len(cells_at_risk) / cell_count * 100, 2)
        main_title = 'Cells At Risk: {}, {}, {}, {}, 2080. ({} percent affected - {} cells)'.format(name, hazard_name, climate_scenario, probability, cells_at_risk_perc, len(cells_at_risk))
        plt.suptitle(main_title, fontsize=14, y=1.02, wrap=True)

        filename_out = "{}_{}_{}_{}_{}.png".format(hazard_name, climate_scenario, model, year, probability)
        path_out = os.path.join(folder_vis, filename_out)

        plt.savefig(path_out,
            pad_inches=0.4,
            bbox_inches='tight',
            dpi=600,
        )
        plt.close()


if __name__ == '__main__':

    filename = 'countries.csv'
    path = os.path.join(DATA_RAW, filename)
    countries = pd.read_csv(path, encoding='latin-1')

    for idx, country in countries.iterrows():

        if not country['iso3'] in ['KEN']:#, 'KEN']: #['KEN']
            continue

        dimensions = (int(country['dimensions_y']), int(country['dimensions_x']))

        iso3 = country['iso3']
        # country['figsize'] = (8,10)

        print('-- {} --'.format(iso3))

        if not os.path.exists(VIS):
            os.makedirs(VIS)

        filename = 'regions_{}_{}.shp'.format(country['lowest'], iso3)
        path = os.path.join(DATA_PROCESSED, iso3, 'regions', filename)
        shapes = gpd.read_file(path, crs='epsg:4326')

        filename = 'national_outline.shp'
        path = os.path.join(DATA_PROCESSED, iso3, filename)
        outline = gpd.read_file(path, crs='epsg:4326')

        # plot_fiber_at_risk(country, outline, dimensions, shapes)

        # plot_roads_at_risk(country, outline, dimensions, shapes)

        plot_cells_at_risk(country, outline, dimensions, shapes)
