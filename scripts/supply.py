"""
Visualize supply-side metrics.

Written by Ed Oughton.

May 2023

"""
import os
# import sys
import configparser
# import numpy as np
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

from misc import get_countries

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
# RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')
REPORTS = os.path.join(BASE_PATH, '..', 'reports', 'images')


def plot_fiber(country, outline):
    """
    Plot fiber data.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'supply')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    dimensions = (int(country['dimensions_x']), int(country['dimensions_y']))
    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = country['buffer']
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'country_data')
    path_fiber = os.path.join(folder, filename)
    if os.path.exists(path_fiber):
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        if iso3 in ['ETH','DJI','SOM','SSD','MDG']:
            live = fiber[fiber['status'].isin(['Live','Needs Upgrading'])]
            if len(live) > 0:
                live.plot(color='orange', legend=True, lw=1.5, ax=ax)
            planned = fiber[fiber['status'].isin(['Planned','Inactive'])]
            if len(planned) > 0:
                planned.plot(color='yellow', legend=True, lw=1.5, ax=ax)

        if iso3 == 'KEN':
            filename = 'From road to NOFBI.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
            path_fiber = os.path.join(folder, filename)
            fiber1 = gpd.read_file(path_fiber, crs='epsg:3857')
            fiber1 = fiber1.to_crs(4326)
            fiber1['status'] = 'Planned'
            fiber1 = fiber1[['geometry', 'status']]
            fiber1.plot(color='yellow', legend=True, lw=1.5, ax=ax)

            filename = 'core_edges_existing.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'afterfibre')
            path_fiber = os.path.join(folder, filename)
            fiber2 = gpd.read_file(path_fiber, crs='epsg:4326')
            fiber2['status'] = 'Live'
            fiber2 = fiber2[['geometry', 'status']]
            fiber2.plot(color='orange', legend=True, lw=1.5, ax=ax)

    outline.plot(linewidth=.5, alpha=1, facecolor="none", 
        legend=True, edgecolor='grey', ax=ax)
    
    if iso3 in ['ETH', 'KEN','SSD']:
        ilemi_path = os.path.join(BASE_PATH, 'raw', 'ILEMI_TRIANGLE.shp')
        ilemi_triangle = gpd.read_file(ilemi_path, crs='epsg:4326')
        ilemi_triangle.plot(ax=ax, edgecolor='grey', linestyle='dashed', linewidth=2, facecolor='none')

    # if iso3 in ['SOM']:
    #     somaliland_path = os.path.join(BASE_PATH, 'raw', 'somaliland.shp')
    #     somaliland = gpd.read_file(somaliland_path, crs='epsg:4326')
    #     somaliland.plot(ax=ax, edgecolor='lightgrey',  facecolor='lightgrey', zorder=10)

    zoom_level = 7
    if iso3 == 'DJI':
        zoom_level = 9
    cx.add_basemap(ax, crs='epsg:4326', rasterized=True, zoom=zoom_level)

    plt.legend(
        ['Live Fiber', 'Planned Fiber'], 
        loc='lower right',
        title='Assets'
    )

    fig.tight_layout()

    main_title = 'Fiber Optic Network'
    plt.suptitle(main_title, fontsize=20, y=1.02, wrap=True)

    path_out = os.path.join(folder_vis, 'fiber.png')

    fig.set_size_inches(dimensions)
    plt.savefig(path_out,
        pad_inches=0.4,
        bbox_inches='tight',
        dpi=600 
    )
    plt.close()


def plot_cells(country, outline):
    """
    Plot cells.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'supply')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    dimensions = (int(country['dimensions_x']), int(country['dimensions_y']))
    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = country['buffer']
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    outline.plot(linewidth=.5, alpha=1, facecolor="none", 
        legend=True, edgecolor='grey', ax=ax)
    
    zoom_level = 7
    if iso3 == 'DJI':
        zoom_level = 9
    cx.add_basemap(ax, crs='epsg:4326', rasterized=True, zoom=zoom_level)

    # if iso3 in ['SOM']:
    #     somaliland_path = os.path.join(BASE_PATH, 'raw', 'somaliland.shp')
    #     somaliland = gpd.read_file(somaliland_path, crs='epsg:4326')
    #     somaliland.plot(ax=ax, edgecolor='lightgrey',  facecolor='lightgrey', zorder=10)

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

    if iso3 in ['ETH', 'KEN','SSD']:
        ilemi_path = os.path.join(BASE_PATH, 'raw', 'ILEMI_TRIANGLE.shp')
        ilemi_triangle = gpd.read_file(ilemi_path, crs='epsg:4326')
        ilemi_triangle.plot(ax=ax, edgecolor='grey', linestyle='dashed', linewidth=2, facecolor='none')

    plt.legend(
        ['2G GSM', '3G UMTS', '4G LTE', '5G NR'], 
        loc='lower right',
        title='Assets'
    )

    fig.tight_layout()

    main_title = 'Crowdsourced Mobile Cell Locations'
    plt.suptitle(main_title, fontsize=20, y=1.02, wrap=True)

    path_out = os.path.join(folder_vis, 'cells.png')

    fig.set_size_inches(dimensions)
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

    for idx, country in countries.iterrows(): #, total=countries.shape[0]):

        if not country['iso3'] in [
            # 'KEN', 
            # 'ETH', 
            # 'DJI',
            'SOM', 
            # 'SSD', 
            # 'MDG'
            ]:
            continue

        iso3 = country['iso3']

        print('-- {} --'.format(country['iso3']))

        folder_reports = os.path.join(REPORTS, iso3)
        if not os.path.exists(folder_reports):
            os.makedirs(folder_reports)

        filename = 'regions_{}_{}.shp'.format(country['gid_region'], iso3)
        path = os.path.join(DATA_PROCESSED, iso3, 'regions', filename)
        shapes = gpd.read_file(path, crs='epsg:4326')

        filename = 'national_outline.shp'
        path = os.path.join(DATA_PROCESSED, iso3, filename)
        outline = gpd.read_file(path, crs='epsg:4326')

        print('Plotting plot_fiber')
        plot_fiber(country, outline)

        print('Plotting plot_cells')
        plot_cells(country, outline)
