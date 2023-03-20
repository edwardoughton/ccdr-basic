"""
Visualize unconnected population to hazards.

Written by Ed Oughton.

May 4th 2022

"""
import os
import sys
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as cx
import geopy as gp
from math import ceil

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')
REPORTS = os.path.join(BASE_PATH, '..', 'reports', 'images')




def process_inunriver(country):
    """
    Process river flooding.

    """
    iso3 = country['iso3']

    models = [
        '00000NorESM1-M',
        '0000GFDL-ESM2M',
        '0000HadGEM2-ES',
        '00IPSL-CM5A-LR',
        'MIROC-ESM-CHEM',
    ]

    for model in models:

        my_files = [
            ('inunriver_rcp8p5_{}_2080_rp01000.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00100.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00050.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00025.tif'.format(model))
        ]

        for my_file in my_files:

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
            if not os.path.exists(folder):
                os.mkdir(folder)
            path_out = os.path.join(folder, my_file)

            if os.path.exists(path_out):
                continue

            path = os.path.join(DATA_RAW,'flood_hazard', my_file)

            hazard = rasterio.open(path, 'r+')
            hazard.nodata = 255
            hazard.crs.from_epsg(4326)

            path_country = os.path.join(DATA_PROCESSED, iso3,
                'national_outline.shp')

            if os.path.exists(path_country):
                country = gpd.read_file(path_country)
            else:
                print('Must generate national_outline.shp first' )

            geo = gpd.GeoDataFrame({'geometry': country.geometry})
            coords = [json.loads(geo.to_json())['features'][0]['geometry']]

            out_img, out_transform = mask(hazard, coords, crop=True)
            out_meta = hazard.meta.copy()
            out_meta.update({"driver": "GTiff",
                            "height": out_img.shape[1],
                            "width": out_img.shape[2],
                            "transform": out_transform,
                            "crs": 'epsg:4326'})

            with rasterio.open(path_out, "w", **out_meta) as dest:
                    dest.write(out_img)

    return


def extract_inunriver(country):
    """
    Extract river flooding.

    """
    iso3 = country['iso3']

    models = [
        '00000NorESM1-M',
        '0000GFDL-ESM2M',
        '0000HadGEM2-ES',
        '00IPSL-CM5A-LR',
        'MIROC-ESM-CHEM',
    ]

    for model in models:

        my_files = [
            ('inunriver_rcp8p5_{}_2080_rp01000.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00100.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00050.tif'.format(model)),
            ('inunriver_rcp8p5_{}_2080_rp00025.tif'.format(model))
        ]

        for my_file in my_files:

            filename = my_file.replace('.tif','')

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
            if not os.path.exists(folder):
                os.mkdir(folder)
            path_out = os.path.join(folder, filename + '.shp')

            if os.path.exists(path_out):
                continue

            filename = 'national_outline.shp'
            folder = os.path.join(DATA_PROCESSED, iso3)
            path = os.path.join(folder, filename)
            national_outline = gpd.read_file(path, crs='epsg:4326')

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
            if not os.path.exists(folder):
                os.mkdir(folder)
            path = os.path.join(folder, my_file)

            with rasterio.open(path) as src:

                affine = src.transform
                array = src.read(1)#[:1]

                output = []

                for vec in rasterio.features.shapes(array):

                    if vec[1] > 0 and not vec[1] == 255:

                        coordinates = [i for i in vec[0]['coordinates'][0]]

                        coords = []

                        for i in coordinates:

                            x = i[0]
                            y = i[1]

                            x2, y2 = src.transform * (x, y)

                            coords.append((x2, y2))

                        output.append({
                            'type': vec[0]['type'],
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords],
                            },
                            'properties': {
                                'value': vec[1],
                            }
                        })

                output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')
                output.to_file(path_out, driver='ESRI Shapefile')

    return


def plot_inuncoast_uncovered(country, outline, path, background, main_title, dimensions):
    """
    Plot coastal uncovered population by region.

    """
    iso3 = country['iso3']
    name = country['country']

    fig, (ax1, ax2) = plt.subplots(2, 2, figsize=dimensions)
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    minx, miny, maxx, maxy = outline.total_bounds
    buffer = 2
    for ax in [ax1, ax2]:
        for dim in [0,1]:
            ax[dim].set_xlim(minx-(buffer-1), maxx+(buffer+1))
            ax[dim].set_ylim(miny-0.1, maxy+.1)

    fig.set_facecolor('gainsboro')

    for ax in [ax1, ax2]:
        for dim in [0,1]:
            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inuncoast')
            path1 = os.path.join(folder, 'inuncoast_rcp8p5_wtsub_2080_rp1000_0_perc_50.shp')
            if os.path.exists(path1):
                ##Not sure there actually is a shapefile for this hazard yet
                hazard = gpd.read_file(path1, crs='epsg:3857')
                hazard = hazard.to_crs(4326)
                hazard.plot(color='black', linewidth=1.5, alpha=1,
                    legend=True, edgecolor='black', ax=ax[dim])
                cx.add_basemap(ax[dim], crs='epsg:4326')
            else:
                outline['coastal'] = ['No Risk']
                # hazard.plot(color='black', linewidth=1.5, alpha=1,
                #     legend=True, edgecolor='black', ax=ax[dim])
                outline = outline.to_crs(4326)
                outline.plot(column='coastal', cmap='Greys',
                    linewidth=0, alpha=.5, #column='ws4038tl', cmap='viridis'
                    legend=True, edgecolor='black', ax=ax[dim])
                cx.add_basemap(ax[dim], crs='epsg:4326')

    my_files = [
        ('baseline_uncovered_GSM.shp', ax1[0]),
        ('baseline_uncovered_UMTS.shp', ax1[1]),
        ('baseline_uncovered_LTE.shp', ax2[0]),
        ('baseline_uncovered_NR.shp', ax2[1])
    ]

    if background == 1:
        for my_file in my_files:

            folder = os.path.join(DATA_PROCESSED, iso3, 'coverage')
            path1 = os.path.join(folder, my_file[0])
            if os.path.exists(path1):
                layer = gpd.read_file(path1, crs='epsg:3857')
                layer = layer.to_crs(4326)
                layer.plot(column='covered', cmap='viridis_r', linewidth=0.01, alpha=.5,
                    legend=True, edgecolor='grey', ax=my_file[1])
            else:
                layer = gpd.read_file(os.path.join(folder, '..', 'national_outline.shp'), crs='epsg:4326')
                layer['covered'] = 'Uncovered'
                layer.plot(column='covered', cmap='viridis', linewidth=0.01, alpha=.5,
                    legend=True, edgecolor='grey', ax=my_file[1])

    ax1[0].set_title('2G GSM Uncovered')
    ax1[1].set_title('3G UMTS Uncovered')
    ax2[0].set_title('4G LTE Uncovered')
    ax2[1].set_title('5G NR Uncovered')

    filename = 'core_edges_existing.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
    path_fiber = os.path.join(folder, filename)
    if os.path.exists(path_fiber):
        fiber = gpd.read_file(path_fiber, crs='epsg:4326')
        fiber.plot(color='orange', lw=2, ax=ax1[0])
        fiber.plot(color='orange', lw=2, ax=ax1[1])
        fiber.plot(color='orange', lw=2, ax=ax2[0])
        fiber.plot(color='orange', lw=2, ax=ax2[1])

    plt.legend(['Fiber', '2G GSM', '3G UMTS', '4G LTE', '5G NR' ], loc='lower right', title='Assets')

    fig.tight_layout()

    plt.suptitle(main_title, fontsize=20, y=1.03)

    plt.savefig(path,
    pad_inches=0.4,
    bbox_inches='tight',
    dpi=600,
    )
    plt.close()


def plot_inunriver_uncovered(country, outline, path, dimensions):
    """
    Plot river uncovered population by region.

    """
    iso3 = country['iso3']
    name = country['country']

    models = [
        '00000NorESM1-M',
        '0000GFDL-ESM2M',
        '0000HadGEM2-ES',
        '00IPSL-CM5A-LR',
        'MIROC-ESM-CHEM',
    ]

    return_periods = [
        'rp01000',
        'rp00100',
        'rp00050',
        'rp00025'
    ]

    for rp in return_periods:
        for model in models:

            fig, ax = plt.subplots(1, 1, figsize=dimensions)
            fig.subplots_adjust(hspace=.3, wspace=.1)
            fig.set_facecolor('gainsboro')

            minx, miny, maxx, maxy = outline.total_bounds
            buffer = 2
            ax.set_xlim(minx-(buffer-1), maxx+(buffer+1))
            ax.set_ylim(miny-0.1, maxy+.1)

            fig.set_facecolor('gainsboro')

            filename = 'core_edges_existing.shp'
            folder = os.path.join(DATA_PROCESSED, iso3, 'network_existing')
            path_fiber = os.path.join(folder, filename)
            if os.path.exists(path_fiber):
                fiber = gpd.read_file(path_fiber, crs='epsg:4326')
                fiber.plot(color='orange', lw=1, ax=ax)

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

            folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
            filename = 'inunriver_rcp8p5_{}_2080_{}.shp'.format(model, rp)
            path1 = os.path.join(folder, filename)
            if os.path.exists(path1):
                hazard = gpd.read_file(path1, crs='epsg:3857')
                hazard = hazard.to_crs(4326)
                hazard.plot(color='black', linewidth=1.5, alpha=.5,
                    legend=True, edgecolor='black', ax=ax)
                cx.add_basemap(ax, crs='epsg:4326')

            plt.legend(
                ['Fiber', '2G GSM', '3G UMTS', '4G LTE', '5G NR' ],
                loc='lower right',
                title='Assets'
            )

            fig.tight_layout()

            main_title = 'Projected River Flooding: {}, {}, {}, 2080'.format(name, model, rp)
            plt.suptitle(main_title, fontsize=20, y=1.03)

            plt.savefig(path.replace('.tiff', '_{}_{}.tiff'.format(model, rp)),
            pad_inches=0.4,
            bbox_inches='tight',
            dpi=600,
            )
            plt.close()


# def plot_inunriver_multi_rp(country, outline, path, dimensions):
#     """
#     Plot river uncovered population by region.

#     """
#     iso3 = country['iso3']
#     name = country['country']

#     folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
#     filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp01000.shp'
#     path1 = os.path.join(folder, filename)
#     rp01000 = gpd.read_file(path1, crs='epsg:3857')
#     rp01000['rp'] = 'rp01000'
#     rp01000['color'] = 'blue'

#     filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00100.shp'
#     path1 = os.path.join(folder, filename)
#     rp00100 = gpd.read_file(path1, crs='epsg:3857')
#     rp00100['rp'] = 'rp00100'
#     rp00100['color'] = 'purple'

#     filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00050.shp'
#     path1 = os.path.join(folder, filename)
#     rp00050 = gpd.read_file(path1, crs='epsg:3857')
#     rp00050['rp'] = 'rp00050'
#     rp00050['color'] = 'orange'

#     filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00050.shp'
#     path1 = os.path.join(folder, filename)
#     rp00025 = gpd.read_file(path1, crs='epsg:3857')
#     rp00025['rp'] = 'rp00025'
#     rp00025['color'] = 'yellow'

#     hazard = gpd.GeoDataFrame(
#         pd.concat([rp01000, rp00100, rp00050, rp00025], ignore_index=True), crs=rp01000.crs)

#     hazard = hazard.to_crs(4326)

#     fig = plt.figure(figsize=(10,10))
#     ax = fig.add_subplot(1,1,1)

#     hazard.plot(ax=ax,
#     color=hazard['color'],
#                 column=hazard['rp'],
# #                 alpha=1,
#                 edgecolor=hazard['color'],
#                 legend=True)

#     plt.savefig(path,
#         pad_inches=0.4,
#         bbox_inches='tight',
#         dpi=600,
#     )
#     plt.close()


def plot_inunriver_multi_rp(country, outline, path, dimensions):
    """
    Plot river uncovered population by region.

    """
    iso3 = country['iso3']
    name = country['country']

    fig = plt.figure(figsize=(10,10))
    ax = fig.add_subplot(1,1,1)

    folder = os.path.join(DATA_PROCESSED, iso3, 'hazards', 'inunriver')
    filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp01000.shp'
    path1 = os.path.join(folder, filename)
    rp01000 = gpd.read_file(path1, crs='epsg:3857')
    rp01000 = rp01000.to_crs(4326)
    rp01000['rp'] = 'rp01000'
    rp01000['color'] = 'blue'
    rp01000.plot(ax=ax,
                color=rp01000['color'],
                #column=rp01000['rp'],
                # alpha=1,
                # edgecolor=None,
                legend=True,
                # label='rp01000'
                )

    filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00100.shp'
    path1 = os.path.join(folder, filename)
    rp00100 = gpd.read_file(path1, crs='epsg:3857')
    rp00100 = rp00100.to_crs(4326)
    rp00100['rp'] = 'rp00100'
    rp00100['color'] = 'red'
    rp00100.plot(ax=ax,
                color=rp00100['color'],
                #column=rp00100['rp'],
                # alpha=1,
                # edgecolor=None,
                legend=True,
                # label='rp00100'
                )

    filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00050.shp'
    path1 = os.path.join(folder, filename)
    rp00050 = gpd.read_file(path1, crs='epsg:3857')
    rp00050 = rp00050.to_crs(4326)
    rp00050['rp'] = 'rp00050'
    rp00050['color'] = 'orange'
    rp00050.plot(ax=ax,
                color=rp00050['color'],
                #column=rp00050['rp'],
                # alpha=1,
                # edgecolor=None,
                legend=True,
                # label='rp00050'
                )

    filename = 'inunriver_rcp8p5_00IPSL-CM5A-LR_2080_rp00025.shp'
    path1 = os.path.join(folder, filename)
    rp00025 = gpd.read_file(path1, crs='epsg:3857')
    rp00025 = rp00025.to_crs(4326)
    rp00025['rp'] = 'rp00025'
    rp00025['color'] = 'yellow'
    rp00025.plot(ax=ax,
                color=rp00025['color'],
                #column=rp00025['rp'],
                # alpha=.5,
                # edgecolor=None,
                legend=True,
                # label='rp00025'
                )

        # hazard.plot(color='black', linewidth=1.5, alpha=.5,
        #     legend=True, edgecolor='black', ax=ax)
    cx.add_basemap(ax, crs='epsg:4326')

    plt.legend()
    main_title = 'Projected River Flooding: {} 2080'.format(name)
    plt.suptitle(main_title, fontsize=20, y=1.03)

    plt.savefig(path,
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

        if not country['iso3'] in ['AZE']:#, 'KEN']:#, 'KEN']: #['KEN']
            continue

        print('processing rivers')
        process_inunriver(country) #river flooding

        print('extracting rivers')
        extract_inunriver(country)

        dimensions = (int(country['dimensions_y']), int(country['dimensions_x']))
        iso3 = country['iso3']
        country['figsize'] = (8,10)

        print('-- {} --'.format(iso3))

        folder_reports = os.path.join(REPORTS, iso3)
        if not os.path.exists(folder_reports):
            os.makedirs(folder_reports)

        folder_vis = os.path.join(VIS, iso3)
        if not os.path.exists(folder_vis):
            os.makedirs(folder_vis)

        filename = 'regions_{}_{}.shp'.format(country['lowest'], iso3)
        path = os.path.join(DATA_PROCESSED, iso3, 'regions', filename)
        shapes = gpd.read_file(path, crs='epsg:4326')

        filename = 'national_outline.shp'
        path = os.path.join(DATA_PROCESSED, iso3, filename)
        outline = gpd.read_file(path, crs='epsg:4326')

        # path = os.path.join(folder_vis, '{}_inuncoast_uncovered_no-background.tiff'.format(iso3))
        # # # if not os.path.exists(path):
        # main_title = 'Coastal Flooding Areas: {}'.format(country['country'])
        # plot_inuncoast_uncovered(country, outline, path, 0, main_title, dimensions)

        path = os.path.join(folder_vis, '{}_inunriver_uncovered.tiff'.format(iso3))
        # if not os.path.exists(path):
        plot_inunriver_uncovered(country, outline, path, dimensions)

        # path = os.path.join(folder_vis, '{}_inunriver_multi-rp.tiff'.format(iso3))
        # plot_inunriver_multi_rp(country, outline, path, dimensions)
