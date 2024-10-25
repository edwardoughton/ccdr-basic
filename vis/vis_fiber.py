"""
Visualize estimated damage costs.

Written by Ed Oughton.

April 2023

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


def plot_inunriver_costs_map(country, outline, dimensions, shapes):
    """
    Plot river damage costs by region.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'riverine')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
    path_fiber = os.path.join(folder, filename)
    fiber = gpd.read_file(path_fiber, crs='epsg:4326')
    fiber = fiber[['geometry']]
    fiber_length = fiber.to_crs(3857)
    fiber_length['length_m'] = fiber_length['geometry'].length
    fiber_length_km = round(fiber_length['length_m'].sum()/1e3,0)

    filename = 'mean_regional_direct_costs.csv'
    folder =  os.path.join(VIS, '..', 'data', iso3)
    path = os.path.join(folder, filename)

    data = pd.read_csv(path)

    scenarios = data['climatescenario'].unique()
    probabilities = data['probability'].unique()

    for scenario in scenarios:
        for probability in probabilities:

            subset = data[
                (data['climatescenario'] == scenario) &
                (data['probability'] == probability)
            ]

            shapes_data = pd.merge(
                    shapes, subset, on="GID_1", how="left",
                )
            shapes_data = shapes_data.fillna(0)

            fig, ax = plt.subplots(1, 1, figsize=dimensions)
            fig.subplots_adjust(hspace=.3, wspace=.1)
            fig.set_facecolor('gainsboro')

            minx, miny, maxx, maxy = outline.total_bounds
            buffer = 2
            ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
            ax.set_ylim(miny-0.1, maxy+.1)

            fig.set_facecolor('gainsboro')

            shapes_data['bin'] = pd.qcut(shapes_data["cost_usd_baseline"]/1e6, q=5)

            # bins = [-10,.25,.5,.75,1,1.25,1.5,1.75,2,2.25, 1e12]
            # labels = ['<$0.25m','$0.5m','$0.75m','$1m','$1.25m','$1.5m','$1.75m','$2m','$2.25m','>$2.5m']

            # shapes_data['bin'] = pd.cut(
            #     shapes_data["cost_usd_baseline"]/1e6,
            #     bins=bins,
            #     labels=labels
            # )#.astype(str)

            base = shapes_data.plot(column='bin', ax=ax, cmap='viridis',
                linewidth=.5, alpha=0.5, legend=True, antialiased=False)
            outline.plot(facecolor="none", edgecolor='grey', lw=1, ax=ax)
            cx.add_basemap(ax, crs='epsg:4326')

            fig.tight_layout()
            flooded_length_km = round(subset['length_m'].sum() / 1e3)

            flooded_length_perc = round(flooded_length_km / fiber_length_km * 100, 2)

            main_title = 'Estimated Direct Damage to Fiber Assets from Projected Riverine Flooding: {}, {}, {} annual probability, 2080 (US$ Millions). Estimates based on {} percent of fiber affected, equating to {} km at risk'.format(name, scenario, probability, flooded_length_perc, flooded_length_km)
            plt.suptitle(main_title, fontsize=20, y=1.02, wrap=True)

            path_out = os.path.join(folder_vis, 'inunriver_{}_model-average_{}.png'.format(scenario, probability))

            plt.savefig(path_out,
                pad_inches=0.4,
                bbox_inches='tight',
                dpi=600,
            )
            plt.close()


if __name__ == '__main__':

    filename = 'countries.csv'
    path = os.path.join(BASE_PATH, 'raw', filename)
    countries = pd.read_csv(path, encoding='latin-1')

    for idx, country in countries.iterrows():

        if not country['iso3'] in [
            'KEN', 
            'ETH', 
            'DJI', 
            'SOM', 
            'SSD', 
            'MDG' 
            ]:
            continue

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

        plot_inunriver_costs_map(country, outline, dimensions, shapes)

        # barplot_inunriver_costs(country, outline, dimensions, shapes)
