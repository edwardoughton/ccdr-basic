"""
Visualize riverine hazard.

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


def plot_landslide(country, outline, dimensions):
    """
    Plot landslide by region.

    """
    iso3 = country['iso3']
    name = country['country']
    z = 7
    if country['iso3'] == 'DJI':
        z = 9
    folder_vis = os.path.join(VIS, iso3, 'landslide')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = 2
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    fig.set_facecolor('gainsboro')

    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
    filename = 'ls_arup.shp'
    path1 = os.path.join(folder, filename)
    if os.path.exists(path1):
        hazard = gpd.read_file(path1, crs='epsg:3857')
        hazard = hazard[hazard['Risk'].isin(['3.0','4.0'])]
        hazard = hazard.to_crs(4326)
        hazard.plot(color='black', linewidth=1.5, alpha=.5,
            legend=True, edgecolor='black', ax=ax)
        cx.add_basemap(ax, crs='epsg:4326', rasterized=True, zoom=7)

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing','country_data')
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

    main_title = 'Landslide Risk Exposure for Medium and High Risk Areas'
    plt.suptitle(main_title, fontsize=20, y=1.03, wrap=True)

    path_out = os.path.join(folder_vis, 'landslide.png')

    plt.savefig(path_out,
        pad_inches=0.4,
        bbox_inches='tight',
        dpi=600,
    )
    plt.close()


def plot_landslide_fiber(country, outline, dimensions):
    """
    Plot landslide by region.

    """
    sources = ['country_data']

    for source in sources:
            
        iso3 = country['iso3']
        name = country['country']
        z = 7
        if country['iso3'] == 'DJI':
            z = 9
        folder_vis = os.path.join(VIS, iso3, 'landslide')
        if not os.path.exists(folder_vis):
            os.makedirs(folder_vis)

        fig, ax = plt.subplots(1, 1, figsize=dimensions)
        fig.subplots_adjust(hspace=.3, wspace=.1)
        fig.set_facecolor('gainsboro')

        minx, miny, maxx, maxy = outline.total_bounds
        buffer = 2
        ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
        ax.set_ylim(miny-0.1, maxy+.1)

        fig.set_facecolor('gainsboro')

        folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
        filename = 'ls_arup.shp'
        path1 = os.path.join(folder, filename)
        if os.path.exists(path1):
            hazard = gpd.read_file(path1, crs='epsg:3857')
            hazard = hazard[hazard['Risk'].isin(['3.0','4.0'])]
            hazard = hazard.to_crs(4326)
            hazard.plot(color='black', linewidth=1.5, alpha=.5,
                legend=True, edgecolor='black', ax=ax)
            cx.add_basemap(ax, crs='epsg:4326', rasterized=True, zoom=7)

        filename = 'core_edges_existing.shp'
        folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', source)
        path_fiber = os.path.join(folder, filename)
        if os.path.exists(path_fiber):
            fiber = gpd.read_file(path_fiber, crs='epsg:4326')
            planned = fiber[fiber['live'] == 'planned']
            if len(planned) > 0:            
                planned.plot(color='yellow', legend=True, lw=1.5, ax=ax) 
            live = fiber[fiber['live'] == 'live']
            live.plot(color='orange', legend=True, lw=1.5, ax=ax) 
        else:
            print('path did not exist: {}'.format(path_fiber))
        
        if len(planned) > 0: 
            legend = ['Planned', 'Live']
        else:
            legend = ['Live']
        plt.legend(legend, loc='lower right', title='Assets')

        fig.tight_layout()

        main_title = 'Landslide Risk Exposure for Medium and High Risk Areas'
        plt.suptitle(main_title, fontsize=20, y=1.03, wrap=True)

        filename = 'landslide_fiber_{}.png'.format(source)
        path_out = os.path.join(folder_vis, filename)

        plt.savefig(path_out,
            pad_inches=0.4,
            bbox_inches='tight',
            dpi=600,
        )
        plt.close()


def plot_landslide_cells(country, outline, dimensions):
    """
    Plot landslide by region.

    """
    iso3 = country['iso3']
    name = country['country']
    z = 7
    if country['iso3'] == 'DJI':
        z = 9
    folder_vis = os.path.join(VIS, iso3, 'landslide')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = 2
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    fig.set_facecolor('gainsboro')

    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'landslide')
    filename = 'ls_arup.shp'
    path1 = os.path.join(folder, filename)
    if os.path.exists(path1):
        hazard = gpd.read_file(path1, crs='epsg:3857')
        hazard = hazard[hazard['Risk'].isin(['3.0','4.0'])]
        hazard = hazard.to_crs(4326)
        hazard.plot(color='black', linewidth=1.5, alpha=.5,
            legend=True, edgecolor='black', ax=ax)
        cx.add_basemap(ax, crs='epsg:4326', rasterized=True, zoom=7)

    # filename = 'core_edges_existing.shp'
    # folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
    # path_fiber = os.path.join(folder, filename)
    # if os.path.exists(path_fiber):
    #     fiber = gpd.read_file(path_fiber, crs='epsg:4326')
    #     fiber.plot(color='orange', lw=1.5, ax=ax)

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

    gsm.plot(color='red', markersize=1, ax=ax, legend=True)
    umts.plot(color='blue', markersize=1, ax=ax, legend=True)
    lte.plot(color='yellow', markersize=1, ax=ax, legend=True)
    if len(nr) > 0:
        nr.plot(color='black', markersize=1, ax=ax, legend=True)

    plt.legend(
        ['2G GSM', '3G UMTS', '4G LTE', '5G NR' 
        ],
        loc='lower right',
        title='Assets'
    )

    fig.tight_layout()

    main_title = 'Landslide Risk Exposure for Medium and High Risk Areas'
    plt.suptitle(main_title, fontsize=20, y=1.03, wrap=True)

    path_out = os.path.join(folder_vis, 'landslide_cells.png')

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

        dimensions = (int(country['dimensions_x']), int(country['dimensions_y']))
        iso3 = country['iso3']
        country['figsize'] = dimensions

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

        plot_landslide(country, outline, dimensions)

        plot_landslide_fiber(country, outline, dimensions)

        plot_landslide_cells(country, outline, dimensions)
