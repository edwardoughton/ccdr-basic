"""
Visualize demand-side metrics.

Written by Ed Oughton.

May 2023

"""
import os
import configparser
import json
import csv
import geopandas as gpd
import pandas as pd
import glob
import pyproj
# from shapely.geometry import MultiPolygon, mapping, MultiLineString
# from shapely.ops import transform, unary_union, nearest_points
import rasterio
from rasterio.mask import mask
from rasterstats import zonal_stats
# from tqdm import tqdm
from shapely.geometry import box, shape
# from rasterio.merge import merge
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx

from misc import get_countries

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')
REPORTS = os.path.join(BASE_PATH, '..', 'reports', 'images')


def create_regional_grid(country):
    """
    Create a grid at the desired resolution for each region.

    """
    filename = "national_outline.shp"
    folder = os.path.join(DATA_PROCESSED, country['iso3'])
    path = os.path.join(folder, filename)

    national_outline = gpd.read_file(path, crs='epsg:4326')
    national_outline = national_outline.to_crs(3857)

    xmin, ymin, xmax, ymax= national_outline.total_bounds

    cell_size = 25000

    grid_cells = []
    for x0 in np.arange(xmin, xmax+cell_size, cell_size ):
        for y0 in np.arange(ymin, ymax+cell_size, cell_size):
            x1 = x0 - cell_size
            y1 = y0 + cell_size
            grid_cells.append(box(x0, y0, x1, y1))

    grid = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs='epsg:3857')

    grid = gpd.overlay(grid, national_outline, how='intersection')

    grid = grid.to_crs(4326)

    filename = 'regions_{}_{}.shp'.format(country['gid_region'], country['iso3'])
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')#[:3]

    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'grid')
    if not os.path.exists(folder):
        os.makedirs(folder)

    for idx, region in regions.iterrows():

        gid_level = 'GID_{}'.format(country['gid_region'])
        gid_id = region[gid_level]

        filename = "{}.shp".format(gid_id)
        path_out = os.path.join(folder, filename)

        if os.path.exists(path_out):
            continue

        output = []

        for idx, grid_tile in grid.iterrows():
            if region['geometry'].intersects(grid_tile['geometry'].centroid):
                output.append({
                    'geometry': grid_tile['geometry'],
                    'properties': {
                        'tile_id': idx,
                    }
                })

        if len(output) == 0:
            continue

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        output.to_file(path_out, crs='epsg:4326')

    return


def process_settlement_layer(country):
    """
    Clip the settlement layer to the chosen country boundary and place in
    desired country folder.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    iso3 = country['iso3']
    regional_level = country['gid_region']

    path_settlements = os.path.join(DATA_RAW, 'settlement_layer',
        'ppp_2020_1km_Aggregated.tif')

    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    iso3 = country['iso3']
    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')

    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        print('Must generate national_outline.shp first' )

    path_country = os.path.join(DATA_PROCESSED, iso3)
    shape_path = os.path.join(path_country, 'settlements.tif')

    if os.path.exists(shape_path):
        return print('Completed settlement layer processing')

    print('----')
    print('Working on {} level {}'.format(iso3, regional_level))

    geo = gpd.GeoDataFrame()
    geo = gpd.GeoDataFrame({'geometry': country['geometry']})

    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(settlements, coords, crop=True)

    out_meta = settlements.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})

    with rasterio.open(shape_path, "w", **out_meta) as dest:
            dest.write(out_img)

    return print('Completed processing of settlement layer')


def export_population_grid(country):
    """
    Extract regional data including luminosity and population.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    iso3 = country['iso3']
    level = country['gid_region']
    gid_level = 'GID_{}'.format(level)

    filename = 'grid.shp'
    folder_out = os.path.join(DATA_PROCESSED, country['iso3'], 'population')
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)
    path_out = os.path.join(folder_out, filename)

    if os.path.exists(path_out):
        return print('Regional data already exists')

    path_settlements = os.path.join(DATA_PROCESSED, iso3,
        'settlements.tif')

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path)

    output = []

    for index, region in regions.iterrows():

        gid_id = region[gid_level]

        folder_grid = os.path.join(DATA_PROCESSED, iso3, 'grid')
        path_grid = os.path.join(folder_grid, gid_id + '.shp')
        if not os.path.exists(path_grid):
            continue
        grid = gpd.read_file(path_grid, crs='epsg:4326')#[:2]
        
        for idx, grid_tile in grid.iterrows():

            with rasterio.open(path_settlements) as src:

                affine = src.transform
                array = src.read(1)
                array[array <= 0] = 0

                population_summation = [d['sum'] for d in zonal_stats(
                    grid_tile['geometry'],
                    array,
                    stats=['sum'],
                    nodata=0,
                    affine=affine)][0]

                output.append({
                    'geometry': grid_tile['geometry'],
                    'properties': {
                        'population': population_summation,
                    }
                })

    if len(output) == 0:
        return

    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    output.to_file(path_out, crs='epsg:4326')

    return


def process_regional_wealth(country):
    """
    Process wealth index by country.

    """
    filename = "{}_relative_wealth_index.csv".format(country['iso3'])
    folder = os.path.join(DATA_RAW, 'relative_wealth_index')
    path_in = os.path.join(folder, filename)

    folder_out = os.path.join(DATA_PROCESSED, country['iso3'], 'relative_wealth_index', 'regions')

    if not os.path.exists(folder_out):
        os.makedirs(folder_out)

    data = pd.read_csv(path_in)#[:10]
    data['decile'] = pd.qcut(data['rwi'], 5, labels=False)
    data = gpd.GeoDataFrame(data,
            geometry=gpd.points_from_xy(data.longitude, data.latitude),
            crs='epsg:4326')
    data = data.drop(columns=['longitude', 'latitude'])

    filename = 'regions_{}_{}.shp'.format(country['gid_region'], country['iso3'])
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')#[:3]

    for idx, region in regions.iterrows():

        output = []

        gid_level = 'GID_{}'.format(country['gid_region'])
        gid_id = region[gid_level]

        for idx, point in data.iterrows():
            if point['geometry'].intersects(region['geometry']):
                output.append({
                    'geometry': point['geometry'],
                    'properties': {
                        'rwi': point['rwi'],
                        'decile': point['decile'],
                    }
                })

        if len(output) == 0:
            continue

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        filename = "{}.shp".format(gid_id)
        path_out = os.path.join(folder_out, filename)
        output.to_file(path_out, crs='epsg:4326')

    return


def export_wealth_grid(country):
    """
    Process wealth index by country.

    """
    output = []

    filename = 'regions_{}_{}.shp'.format(country['gid_region'], country['iso3'])
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')#[:2]

    folder_regions = os.path.join(DATA_PROCESSED, country['iso3'], 'relative_wealth_index', 'regions')
    folder_grid = os.path.join(DATA_PROCESSED, country['iso3'], 'grid')

    for idx, region in regions.iterrows():

        gid_level = 'GID_{}'.format(country['gid_region'])
        gid_id = region[gid_level]

        print('Working on {}'.format(gid_id))

        # if not gid_id == 'COD.21_1':
        #     continue

        path1 = os.path.join(folder_regions, gid_id + '.shp')
        if not os.path.exists(path1):
            continue
        points = gpd.read_file(path1, crs='epsg:4326')

        path2 = os.path.join(folder_grid, gid_id + '.shp')
        if not os.path.exists(path2):
            continue
        grid = gpd.read_file(path2, crs='epsg:4326')#[:12]

        seen = set()
        
        for idx, grid_tile in grid.iterrows():

            rwi = []
            for idx, point in points.iterrows():
                if point['geometry'].intersects(grid_tile['geometry']):
                    rwi.append(point['rwi'])

            if len(rwi) > 0:
                rwi_mean = round(sum(rwi) / len(rwi), 5)
            else:
                rwi_mean = None

            output.append({
                'geometry': grid_tile['geometry'],
                'properties': {
                    'rwi': rwi_mean,
                    # 'decile': point['decile'],
                }
            })
            seen.add(idx)

        # for idx, grid_tile in grid.iterrows():
        #     if not idx in list(seen):
        #         output.append({
        #             'geometry': grid_tile['geometry'],
        #             'properties': {
        #                 'rwi': 'NA',
        #                 # 'decile': 0,
        #             }
        #         })

    if len(output) == 0:
        return
    
    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    output['decile'] = pd.qcut(output['rwi'], 10, labels=False)

    filename = "rwi_grid.shp"
    path_out = os.path.join(folder_regions, '..', filename)
    output.to_file(path_out, crs='epsg:4326')

    return


def plot_population(country, outline, dimensions):
    """
    Plot population.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'demand')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = country['buffer']
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    fig.set_facecolor('gainsboro')

    folder = os.path.join(DATA_PROCESSED, iso3, 'population')
    filename = 'grid.shp'
    path1 = os.path.join(folder, filename)
    grid = gpd.read_file(path1, crs='epsg:4326')
    grid = grid.to_crs('epsg:3857')
    grid['area_km2'] = grid['geometry'].area/1e6
    grid['pop_density_km2'] =  grid['population'] / grid['area_km2']
    grid = grid.to_crs('epsg:4326')

    bins = [-1e6, 10, 50, 100, 200, 300, 400, 500, 600, 700, 1e12]
    labels = ['<10 $km^2$','<50 $km^2$','<100 $km^2$','<200 $km^2$',
              '<300 $km^2$', '<400 $km^2$', '<500 $km^2$', '<600 $km^2$', '<700 $km^2$', '>700 $km^2$']

    #create a new variable with our bin labels
    grid['bin'] = pd.cut(
        grid['pop_density_km2'],
        bins=bins,
        labels=labels
    )

    grid.plot(
        column='bin', cmap='viridis', linewidth=0.5, alpha=.9,
        legend=True, edgecolor='black', ax=ax,     
        missing_kwds={
            "color": "lightgrey",
            "label": "Missing data",
        },
    )
    cx.add_basemap(ax, crs='epsg:4326')

    main_title = 'Population Density\n(Persons Per $km^2$)'
    plt.suptitle(main_title, fontsize=20, y=1.01, wrap=True)

    path_out = os.path.join(folder_vis, 'pop_density.png')

    plt.savefig(path_out,
        pad_inches=0.4,
        bbox_inches='tight',
        dpi=600,
    )
    plt.close()


def plot_wealth(country, outline, dimensions):
    """
    Plot wealth.

    """
    iso3 = country['iso3']
    name = country['country']

    folder_vis = os.path.join(VIS, iso3, 'demand')
    if not os.path.exists(folder_vis):
        os.makedirs(folder_vis)

    fig, ax = plt.subplots(1, 1, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = country['buffer']
    ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
    ax.set_ylim(miny-0.1, maxy+.1)

    fig.set_facecolor('gainsboro')

    folder = os.path.join(DATA_PROCESSED, iso3, 'relative_wealth_index')
    filename = 'rwi_grid.shp'
    path1 = os.path.join(folder, filename)
    grid = gpd.read_file(path1, crs='epsg:4326')

    bins = [-1e6, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8, 9.9, 1e12]
    labels = ['Decile 1','Decile 2','Decile 3','Decile 4',
              'Decile 5', 'Decile 6', 'Decile 7', 'Decile 8', 'Decile 9', 'Decile 10']

    #create a new variable with our bin labels
    grid['bin'] = pd.cut(
        grid['decile'],
        bins=bins,
        labels=labels
    )

    grid.plot(
        column='bin', cmap='viridis_r', linewidth=0.5, alpha=.9,
        legend=True, edgecolor='black', ax=ax,   
        missing_kwds={
            "color": "lightgrey",
            "label": "Missing data",
        },
    )
    handles, labels = ax.get_legend_handles_labels()

    cx.add_basemap(ax, crs='epsg:4326')

    main_title = 'Relative Wealth Index\n(Decile 10: Highest Income, Decile 1: Lowest Income)'
    plt.suptitle(main_title, fontsize=20, y=1.01, wrap=True)

    path_out = os.path.join(folder_vis, 'wealth.png')

    plt.savefig(path_out,
        pad_inches=0.4,
        bbox_inches='tight',
        dpi=600,
    )
    plt.close()


if __name__ == '__main__':

    countries = get_countries()

    for idx, country in countries.iterrows(): #, total=countries.shape[0]):

        if not country['iso3'] in ['COD']:#'MWI', 'GHA']:
            continue

        create_regional_grid(country)

        process_settlement_layer(country)

        export_population_grid(country)

        process_regional_wealth(country)

        export_wealth_grid(country)

        dimensions = (int(country['dimensions_x']), int(country['dimensions_y']))
        iso3 = country['iso3']
        country['figsize'] = dimensions#(8,10)

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

        plot_population(country, outline, dimensions)

        plot_wealth(country, outline, dimensions)
