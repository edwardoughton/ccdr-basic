"""
Download Aquaduct data.

"""
import os
import configparser
from lxml import html
import requests
import urllib.request
from tqdm import tqdm

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')


def dl_flood_layers():
    """
    Download WRI Aqueduct flooding layers.
    """
    path = 'http://wri-projects.s3.amazonaws.com/AqueductFloodTool/download/v2/index.html'
    page = requests.get(path)
    webpage = html.fromstring(page.content)

    for in_path in tqdm(webpage.xpath('//a/@href')):

        if not in_path.endswith('.tif'):
            continue

        # if not 'inunriver_rcp4p5_00IPSL-CM5A-LR_2050_rp00250' in in_path:
        #     continue

        filename = os.path.basename(in_path)

        folder = os.path.join(DATA_RAW, 'flood_hazard')

        if not os.path.exists(folder):
            os.mkdir(folder)

        filename = "{}".format(filename)
        out_path = os.path.join(folder, filename)

        #if not os.path.exists(out_path):

        urllib.request.urlretrieve(in_path, out_path)

    return


if __name__ == "__main__":

    dl_flood_layers()
