"""
Botswana fiber planning example.

Written by Ed Oughton.

April 2nd 2024.

"""
import os
import configparser
from operator import itemgetter
import geopandas as gpd
from shapely.geometry import Point, LineString
import networkx as nx

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def process_fiber():
    """
    
    """
    filename = 'regions_2_BWA.shp'
    folder = os.path.join(DATA_PROCESSED, 'BWA', 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, 'BWA', 'network_existing')
    path_in = os.path.join(folder, filename)
    fiber = gpd.read_file(path_in, crs='epsg:4326')

    for idx, region in regions.iterrows(): 
        gdf = gpd.GeoDataFrame({'geometry': region['geometry']},index=[0], crs='epsg:4326')
        intersection = fiber.overlay(gdf, how='intersection')
        filename = "{}.shp".format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED, 'BWA','network_existing', 'regions')
        if not os.path.exists(folder):
            os.makedirs(folder)
        path_out = os.path.join(folder, filename)
        intersection.to_file(path_out, crs='epsg:4326')

    return


def process_settlements():
    """
    
    """
    filename = 'regions_2_BWA.shp'
    folder = os.path.join(DATA_PROCESSED, 'BWA', 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')

    filename = 'settlements.shp'
    folder = os.path.join(DATA_RAW, 'botswana_settlements')
    path_in = os.path.join(folder, filename)
    settlements = gpd.read_file(path_in, crs='epsg:4326')

    for idx, region in regions.iterrows(): 
        gdf = gpd.GeoDataFrame({'geometry': region['geometry']},index=[0], crs='epsg:4326')
        intersection = settlements.overlay(gdf, how='intersection')
        if len(intersection) == 0:
            continue
        filename = "{}.shp".format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED, 'BWA','settlements', 'regions')
        if not os.path.exists(folder):
            os.makedirs(folder)
        path_out = os.path.join(folder, filename)
        intersection.to_file(path_out, crs='epsg:4326')

    return


def fit_mst_by_region():
    """
    
    """
    filename = 'regions_2_BWA.shp'
    folder = os.path.join(DATA_PROCESSED, 'BWA', 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')
    regions = regions.to_dict('records')

    for region in regions:

        filename = '{}.shp'.format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED,'BWA','settlements','regions')
        path_in = os.path.join(folder, filename)
        if not os.path.exists(path_in):
            continue
        nodes = gpd.read_file(path_in, crs='epsg:4326')
        nodes = nodes.to_crs(3857)
        nodes['id'] = nodes.index
        nodes = nodes.to_dict('records')

        edges = fit_edges(nodes)
        tree = fit_mst(nodes, edges)

        mst = []

        for source, sink, geojson in tree:
            if geojson['object']['properties']['length'] > 0:
                mst.append({
                    'geometry': geojson['object']['geometry'],
                    'properties': geojson['object']['properties']
                    })

        if len(mst) == 0:
            continue
        
        edges = gpd.GeoDataFrame.from_features(mst, crs='epsg:3857')
        edges = edges.to_crs('epsg:4326')
        filename = '{}.shp'.format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED,'BWA','network_routing_structure','regions')
        if not os.path.exists(folder):
            os.mkdir(folder)
        path_out = os.path.join(folder, filename)
        edges.to_file(path_out, crs='epsg:4326')

    return


def fit_edges(nodes):
    """
    
    """
    my_edges = []

    for item1 in nodes:
        for item2 in nodes:
            if item1['id'] != item2['id']:
                line = LineString([item1['geometry'], item2['geometry']])
                my_edges.append({
                    'geometry': line,
                    'properties': {
                        'from': item1['id'],
                        'to': item2['id'],
                        'length': line.length
                    }
                })

    return my_edges


def fit_mst(nodes, edges):
    """
    
    """
    G = nx.Graph()

    for node_id, node in enumerate(nodes):
        G.add_node(node_id, object=node)

    for edge in edges:
        G.add_edge(edge['properties']['from'], edge['properties']['to'],
            object=edge, weight=edge['properties']['length'])

    tree = nx.minimum_spanning_edges(G)

    return tree


def connect_to_road():
    """
    
    """
    filename = 'regions_2_BWA.shp'
    folder = os.path.join(DATA_PROCESSED, 'BWA', 'regions')
    path_in = os.path.join(folder, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')
    regions = regions.to_dict('records')#[:1]

    for region in regions:

        # if not region['GID_2'] == 'BWA.7.2_1':
        #     continue

        filename = '{}.shp'.format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED,'BWA','network_routing_structure','regions')
        path_in = os.path.join(folder, filename)
        if not os.path.exists(path_in):
            continue
        mst = gpd.read_file(path_in, crs='epsg:4326')
        mst = mst.to_crs(3857)
        mst = mst.to_dict('records')

        filename = '{}.shp'.format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED,'BWA','network_existing','regions')
        path_in = os.path.join(folder, filename)
        if not os.path.exists(path_in):
            continue
        fiber = gpd.read_file(path_in, crs='epsg:4326')
        fiber = fiber.to_crs(3857)
        if not len(fiber) > 0:
            continue
        fiber = fiber.explode(index_parts=True)
        fiber = fiber.to_dict('records')
       
        coords_fiber = []

        for item in fiber:
            coords_fiber = coords_fiber + list(item['geometry'].coords)

        coords_mst = []

        for item in mst:
            coords_mst = coords_mst + list(item['geometry'].coords)

        link_lengths = []

        for item1 in coords_fiber:
            for item2 in coords_mst:
                line = LineString([Point(item1), Point(item2)])
                link_lengths.append([item1, item2, line.length])
        
        link_lengths = sorted(link_lengths, key=itemgetter(2))
        p1, p2, length = link_lengths[0]

        output = []

        for item in mst:
            output.append({
                'geometry': item['geometry'],
                'properties': {
                    'length': item['length'],
                }
            })
        output.append({
            'geometry': LineString([p1,p2]),
            'properties': {
                'length': length
            }
        })
        
        output = gpd.GeoDataFrame.from_features(output, crs='epsg:3857')
        output = output.to_crs('epsg:4326')
        filename = '{}.shp'.format(region['GID_2'])
        folder = os.path.join(DATA_PROCESSED,'BWA','network_routing_structure','regions_final')
        if not os.path.exists(folder):
            os.mkdir(folder)
        path_out = os.path.join(folder, filename)
        output.to_file(path_out, crs='epsg:4326')

    return


if __name__ == '__main__':

    # process_fiber()

    # process_settlements()

    # fit_mst_by_region()

    connect_to_road()







