"""
Prepare all necessary data layers required for running the main
model script (scripts/run.py).

Written by Ed Oughton.

November 2020

"""
import os
import configparser
import json
import math
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import pyproj
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, nearest_points, transform
import rasterio
import networkx as nx
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterstats import zonal_stats, gen_zonal_stats
# import rioxarray as rxr
# import xarray

# grass7bin = r'"C:\Program Files\GRASS GIS 7.8\grass78.bat"'
# os.environ['GRASSBIN'] = grass7bin
# os.environ['PATH'] += ';' + r"C:\Program Files\GRASS GIS 7.8\lib"

# from grass_session import Session
# from grass.script import core as gcore

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def generate_settlement_lut(country):
    """
    Generate a lookup table of all settlements over the defined
    settlement thresholds for the country being modeled.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)
    main_settlement_size = country['main_settlement_size']

    folder = os.path.join(DATA_PROCESSED, iso3, 'settlements')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_output = os.path.join(folder, 'settlements.shp')

    # if os.path.exists(path_output):
    #     return print('Already processed settlement lookup table (lut)')

    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs="epsg:4326")#[:20]
    regions = regions.loc[regions.is_valid]

    path_settlements = os.path.join(DATA_PROCESSED, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 0
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_PROCESSED, iso3, 'settlements', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        path_output = os.path.join(folder_tifs, region[GID_level] + '.tif')

        # if os.path.exists(path_output):
        #     continue

        bbox = region['geometry'].envelope

        geo = gpd.GeoDataFrame()
        geo = gpd.GeoDataFrame({'geometry': bbox}, index=[idx], crs='epsg:4326')
        coords = [json.loads(geo.to_json())['features'][0]['geometry']]

        #chop on coords
        out_img, out_transform = mask(settlements, coords, crop=True)

        # Copy the metadata
        out_meta = settlements.meta.copy()

        out_meta.update({"driver": "GTiff",
                        "height": out_img.shape[1],
                        "width": out_img.shape[2],
                        "transform": out_transform,
                        # "crs": 'epsg:4326'
                        })

        with rasterio.open(path_output, "w", **out_meta) as dest:
                dest.write(out_img)

    nodes = find_nodes(country, regions)

    nodes = gpd.GeoDataFrame.from_features(nodes, crs='epsg:4326')

    bool_list = nodes.intersects(regions['geometry'].unary_union)
    nodes = pd.concat([nodes, bool_list], axis=1)
    nodes = nodes[nodes[0] == True].drop(columns=0)

    settlements = []

    print('Identifying settlements')
    for idx1, region in regions.iterrows():

        # if not region['GID_2'] in single_region:
        #     continue

        seen = set()
        for idx2, node in nodes.iterrows():
            if node['geometry'].intersects(region['geometry']):
                if node['sum'] > 0:
                    settlements.append({
                        'type': 'Feature',
                        'geometry': mapping(node['geometry']),
                        'properties': {
                            'id': idx1,
                            'GID_0': region['GID_0'],
                            GID_level: region[GID_level],
                            'population': node['sum'],
                            'type': node['type'],
                        }
                    })
                    seen.add(region[GID_level])

    settlements = gpd.GeoDataFrame.from_features(
            [
                {
                    'geometry': item['geometry'],
                    'properties': {
                        'id': item['properties']['id'],
                        'GID_0':item['properties']['GID_0'],
                        GID_level: item['properties'][GID_level],
                        'population': item['properties']['population'],
                        'type': item['properties']['type'],
                    }
                }
                for item in settlements
            ],
            crs='epsg:4326'
        )

    settlements['lon'] = round(settlements['geometry'].x, 5)
    settlements['lat'] = round(settlements['geometry'].y, 5)

    settlements = settlements.drop_duplicates(subset=['lon', 'lat'])

    folder = os.path.join(DATA_PROCESSED, iso3, 'settlements')
    path_output = os.path.join(folder, 'settlements' + '.shp')
    settlements.to_file(path_output)

    folder = os.path.join(DATA_PROCESSED, iso3, 'network_routing_structure')

    if not os.path.exists(folder):
        os.makedirs(folder)

    path_output = os.path.join(folder, 'main_nodes' + '.shp')
    main_nodes = settlements.loc[settlements['population'] >= main_settlement_size]
    main_nodes.to_file(path_output)

    settlements = settlements[['lon', 'lat', GID_level, 'population', 'type']]
    settlements.to_csv(os.path.join(folder, 'settlements.csv'), index=False)

    return


def find_nodes(country, regions):
    """
    Find key nodes in each region.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.
    regions : dataframe
        Pandas df containing all regions for modeling.

    Returns
    -------
    interim : list of dicts

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_PROCESSED, iso3, 'settlements', 'tifs')

    interim = []

    # print('Working on gathering data from regional rasters')
    for idx, region in regions.iterrows():

        # if not region['GID_2'] == ['PER.1.1_1']:
        #     continue

        path = os.path.join(folder_tifs, region[GID_level] + '.tif')

        with rasterio.open(path) as src: # convert raster to pandas geodataframe
            data = src.read()
            data[data < threshold] = 0
            data[data >= threshold] = 1
            polygons = rasterio.features.shapes(data, transform=src.transform)
            shapes_df = gpd.GeoDataFrame.from_features(
                [{'geometry': poly, 'properties':{'value':value}}
                    for poly, value in polygons if value > 0]#, crs='epsg:4326'
            )

        if len(shapes_df) == 0: #if you put the crs in the preceeding function
            continue            #there is an error for an empty df
        shapes_df = shapes_df.set_crs('epsg:4326')

        geojson_region = [
            {'geometry': region['geometry'],
            'properties': {GID_level: region[GID_level]}
            }]

        gpd_region = gpd.GeoDataFrame.from_features(
                [{'geometry': poly['geometry'],
                    'properties':{GID_level: poly['properties'][GID_level]}}
                    for poly in geojson_region
                ]#, crs='epsg:4326'
            )

        if len(gpd_region) == 0: #if you put the crs in the preceeding function
            continue             #there is an error for an empty df
        gpd_region = gpd_region.set_crs('epsg:4326')

        nodes = gpd.overlay(shapes_df, gpd_region, how='intersection')

        results = []

        for idx, node in nodes.iterrows():
            pop = zonal_stats(
                node['geometry'],
                path,
                nodata=0,
                stats=['sum']
            )
            if not pop[0]['sum'] == None and pop[0]['sum'] > settlement_size:
                results.append({
                    'geometry': node['geometry'],
                    'properties': {
                        '{}'.format(GID_level): node[GID_level],
                        'sum': pop[0]['sum']
                    },
                })

        nodes = gpd.GeoDataFrame.from_features(
            [{
                'geometry': item['geometry'],
                'properties': {
                        '{}'.format(GID_level): item['properties'][GID_level],
                        'sum': item['properties']['sum'],
                    },
                }
                for item in results
            ]#, crs='epsg:4326'
        )

        nodes = nodes.drop_duplicates()

        if len(nodes) == 0: #if you put the crs in the preceeding function
            continue        #there is an error for an empty df
        nodes = nodes.set_crs('epsg:4326')

        nodes.loc[(nodes['sum'] >= 20000), 'type'] = '>20k'
        nodes.loc[(nodes['sum'] <= 10000) | (nodes['sum'] < 20000), 'type'] = '10-20k'
        nodes.loc[(nodes['sum'] <= 5000) | (nodes['sum'] < 10000), 'type'] = '5-10k'
        nodes.loc[(nodes['sum'] <= 1000) | (nodes['sum'] < 5000), 'type'] = '1-5k'
        nodes.loc[(nodes['sum'] <= 500) | (nodes['sum'] < 1000), 'type'] = '0.5-1k'
        nodes.loc[(nodes['sum'] <= 250) | (nodes['sum'] < 500), 'type'] = '0.25-0.5k'
        nodes.loc[(nodes['sum'] <= 250), 'type'] = '<0.25k'

        nodes = nodes.dropna()

        for idx, item in nodes.iterrows():
            if item['sum'] > 0:
                interim.append({
                        'geometry': item['geometry'].centroid,
                        'properties': {
                            GID_level: region[GID_level],
                            'sum': item['sum'],
                            'type': item['type'],
                        },
                })

    return interim


def generate_agglomeration_lut(country):
    """
    Generate a lookup table of agglomerations.
    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    core_node_level = 'GID_{}'.format(country['core_node_level'])
    regional_node_level = 'GID_{}'.format(country['regional_node_level'])

    folder = os.path.join(DATA_PROCESSED, iso3, 'agglomerations')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_output = os.path.join(folder, 'agglomerations.shp')

    if os.path.exists(path_output):
        return print('Agglomeration processing has already completed')

    print('Working on {} agglomeration lookup table'.format(iso3))

    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs="epsg:4326")#[:1]

    path_settlements = os.path.join(DATA_PROCESSED, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_PROCESSED, iso3, 'agglomerations', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        path_output = os.path.join(folder_tifs, region[GID_level] + '.tif')

        if os.path.exists(path_output):
            continue

        # geo = gpd.GeoDataFrame({'geometry': region['geometry']}, index=[idx])
        geo = gpd.GeoDataFrame(geometry=gpd.GeoSeries(region['geometry']))

        coords = [json.loads(geo.to_json())['features'][0]['geometry']]

        #chop on coords
        out_img, out_transform = mask(settlements, coords, crop=True)

        # Copy the metadata
        out_meta = settlements.meta.copy()

        out_meta.update({"driver": "GTiff",
                        "height": out_img.shape[1],
                        "width": out_img.shape[2],
                        "transform": out_transform,
                        "crs": 'epsg:4326'})

        with rasterio.open(path_output, "w", **out_meta) as dest:
                dest.write(out_img)

    print('Completed settlement.tif regional segmentation')

    nodes, missing_nodes = find_settlement_nodes(country, regions)

    nodes = gpd.GeoDataFrame.from_features(nodes, crs='epsg:4326')

    bool_list = nodes.intersects(regions['geometry'].unary_union)
    nodes = pd.concat([nodes, bool_list], axis=1)
    nodes = nodes[nodes[0] == True].drop(columns=0)

    agglomerations = []

    print('Identifying agglomerations')
    for idx1, region in regions.iterrows():
        seen_coords = set()
        for idx2, node in nodes.iterrows():
            if node['geometry'].intersects(region['geometry']):

                x = float(str(node['geometry'].x)[:12])
                y = float(str(node['geometry'].y)[:12])
                coord = '{}_{}'.format(x ,y)

                if coord in seen_coords:
                    continue #avoid duplicates

                agglomerations.append({
                    'type': 'Feature',
                    'geometry': mapping(node['geometry']),
                    'properties': {
                        'id': idx1,
                        'GID_0': region['GID_0'],
                        GID_level: region[GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        'population': node['sum'],
                    }
                })
                seen_coords.add(coord)

        # if no settlements above the threshold values
        # find the most populated 1km2 cell centroid
        if len(seen_coords) == 0:

            pop_tif = os.path.join(folder_tifs, region[GID_level] + '.tif')

            with rasterio.open(pop_tif) as src:
                data = src.read()
                polygons = rasterio.features.shapes(data, transform=src.transform)
                shapes_df = gpd.GeoDataFrame.from_features(
                    [
                        {'geometry': poly, 'properties':{'value':value}}
                        for poly, value in polygons
                    ],
                    crs='epsg:4326'
                )
                shapes_df =shapes_df.nlargest(1, columns=['value'])

                shapes_df['geometry'] = shapes_df['geometry'].to_crs('epsg:3857')
                shapes_df['geometry'] = shapes_df['geometry'].centroid
                shapes_df['geometry'] = shapes_df['geometry'].to_crs('epsg:4326')
                geom = shapes_df['geometry'].values[0]

                x = float(str(node['geometry'].x)[:12])
                y = float(str(node['geometry'].y)[:12])
                coord = '{}_{}'.format(x ,y)

                if coord in seen_coords:
                    continue #avoid duplicates

                agglomerations.append({
                        'type': 'Feature',
                        'geometry': mapping(geom),
                        'properties': {
                            'id': 'regional_node',
                            'GID_0': region['GID_0'],
                            GID_level: region[GID_level],
                            core_node_level: region[core_node_level],
                            regional_node_level: region[regional_node_level],
                            'population': shapes_df['value'].values[0],
                        }
                    })

    agglomerations = gpd.GeoDataFrame.from_features(
            [
                {
                    'geometry': item['geometry'],
                    'properties': {
                        'id': item['properties']['id'],
                        'GID_0':item['properties']['GID_0'],
                        GID_level: item['properties'][GID_level],
                        core_node_level: item['properties'][core_node_level],
                        regional_node_level: item['properties'][regional_node_level],
                        'population': item['properties']['population'],
                    }
                }
                for item in agglomerations
            ],
            crs='epsg:4326'
        )

    agglomerations = agglomerations.drop_duplicates(subset=['geometry']).reset_index()

    folder = os.path.join(DATA_PROCESSED, iso3, 'agglomerations')
    path_output = os.path.join(folder, 'agglomerations' + '.shp')

    agglomerations.to_file(path_output)

    agglomerations['lon'] = agglomerations['geometry'].x
    agglomerations['lat'] = agglomerations['geometry'].y
    agglomerations = agglomerations[['lon', 'lat', GID_level, 'population']]
    agglomerations = agglomerations.drop_duplicates(subset=['lon', 'lat']).reset_index()
    agglomerations.to_csv(os.path.join(folder, 'agglomerations.csv'), index=False)

    return print('Agglomerations layer complete')


def find_settlement_nodes(country, regions):
    """
    Find key nodes.
    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    core_node_level = 'GID_{}'.format(country['core_node_level'])
    regional_node_level = 'GID_{}'.format(country['regional_node_level'])

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_PROCESSED, iso3, 'agglomerations', 'tifs')

    interim = []
    missing_nodes = set()

    print('Working on gathering data from regional rasters')
    for idx, region in regions.iterrows():

        path = os.path.join(folder_tifs, region[GID_level] + '.tif')

        with rasterio.open(path) as src:
            data = src.read()
            data[data < threshold] = 0
            data[data >= threshold] = 1
            polygons = rasterio.features.shapes(data, transform=src.transform)
            shapes_df = gpd.GeoDataFrame.from_features(
                [
                    {'geometry': poly, 'properties':{'value':value}}
                    for poly, value in polygons
                    if value > 0
                ]
            )
        if len(shapes_df) == 0:
            continue

        shapes_df = shapes_df.set_crs('epsg:4326')

        geojson_region = [
            {
                'geometry': region['geometry'],
                'properties': {
                    GID_level: region[GID_level],
                    core_node_level: region[core_node_level],
                    regional_node_level: region[regional_node_level],
                }
            }
        ]

        gpd_region = gpd.GeoDataFrame.from_features(
                [
                    {'geometry': poly['geometry'],
                    'properties':{
                        GID_level: poly['properties'][GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        }}
                    for poly in geojson_region
                ], crs='epsg:4326'
            )

        if len(shapes_df) == 0:
            continue

        nodes = gpd.overlay(shapes_df, gpd_region, how='intersection')

        stats = zonal_stats(shapes_df['geometry'], path, stats=['count', 'sum'])

        stats_df = pd.DataFrame(stats)

        nodes = pd.concat([shapes_df, stats_df], axis=1).drop(columns='value')

        nodes_subset = nodes[nodes['sum'] >= settlement_size]

        if len(nodes_subset) == 0:
            missing_nodes.add(region[GID_level])

        for idx, item in nodes_subset.iterrows():
            interim.append({
                    'geometry': item['geometry'].centroid,
                    'properties': {
                        GID_level: region[GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        'count': item['count'],
                        'sum': item['sum']
                    }
            })

    return interim, missing_nodes


def find_largest_regional_settlement(country):
    """
    Find the largest settlement in each region as the main regional
    routing node.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_PROCESSED, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'largest_regional_settlements.shp')

    # if os.path.exists(path_output):
    #     return print('Already processed the largest regional settlement layer')

    folder = os.path.join(DATA_PROCESSED, iso3, 'settlements')
    path_input = os.path.join(folder, 'settlements' + '.shp')
    nodes = gpd.read_file(path_input, crs='epsg:4326')

    nodes = nodes.loc[nodes.reset_index().groupby([GID_level])['population'].idxmax()]
    nodes.to_file(path_output, crs='epsg:4326')

    return


if __name__ == '__main__':

    # countries = [
    #     {
    #         'iso3': 'BWA', #'iso2': 'PE', 'name': 'Peru',
    #         'regional_level': 2,
    #         'lowest_regional_level': 3, #'region': 'LAT',
    #         'pop_density_km2': 2, 'settlement_size': 25,
    #         'main_settlement_size': 20000, #'subs_growth': 3.5,
    #         #'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16,
    #         #'core_node_level': 1, 'regional_node_level': 2,
    #     },
    # ]

    for country in countries:

        if not country['iso3'] in ['COD', 'KEN', 'ETH', 'DJI','SOM', 'SSD', 'MDG']:
            continue

        print('Working on {}'.format(country['iso3']))

        generate_settlement_lut(country)

        # # ### Generating the settlement layer ready to export
        # generate_agglomeration_lut(country)

        # ### Find largest settlement in each region ready to export
        # find_largest_regional_settlement(country)

        # ### Get settlement routing paths
        # get_settlement_routing_paths(country)

    print('Preprocessing complete')