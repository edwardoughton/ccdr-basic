"""
Intersection of fiber routes with hazard layers.

Written by Ed Oughton.

March 2023.

"""
import os
import sys
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import fiona
from shapely.geometry import MultiLineString, mapping
import json

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def intersect_hazard_fiber(country, hazard_type):
    """
    Intersect fiber with hazards and write out shapes.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']

    filename = 'regions_{}_{}.shp'.format(gid_region, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')

    folder_hazards = os.path.join(DATA_PROCESSED, iso3, 'hazards', hazard_type)
    hazard_filenames = os.listdir(folder_hazards)#[:5]

    for hazard_filename in hazard_filenames:

        if not ".shp" in hazard_filename:
            continue

        # if not "inunriver_rcp4p5_0000HadGEM2-ES_2080_rp00025" in hazard_filename:
        #     continue

        print("Working on {}, {}".format(hazard_filename, hazard_type))

        if iso3 in ['DJI', 'ETH', 'MDG', 'SOM', 'SSD']:
            filename = 'core_edges_existing.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'country_data')
            path_fiber = os.path.join(folder, filename)
            fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        if iso3 in ['KEN']:
            filename = 'From road to NOFBI.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
            path_fiber = os.path.join(folder, filename)
            fiber1 = gpd.read_file(path_fiber, crs='epsg:3857')
            fiber1 = fiber1.to_crs(4326)
            fiber1['status'] = 'Live'
            fiber1 = fiber1[['geometry', 'status']]
            filename = 'core_edges_existing.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing', 'afterfibre')
            path_fiber = os.path.join(folder, filename)
            fiber2 = gpd.read_file(path_fiber, crs='epsg:4326')
            fiber2['status'] = 'Live'
            fiber2 = fiber2[['geometry', 'status']]
            fiber = fiber1.append(fiber2)
        
        fiber_length = fiber.to_crs(3857)
        fiber_length['length_m'] = fiber_length['geometry'].length

        path_hazard = os.path.join(folder_hazards, hazard_filename)
        hazard_layer = gpd.read_file(path_hazard, crs='epsg:4326')

        #intersect fiber with hazard.
        fiber = gpd.overlay(fiber, hazard_layer, how='intersection', keep_geom_type=True) #, make_valid=True
        
        if len(fiber) == 0:
            return
        
        #intersect fiber with regional layer to provide GID id.
        fiber = gpd.overlay(fiber, regions, how='intersection', keep_geom_type=True) #, make_valid=True

        if hazard_type == 'landslide':
            fiber['value'] = fiber['Risk']

        fiber = fiber.to_crs(3857)
        fiber['length_m'] = fiber['geometry'].length

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'shapes')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, hazard_filename)
        fiber.to_file(path_out)

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber') #, 'csv_files'
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, "fiber_length.csv")
        # if os.path.exists(path_out):
        #     continue
        to_csv = fiber_length[['length_m']] #'GID_1',
        to_csv.to_csv(path_out)

    return


def estimate_flooding_vuln_fiber(country, asset_type, hazard_type):
    """
    Collect data by region and estimate flooding vulnerability.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    filename = 'fragility_curve_fiber.csv'
    path_fragility = os.path.join(DATA_RAW, filename)
    low, baseline, high = load_f_curves(path_fragility)

    folder_shapes = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'shapes')
    if not os.path.exists(folder_shapes):
        return
    fiber_shapes = os.listdir(folder_shapes)

    for fiber_filename in fiber_shapes:

        if not ".shp" in fiber_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
        #     continue

        print("Working on {}".format(fiber_filename))

        output = []

        path_fiber = os.path.join(folder_shapes, fiber_filename)
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')#[:10]


        for idx, fiber_row in fiber.iterrows():

            damage_low = query_fragility_curve(low, fiber_row['value'])
            damage_baseline = query_fragility_curve(baseline, fiber_row['value'])
            damage_high = query_fragility_curve(high, fiber_row['value'])

            output.append({
                gid_level: fiber_row[gid_level],
                'depth_m': fiber_row['value'],
                'length_m': fiber_row['length_m'],
                # 'total_m': fiber_row['total_m'],
                'damage_low': damage_low,
                'damage_baseline': damage_baseline,
                'damage_high': damage_high,
                'cost_usd_low': round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_low),
                'cost_usd_baseline':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_baseline),
                'cost_usd_high':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_high),
            })

        if len(output) == 0:
            continue

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'csv_files', 'disaggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'csv_files', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))
        output = output[[gid_level, "length_m", "cost_usd_low", "cost_usd_baseline","cost_usd_high"]]
        output = output.groupby([gid_level], as_index=False).sum()
        output.to_csv(path_out, index=False)

    return


def load_f_curves(path_fragility):
    """
    Load depth-damage curves.

    """
    low = []
    baseline = []
    high = []

    f_curves = pd.read_csv(path_fragility)

    for idx, item in f_curves.iterrows():

        my_dict = {
            'depth_lower_m': item['depth_lower_m'],
            'depth_upper_m': item['depth_upper_m'],
            'damage': item['damage'],
        }

        if item['scenario'] == 'low':
            low.append(my_dict)
        elif item['scenario'] == 'baseline':
            baseline.append(my_dict)
        elif item['scenario'] == 'high':
            high.append(my_dict)

    return low, baseline, high


def query_fragility_curve(f_curve, depth):
    """
    Query the fragility curve.

    """
    if depth < 0:
        return 0

    for item in f_curve:
        if item['depth_lower_m'] <= depth < item['depth_upper_m']:
            return item['damage']
        else:
            continue

    if depth >= max([d['depth_upper_m'] for d in f_curve]):
        return 1

    print('fragility curve failure: {}'.format(depth))

    return 0


def estimate_landslide_vuln_fiber(country, hazard_type):
    """
    Collect data by region and estimate landslide vulnerability.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    # filename = 'fragility_curve_fiber.csv'
    # path_fragility = os.path.join(DATA_RAW, filename)
    # low, baseline, high = load_f_curves(path_fragility)

    folder_shapes = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'shapes')
    if not os.path.exists(folder_shapes):
        return
    fiber_shapes = os.listdir(folder_shapes)

    for fiber_filename in fiber_shapes:

        if not ".shp" in fiber_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
        #     continue

        print("Working on {}".format(fiber_filename))

        output = []

        path_fiber = os.path.join(folder_shapes, fiber_filename)
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')#[:10]

        for idx, fiber_row in fiber.iterrows():

            # damage_low = query_fragility_curve(low, fiber_row['value'])
            # damage_baseline = query_fragility_curve(baseline, fiber_row['value'])
            # damage_high = query_fragility_curve(high, fiber_row['value'])

            if int(float(fiber_row['value'])) == 1:
                risk_cat = 'no_risk'
            elif int(float(fiber_row['value'])) == 2:
                risk_cat = 'low_risk'
            elif int(float(fiber_row['value'])) == 3:
                risk_cat = 'medium_risk'
            elif int(float(fiber_row['value'])) == 4:
                risk_cat = 'high_risk'
            else:
                risk_cat = 'unknown'

            output.append({
                gid_level: fiber_row[gid_level],
                'risk_cat': risk_cat,
                'risk_value': int(float(fiber_row['value'])),
                'length_m': fiber_row['length_m'],
                # 'risk': fiber_row['value']
                # 'total_m': fiber_row['total_m'],
                # 'damage_low': damage_low,
                # 'damage_baseline': damage_baseline,
                # 'damage_high': damage_high,
                # 'cost_usd_low': round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_low),
                # 'cost_usd_baseline':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_baseline),
                # 'cost_usd_high':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_high),
            })

        if len(output) == 0:
            continue

        # results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'csv_files', 'disaggregated')
        # if not os.path.exists(results_folder):
        #     os.makedirs(results_folder)
        # path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))

        output = pd.DataFrame(output)
        # output.to_csv(path_out, index=False)

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber')#, 'csv_files', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, 'assets_by_risk_cat.csv')
        output = output[[gid_level, "length_m", "risk_cat", "risk_value"]]
        output = output.groupby(["risk_cat", "risk_value"], as_index=False).sum() #gid_level, 
        output.to_csv(path_out, index=False)

    return


def aggregate_results_fiber(country, hazard_type): #, outline, dimensions, shapes):
    """
    Aggregate final results

    """
    iso3 = country['iso3']
    name = country['country']
    gid_level = "GID_{}".format(country['gid_region'])

    filename = "fiber_length.csv"
    folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber')
    path = os.path.join(folder, filename)
    fiber_length = pd.read_csv(path)
    total_fiber_km = round(fiber_length['length_m'].sum()/1e3)

    folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'csv_files', 'aggregated')
    filenames = os.listdir(folder)

    output = []

    for filename in filenames:

        path = os.path.join(folder, filename)

        data = pd.read_csv(path)

        fiber_at_risk_km = round(data['length_m'].sum()/1e3)
        fiber_at_risk_perc = round(fiber_at_risk_km / total_fiber_km * 100, 1)
        # print(filename)
        # hazard_type = filename.split('_')[0]
        # scenario = filename.split('_')[1]
        # model = filename.split('_')[2]
        # year = filename.split('_')[3]
        # return_period = filename.split('_')[4]
        # return_period = return_period.replace('.csv', '')

        output.append({
            'hazard_type': hazard_type,
            # 'scenario': scenario,
            # 'model': model,
            # 'year': year,
            # 'return_period': return_period,
            'filename': filename,
            'fiber_at_risk_km': fiber_at_risk_km,
            'total_fiber_km': total_fiber_km,
            'fiber_at_risk_perc': fiber_at_risk_perc
        })

    output = pd.DataFrame(output)

    filename = os.path.join('{}_aggregated_results.csv'.format(hazard_type))
    folder = os.path.join(RESULTS, iso3, hazard_type, 'fiber', 'csv_files')
    path_out = os.path.join(folder, filename)
    output.to_csv(path_out, index=False)

    filename = os.path.join('{}_aggregated_fiber_results.csv'.format(hazard_type))
    folder = os.path.join(BASE_PATH, '..', 'vis', 'figures', iso3, 'scenario_results')
    path_out = os.path.join(folder, filename)
    if not os.path.exists(folder):
        os.makedirs(folder)
    output.to_csv(path_out, index=False)

    return


def intersect_hazard_cells(country, hazard_type): #, scenarios
    """
    Intersect cells with hazards.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    filename = 'regions_{}_{}.shp'.format(gid_region, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')
    region_ids = regions[gid_level].unique()

    folder_hazards = os.path.join(DATA_PROCESSED, iso3, 'hazards', hazard_type)
    hazard_filenames = os.listdir(folder_hazards)#[:5]

    for hazard_filename in hazard_filenames:

        if not ".tif" in hazard_filename:
            continue
        if ".xml" in hazard_filename:
            continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in hazard_filename:
        #     continue

        path_in = os.path.join(folder_hazards, hazard_filename)

        print("Working on {}, {}".format(hazard_filename, hazard_type))

        output = []
        site_count = []

        for region in region_ids:

            filename = '{}.csv'.format(region)
            folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower())
            path = os.path.join(folder, filename)

            if not os.path.exists(path):
                continue

            sites = pd.read_csv(path)#[:10]

            failures = 0

            for idx, site in sites.iterrows():
                
                x = float(site['cellid4326'].split('_')[0])
                y = float(site['cellid4326'].split('_')[1])

                with rasterio.open(path_in) as src:

                    src.kwargs = {'nodata':255}

                    coords = [(x, y)]

                    value = [sample[0] for sample in src.sample(coords)][0]

                    # if depth < 0:
                    #     depth = 0

                    if not value > 0:
                        continue

                    if value == 255:
                        continue

                    output.append({
                        'radio': site['radio'],
                        'mcc': site['mcc'],
                        'net': site['net'],
                        'area': site['area'],
                        'cell': site['cell'],
                        # 'gid_level': gid_level,
                        gid_level: region,
                        'cellid4326': site['cellid4326'],
                        'cellid3857': site['cellid3857'],
                        'value': value,
                    })

            results_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells') #, 'csv_files'
            if not os.path.exists(results_folder):
                os.makedirs(results_folder)
            path_out = os.path.join(results_folder, "number_of_cells.csv")
            if not os.path.exists(path_out):
                sites = sites[['radio', 'gid_id']]
                sites['count'] = 1
                sites = sites.groupby(['radio', 'gid_id'], as_index=False)['count'].sum()
                sites = sites.to_dict('records')
                site_count = site_count + sites

        if not os.path.exists(path_out):
            site_count = pd.DataFrame(site_count)
            site_count.to_csv(path_out, index=False)

        if len(output) == 0:
            return
        output = pd.DataFrame(output)

        step1_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'step1')
        if not os.path.exists(step1_folder):
            os.makedirs(step1_folder)
        path_out = os.path.join(step1_folder, hazard_filename.replace(".tif", ".csv"))
        output.to_csv(path_out)

    return


def estimate_landslide_vuln_cells(country, hazard_type):
    """
    Estimate landslide vulnerability for cells.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    # filename = 'fragility_curve_cells.csv'
    # path_fragility = os.path.join(DATA_RAW, filename)
    # low, baseline, high = load_f_curves(path_fragility)

    folder_shapes = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'step1')
    if not os.path.exists(folder_shapes):
        return
    cells_shapes = os.listdir(folder_shapes)

    for filename in cells_shapes:

        # if not ".shp" in filename:
        #     continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
        #     continue

        print("Working on {}".format(filename))

        output = []

        path_cells = os.path.join(folder_shapes, filename)
        cells = pd.read_csv(path_cells)#[:10]

        for idx, cell_row in cells.iterrows():

            if int(float(cell_row['value'])) == 1:
                risk_cat = 'no_risk'
            elif int(float(cell_row['value'])) == 2:
                risk_cat = 'low_risk'
            elif int(float(cell_row['value'])) == 3:
                risk_cat = 'medium_risk'
            elif int(float(cell_row['value'])) == 4:
                risk_cat = 'high_risk'
            else:
                risk_cat = 'unknown'

            output.append({
                gid_level: cell_row[gid_level],
                # 'gid_id': cell_row['gid_id'],
                'risk_cat': risk_cat,
                'risk_value': int(float(cell_row['value'])),
                # 'length_m': cell_row['length_m'],
                # 'total_m': cell_row['total_m'],
                # 'asset_cost_usd': country['cell_cost_usd'],
                # 'damage_low': damage_low,
                # 'damage_baseline': damage_baseline,
                # 'damage_high': damage_high,
                # 'cost_usd_low': round(country['cell_cost_usd'] * damage_low),
                # 'cost_usd_baseline':  round(country['cell_cost_usd'] * damage_baseline),
                # 'cost_usd_high':  round(country['cell_cost_usd'] * damage_high),
            })

        if len(output) == 0:
            continue

        # results_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'csv_files', 'disaggregated')
        # if not os.path.exists(results_folder):
        #     os.makedirs(results_folder)
        # path_out = os.path.join(results_folder, filename.replace('.shp', '.csv'))

        output = pd.DataFrame(output)
        # output.to_csv(path_out, index=False)

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells')#, 'csv_files', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, 'assets_by_risk_cat.csv')
        output["count"] = 1
        output = output[[gid_level, "count", "risk_cat", "risk_value"]]
        output = output.groupby(["risk_cat", "risk_value"], as_index=False).sum()
        output.to_csv(path_out, index=False)

    return


def estimate_flooding_vuln_cells(country, asset_type, hazard_type):
    """
    Estimate flooding vulnerability for cells.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_level = "GID_{}".format(gid_region)

    filename = 'fragility_curve_cells.csv'
    path_fragility = os.path.join(DATA_RAW, filename)
    low, baseline, high = load_f_curves(path_fragility)

    folder_shapes = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'step1')
    if not os.path.exists(folder_shapes):
        return
    cells_shapes = os.listdir(folder_shapes)

    for filename in cells_shapes:

        # if not ".shp" in filename:
        #     continue

        # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
        #     continue

        print("Working on {}".format(filename))

        output = []

        path_cells = os.path.join(folder_shapes, filename)
        cells = pd.read_csv(path_cells)#[:10]

        for idx, cell_row in cells.iterrows():

            damage_low = query_fragility_curve(low, cell_row['value'])
            damage_baseline = query_fragility_curve(baseline, cell_row['value'])
            damage_high = query_fragility_curve(high, cell_row['value'])

            output.append({
                gid_level: cell_row[gid_level],
                # 'gid_id': cell_row['gid_id'],
                'depth_m': cell_row['value'],
                # 'length_m': cell_row['length_m'],
                # 'total_m': cell_row['total_m'],
                'asset_cost_usd': country['cell_cost_usd'],
                'damage_low': damage_low,
                'damage_baseline': damage_baseline,
                'damage_high': damage_high,
                'cost_usd_low': round(country['cell_cost_usd'] * damage_low),
                'cost_usd_baseline':  round(country['cell_cost_usd'] * damage_baseline),
                'cost_usd_high':  round(country['cell_cost_usd'] * damage_high),
            })

        if len(output) == 0:
            continue

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'csv_files', 'disaggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, filename.replace('.shp', '.csv'))

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

        results_folder = os.path.join(RESULTS, iso3, hazard_type, 'cells', 'csv_files', 'aggregated')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        path_out = os.path.join(results_folder, filename.replace('.shp', '.csv'))
        output["count"] = 1
        output = output[[gid_level, "count", "cost_usd_low", "cost_usd_baseline","cost_usd_high"]]
        output = output.groupby([gid_level], as_index=False).sum()
        output.to_csv(path_out, index=False)

    return


def aggregate_results_cells(country): #, outline, dimensions, shapes):
    """
    Bar plot of river damage costs.

    """
    iso3 = country['iso3']
    name = country['country']
    gid_level = "GID_{}".format(country['gid_region'])

    filename = "number_of_cells.csv"
    folder = os.path.join(RESULTS, iso3, 'inunriver', 'cells')
    path = os.path.join(folder, filename)
    number_of_cells = pd.read_csv(path)
    total_cells = round(number_of_cells['count'].sum())

    folder = os.path.join(RESULTS, iso3, 'inunriver', 'cells', 'csv_files', 'aggregated')
    filenames = os.listdir(folder)

    output = []

    for filename in filenames:

        path = os.path.join(folder, filename)

        data = pd.read_csv(path)

        cells_at_risk = round(data['count'].sum())
        cells_at_risk_perc = round(cells_at_risk / total_cells * 100, 1)

        hazard_type = filename.split('_')[0]
        scenario = filename.split('_')[1]
        model = filename.split('_')[2]
        year = filename.split('_')[3]
        return_period = filename.split('_')[4]
        return_period = return_period.replace('.csv', '')

        output.append({
            'hazard_type': hazard_type,
            'scenario': scenario,
            'model': model,
            'year': year,
            'return_period': return_period,
            'filename': filename,
            'cells_at_risk': cells_at_risk,
            'total_cells': total_cells,
            'cells_at_risk_perc': cells_at_risk_perc
        })

    output = pd.DataFrame(output)

    filename = os.path.join('inunriver_aggregated_results.csv')
    folder = os.path.join(RESULTS, iso3, 'inunriver', 'cells', 'csv_files')
    path_out = os.path.join(folder, filename)
    output.to_csv(path_out, index=False)

    filename = os.path.join('inunriver_aggregated_cell_results.csv')
    folder = os.path.join(BASE_PATH, '..', 'vis', 'figures', iso3, 'scenario_results')
    path_out = os.path.join(folder, filename)
    if not os.path.exists(folder):
        os.makedirs(folder)
    output.to_csv(path_out, index=False)

    return


if __name__ == '__main__':

    filename = 'countries.csv'
    path = os.path.join(DATA_RAW, filename)
    countries = pd.read_csv(path, encoding='latin-1')

    hazard_types = [
        # 'inunriver',
        'inuncoast',
        # 'landslide'
    ]

    asset_types = [
        'fiber',
        'cells'
    ]

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

        for asset_type in asset_types:

            for hazard_type in hazard_types:

                if asset_type == 'fiber':

                    print('-- {}: {}: {} --'.format(country['iso3'], asset_type, hazard_type))

                    intersect_hazard_fiber(country, hazard_type)

                    if hazard_type in ['inunriver', 'inuncoastal']:
                        estimate_flooding_vuln_fiber(country, asset_type, hazard_type)
                        aggregate_results_fiber(country, hazard_type)
                    elif hazard_type == 'landslide':
                        estimate_landslide_vuln_fiber(country, hazard_type) #results will be plotted in R. See vis/[iso3].r scripts

                if asset_type == 'cells':

                    print('-- {}: {}: {} --'.format(country['iso3'], asset_type, hazard_type))

                    intersect_hazard_cells(country, hazard_type)
                    
                    if hazard_type in ['inunriver', 'inuncoastal']:
                        estimate_flooding_vuln_cells(country, asset_type, hazard_type)
                        aggregate_results_cells(country) #results will be plotted in R. See vis/[iso3].r scripts
                    elif hazard_type == 'landslide':
                        estimate_landslide_vuln_cells(country, hazard_type) #results will be plotted in R. See vis/[iso3].r scripts
                    
                    