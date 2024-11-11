"""
Process fiber.

"""
import os
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiLineString, LineString, mapping
import fiona
import zipfile
from lxml import etree
from pykml import parser

from misc import get_countries

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def convert_kmz_to_shp():
    """
    
    """
    folder = os.path.join(DATA_RAW, 'HOA maps')
    all_files = os.listdir(folder)

    folder_out = os.path.join(DATA_RAW, 'HOA maps', 'shapefiles')
    if not os.path.exists(folder_out):
        os.mkdir(folder_out)

    for filename in all_files:

        if not filename.endswith('.kmz'):
            continue
        
        if not "HoA Map 8.1" in filename:
            continue
        
        kmz_path = os.path.join(folder, filename)
        
        filename_out = filename.replace('.kmz','.shp')
        output_shapefile = os.path.join(folder_out, filename_out)

        convert(kmz_path, output_shapefile)

    return


def extract_kml_from_kmz(kmz_path, extract_to='.'):
    """
    Extracts the .kml file from a .kmz archive.
    
    Parameters:
    kmz_path (str): Path to the .kmz file.
    extract_to (str): Directory to extract the .kml file into.

    Returns:
    str: The path to the extracted .kml file.

    """
    with zipfile.ZipFile(kmz_path, 'r') as kmz:
        for file in kmz.namelist():
            if file.endswith('.kml'):
                kmz.extract(file, extract_to)
                return os.path.join(extract_to, file)
            
    raise FileNotFoundError("No KML file found inside the KMZ.")


def kml_to_gdf(kml_file):
    """
    Parses a .kml file and converts it to a GeoDataFrame.
    
    Parameters:
    kml_file (str): Path to the .kml file.
    
    Returns:
    geopandas.GeoDataFrame: A GeoDataFrame containing the 
    geometries and names of placemarks.

    """
    with open(kml_file, 'r') as f:
        kml_tree = parser.parse(f)
        root = kml_tree.getroot()
    
    # Namespace for KML parsing
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    
    # Extract all placemarks (they can be inside folders or directly in the root)
    placemarks = root.findall(".//kml:Placemark", namespaces=ns)
    
    geometries = []
    names = []

    for placemark in placemarks:
        # Get the name of the placemark (if available)
        name = placemark.find(".//kml:name", namespaces=ns)
        name = name.text if name is not None else "Unnamed"

        # Extract geometry based on type (Point, LineString, Polygon)
        if placemark.find(".//kml:Point", namespaces=ns) is not None:
            coords = placemark.find(".//kml:coordinates", namespaces=ns).text.strip()
            lon, lat, _ = coords.split(',')
            geometries.append(Point(float(lon), float(lat)))
        
        elif placemark.find(".//kml:LineString", namespaces=ns) is not None:
            coords = placemark.find(".//kml:coordinates", namespaces=ns).text.strip().split()
            line_coords = [(float(coord.split(',')[0]), float(coord.split(',')[1])) for coord in coords]
            geometries.append(LineString(line_coords))
        
        elif placemark.find(".//kml:Polygon", namespaces=ns) is not None:
            coords = placemark.find(".//kml:coordinates", namespaces=ns).text.strip().split()
            poly_coords = [(float(coord.split(',')[0]), float(coord.split(',')[1])) for coord in coords]
            geometries.append(Polygon(poly_coords))
        
        names.append(name)

    # Create a GeoDataFrame with the geometries and names
    gdf = gpd.GeoDataFrame({'name': names, 'geometry': geometries}, crs="EPSG:4326")

    return gdf


def convert(kmz_path, output_shp_path):
    """
    Converts a .kmz file to a shapefile (.shp).
    
    Parameters:
    kmz_path (str): Path to the .kmz file.
    output_shp_path (str): Path where the output .shp file should be saved.

    """
    if not "HoA Map 8.1" in kmz_path:
        return

    # Extract KML from KMZ
    kml_path = extract_kml_from_kmz(kmz_path)
    
    # Convert KML to GeoDataFrame
    gdf = kml_to_gdf(kml_path)
    gdf.insert(0, 'geo_id', range(0, len(gdf)))
    
    data = gdf.to_dict('records')

    #define route ID status
    exclude = [142, 151]
    planned = [133,134,135,136,137,138,139,140,141,142,143,144,145,
            146,147,148,149,150,151,152,153,154,155]
    inactive = [156,157]
    needs_upgrading = [0,1,2,3,4,5,6]

    output = []

    for item in data:

        if item['geo_id'] in exclude:
            continue
        status = 'Live'
        if item['geo_id'] in planned:
            status = 'Planned'
        if item['geo_id'] in inactive:
            status = 'Inactive'
        if item['geo_id'] in needs_upgrading:
            status = 'Needs Upgrading'

        output.append({
            'geometry': item['geometry'],
            'properties': {
                'geo_id': item['geo_id'],
                'name': item['name'],
                'status': status,
            }
        })

    output = gpd.GeoDataFrame.from_features(output)

    # Save the GeoDataFrame as a shapefile
    output.to_file(output_shp_path)
    print(f"Shapefile saved at {output_shp_path}")

    return


def process_fiber(iso3):
    """
    
    """
    countries = get_countries()

    for idx, country in countries.iterrows():

        if not country['iso3'] == iso3:
            continue

        if country['iso3'] in ['BWA', 'COD', 'KEN', 'MDG'#'ETH', 'DJI','SOM', 'SSD', 
                               ]:
            process_afterfibre_data(country)

        if country['iso3'] in ['AZE']:
            process_itu_data(country)

        if country['iso3'] in ['KEN']:
            preprocess_kenya_link_data()

        if country['iso3'] in ['MDG']:
            preprocess_madagascar_data()

        if country['iso3'] in ['ETH', 'DJI','SOM', 'SSD']:
            preprocess_hoa_data(country['iso3'])

    return


def process_afterfibre_data(country):
    """
    Load and process existing fiber data.

    """
    iso3 = country['iso3']
    iso2 = country['iso2'].lower()
    if iso2 == 'ss':
        iso2 = 'sd'

    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'afterfibre')
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = 'core_edges_existing.shp'
    path_output = os.path.join(folder, filename)

    # if os.path.exists(path_output):
    #     return print('Existing fiber already processed')

    path = os.path.join(DATA_RAW, 'afterfiber', 'afterfiber.shp')

    shapes = fiona.open(path)

    data = []
    idx2 = 0

    for idx, item in enumerate(shapes):
        if item['properties']['iso2'] == iso2:
            if item['geometry']['type'] == 'LineString':
                # if int(item['properties']['live']) == 1:
                data.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': item['geometry']['coordinates'],
                    },
                    'properties': {
                        'idx': idx,
                        'idx2': idx2,
                        'operators': item['properties']['operator'],
                        'live': item['properties']['live'],
                        # 'source': 'existing'
                    }
                })

            if item['geometry']['type'] == 'MultiLineString':
                # if int(item['properties']['live']) == 1:
                for idx2, line in enumerate(list(MultiLineString(item['geometry']['coordinates']).geoms)):
                    data.append({
                        'type': 'Feature',
                        'geometry': mapping(line),
                        'properties': {
                            'idx': idx,
                            'idx2': idx2,
                            'operators': item['properties']['operator'],
                            'live': item['properties']['live'],
                            # 'source': 'existing'
                        }
                    })

    if len(data) == 0:
        return print('No existing infrastructure')

    data = gpd.GeoDataFrame.from_features(data)
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


def preprocess_kenya_link_data():
    """
    
    """
    filename = "Final Link KDEAP list with Coordinates-5000 7th August 2024.csv"
    folder = os.path.join(BASE_PATH,'raw', 'kenya_supply_data')
    path_in = os.path.join(folder, filename)
    data = pd.read_csv(path_in)
    data = data[['Start Coordinates','End Coordinates','Link Name','County']]
    data = data.dropna()
    data = data.to_dict('records')

    output = []

    for item in data:

        x1, y1 = item['Start Coordinates'].split(',')
        x2, y2 = item['End Coordinates'].split(',')
        
        geom = LineString([(float(y1),float(x1)), (float(y2),float(x2))])
        
        output.append({
            'geometry': geom,
            'properties': {
                'link_name': item['Link Name'],
                'county': item['County']
            }
        })

    output = gpd.GeoDataFrame.from_features(output)

    output['live'] = 'unknown'
    filename = 'kdeap_links.shp'
    folder = os.path.join(DATA_PROCESSED, 'KEN', 'network_existing', 'country_data')
    path_out = os.path.join(folder, filename)
    output.to_file(path_out)

    return


def preprocess_madagascar_data():
    """
    Processes:
    - "Madagascar operational fiber routes.shp"

    """
    output = []

    filename = "Madagascar operational fiber routes.shp"
    folder = os.path.join(DATA_RAW,'Madagascar', 'Madagascar Fiber')
    path_in = os.path.join(folder, filename)
    data = gpd.read_file(path_in)
    data['status'] = 'Live'
    data = data.to_dict('records')
    for item in data:
        output.append({
            'geometry': item['geometry'],
            'properties': {
                'country': 'Madagascar',
                'status': 'Live',
            }
        })

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, 'MDG', 'network_existing', 'afterfibre')
    path_in = os.path.join(folder, filename)
    data_afterfibre = gpd.read_file(path_in)
    data_afterfibre = data_afterfibre.to_dict('records')

    for item in data_afterfibre:
        if item['idx'] == 98:
            if item['idx2'] in [0,1]:
                output.append({
                    'geometry': item['geometry'],
                    'properties': {
                        'country': 'Madagascar',
                        'status': 'Live',
                    }
                })

    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, 'MDG', 'network_existing', 'country_data')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_out = os.path.join(folder, filename)
    output.to_file(path_out)

    return


def preprocess_hoa_data(iso3):
    """

    """
    shapes = []

    folder_in = os.path.join(DATA_RAW, 'HOA maps', 'shapefiles')
    filenames = os.listdir(folder_in)

    for filename in filenames:

        if not filename.endswith('.shp'):
            continue

        if not filename == 'HoA Map 8.1.shp':
            continue

        path_in = os.path.join(folder_in, filename)
        data = gpd.read_file(path_in, crs='epsg:4326')
        data = data.to_dict('records')
        for item in data:

            if item['geometry'] == None:
                continue
            if not item['geometry'].geom_type  == 'LineString':
                continue
            if iso3 == 'ETH':
                if item['status'] == 'planned':
                    continue

            shapes.append({
                'geometry': item['geometry'],
                'properties': {
                    'name': item['name'],
                    'status': item['status']
                }
            })

    gdf = gpd.GeoDataFrame.from_features(shapes, crs='epsg:4326')

    filename = 'national_outline.shp'
    folder = os.path.join(DATA_PROCESSED, iso3)
    path_country = os.path.join(folder, filename)
    country = gpd.read_file(path_country, crs='epsg:4326')

    data = gpd.overlay(gdf, country, how='intersection')

    if len(data) == 0:
        return

    # data['live'] = 1
    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'country_data')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_out = os.path.join(folder, filename)
    data.to_file(path_out, crs='epsg:4326')

    return


if __name__ == '__main__':

    convert_kmz_to_shp()
    
    countries = get_countries()

    for idx, country in countries.iterrows():

        if country['iso3'] in ['KEN', 
                               'ETH', 'DJI','SOM', 
                               'SSD', 
                               'MDG'
                               ]:
            process_fiber(country['iso3'])
