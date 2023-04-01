"""
Process opencellid data.

Written by Ed Oughton.

March 2023

"""
import os
import configparser
import pandas as pd
import rasterio
import geopandas as gpd

from misc import get_countries, get_scenarios, get_regions

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def intersect_hazard(country, hazard_types): #, scenarios
    """
    Intersect infrastructure with hazards.

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
    hazard_filenames = os.listdir(folder_hazards)#[:15]

    for hazard_filename in hazard_filenames:

        if not ".tif" in hazard_filename:
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

            sites = pd.read_csv(path)#[:100]

            failures = 0

            for idx, site in sites.iterrows():

                x = float(site['cellid4326'].split('_')[0])
                y = float(site['cellid4326'].split('_')[1])

                with rasterio.open(path_in) as src:

                    src.kwargs = {'nodata':255}

                    coords = [(x, y)]

                    depth = [sample[0] for sample in src.sample(coords)][0]

                    # if depth < 0:
                    #     depth = 0

                    if not depth > 0:
                        continue

                    if depth == 255:
                        continue

                    output.append({
                        'radio': site['radio'],
                        'mcc': site['mcc'],
                        'net': site['net'],
                        'area': site['area'],
                        'cell': site['cell'],
                        'gid_level': gid_level,
                        'gid_level': region,
                        'cellid4326': site['cellid4326'],
                        'cellid3857': site['cellid3857'],
                        'depth': depth,
                    })

            results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'cells') #, 'csv_files'
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

        step1_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'cells', 'step1')
        if not os.path.exists(step1_folder):
            os.makedirs(step1_folder)
        path_out = os.path.join(step1_folder, hazard_filename.replace(".tif", ".csv"))
        output.to_csv(path_out)


    return


def collect_data(country, hazard_type):
    """
    Collect data.

    """
    iso3 = country['iso3']
    gid_region = country['gid_region']
    gid_id = "GID_{}".format(gid_region)

    regions = get_regions(country, 1)
    region_ids = regions[gid_id].unique()

    scenarios = get_scenarios()
    scenarios = [os.path.basename(i).replace('.tif','') for i in scenarios]
    print(scenarios)
    # filename = 'fragility_curve.csv'
    # path_fragility = os.path.join(DATA_RAW, filename)
    # low, baseline, high = load_f_curves(path_fragility)

    # for region in region_ids:

    #     folder = os.path.join(DATA_PROCESSED, iso3, 'regional_data', region, 'flood_scenarios')
    #     if not os.path.exists(folder):
    #         continue
    #     path = os.path.join(folder, fiber_filename)





    # for fiber_filename in fiber_shapes:

    #     if not ".shp" in fiber_filename:
    #         continue

    #     # if not "inunriver_rcp8p5_MIROC-ESM-CHEM_2080_rp01000" in fiber_filename:
    #     #     continue

    #     print("Working on {}".format(fiber_filename))

    #     output = []

    #     path_fiber = os.path.join(folder_shapes, fiber_filename)
    #     fiber = gpd.read_file(path_fiber, crs='epsg:4326')#[:10]

    #     for idx, fiber_row in fiber.iterrows():

    #         damage_low = query_fragility_curve(low, fiber_row['value'])
    #         damage_baseline = query_fragility_curve(baseline, fiber_row['value'])
    #         damage_high = query_fragility_curve(high, fiber_row['value'])

    #         output.append({
    #             gid_level: fiber_row[gid_level],
    #             'depth_m': fiber_row['value'],
    #             'length_m': fiber_row['length_m'],
    #             # 'total_m': fiber_row['total_m'],
    #             'damage_low': damage_low,
    #             'damage_baseline': damage_baseline,
    #             'damage_high': damage_high,
    #             'cost_usd_low': round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_low),
    #             'cost_usd_baseline':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_baseline),
    #             'cost_usd_high':  round(fiber_row['length_m'] * country['fiber_cost_usd_m'] * damage_high),
    #         })

    #     if len(output) == 0:
    #         continue

    #     results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'csv_files', 'disaggregated')
    #     if not os.path.exists(results_folder):
    #         os.makedirs(results_folder)
    #     path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))

    #     output = pd.DataFrame(output)
    #     output.to_csv(path_out, index=False)

    #     results_folder = os.path.join(DATA_PROCESSED, iso3, 'results', hazard_type, 'fiber', 'csv_files', 'aggregated')
    #     if not os.path.exists(results_folder):
    #         os.makedirs(results_folder)
    #     path_out = os.path.join(results_folder, fiber_filename.replace('.shp', '.csv'))
    #     output = output[[gid_level, "length_m", "cost_usd_low", "cost_usd_baseline","cost_usd_high"]]
    #     output = output.groupby([gid_level], as_index=False).sum()
    #     output.to_csv(path_out, index=False)

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


if __name__ == "__main__":

    filename = "countries.csv"
    path = os.path.join(DATA_RAW, filename)

    countries = pd.read_csv(path, encoding='latin-1')

    scenarios = get_scenarios()

    hazard_types = [
        'inunriver',
        # 'inuncoast'
    ]

    for idx, country in countries.iterrows():

        if not country['iso3'] == "AZE":
            continue

        regions = get_regions(country, 1)

        for hazard_type in hazard_types:

        # for idx, region in regions.iterrows():

            intersect_hazard(country, hazard_type)

        # collect_data(country, 'inunriver')
