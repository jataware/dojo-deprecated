'''
Usage: 
    python run_chirps_tiff.py --name=CHIRPS --month=01 --year=2020 --bbox='[33.512234, 2.719907, 49.98171,16.501768]' --statistic=mm_data

Requirements:
    pyproj==2.6.1.post1
    mixmasta==0.5.19
'''

import requests
import logging
from pyproj import Proj, transform
import argparse
import json
import sys
import warnings
from mixmasta import mixmasta as mix
from datetime import datetime

if not sys.warnoptions:
    warnings.simplefilter("ignore")


class CHIRPSController(object):
    """
    A controller to manage CHIRPS model execution.
    """

    def __init__(self, name, month, year, bbox, statistic, day_of_year=None):
        logging.basicConfig(level=logging.INFO)        
        self.name = name
        self.stat = statistic
        self.day_of_year = day_of_year
        self.month = month
        self.year = year
        self.bbox = json.loads(bbox)
        self.min_pt, self.max_pt = self.convert_bbox(self.bbox)
        stat_secondary = {'mm_data': 'Data'}
        self.url = f"https://chc-ewx2.chc.ucsb.edu/proxies/wcsProxy.php?layerNameToUse=chirps:"\
                   f"chirps_africa_1-month-{self.month}-{self.year}_{self.stat}"\
                   f"&lowerLeftXToUse={self.min_pt[0]}&lowerLeftYToUse={self.min_pt[1]}"\
                   f"&upperRightXToUse={self.max_pt[0]}&upperRightYToUse={self.max_pt[1]}"\
                   f"&wcsURLToUse=https://chc-ewx2.chc.ucsb.edu:8443/geoserver/wcs?&resolution=0.05&srsToUse=EPSG:3857&outputSrsToUse=EPSG:4326"
        self.url_gefs = f"https://chc-ewx2.chc.ucsb.edu/proxies/wcsProxy.php?layerNameToUse=chirpsgefs15day2:chirpsgefs15day2_africa_1"\
                        f"-day-{self.day_of_year}-{self.year}_{self.stat}&TILED=true&mapperWMSURL="\
                        f"&lowerLeftXToUse={self.min_pt[0]}&lowerLeftYToUse={self.min_pt[1]}"\
                        f"&upperRightXToUse={self.max_pt[0]}&upperRightYToUse={self.max_pt[1]}"\
                        f"&wcsURLToUse=https://chc-ewx2.chc.ucsb.edu:8443/geoserver/wcs?&resolution=0.05&srsToUse=EPSG:3857&outputSrsToUse=EPSG:4326"

        self.features = {'mm_data': {
                                'feature_name': 'Rainfall',
                                'feature_description': 'rainfall in mm per 5km',
                                'run_description': f'{self.name} rainfall data'
                                    },
                        'mm_anomaly': {
                                'feature_name': 'Rainfall relative to average',
                                'feature_description': 'Rainfall relative to the historic average in mm per 5km',
                                'run_description': f'{self.name} anomaly data'
                                    },
                        'none_z-score': {
                                'feature_name': 'SPI',
                                'feature_description': 'Standardized Precipitation Index',
                                'run_description': f'{self.name} Standardized Precipitation Index data'
                                    }
                        }

    def run_model(self):
        """
        Obtain CHIRPS data
        """
        logging.info(self.url_gefs)
        try:
            # if CHIRPS-GEFS, use that URL
            if self.name == 'CHIRPS-GEFS':
                data = requests.get(self.url_gefs)

            # otherwise, use CHRIPS URL 
            else:
                data = requests.get(self.url)
                
            logging.info("Model run: SUCCESS")

            with open("results/chirps.tiff", "wb") as f:
                f.write(data.content)
        except Exception as e:
            logging.error(f"CHIRPS Fail: {e}")


    def convert_bbox(self, bb):
        """
        Convert WGS84 coordinate system to Web Mercator
        Initial bbox is in format [xmin, ymin, xmax, ymax]. 
        x is longitude, y is latitude.
        Output is Web Mercator min/max points for a bounding box.
        """
        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:3857')
        min_pt = transform(in_proj, out_proj, bb[0], bb[1])
        max_pt = transform(in_proj, out_proj, bb[2], bb[3])
        return min_pt, max_pt  
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CHIRPS runner')
    parser.add_argument('--name', type=str, help='CHIRPS or CHIRPS-GEFS')
    parser.add_argument('--day_of_year', type=str, help='day of year (1 to 365)', default=None)
    parser.add_argument('--month', type=int, help='month')
    parser.add_argument('--year', type=int, help='Year')
    parser.add_argument('--bbox', type=str, help='The bounding box to obtain')
    parser.add_argument('--statistic', choices=['mm_data','mm_anomaly','none_z-score'], help='The statistic to fetch')
    args = parser.parse_args()    

    if len(str(args.month)) == 1:
        month = f"0{args.month}"
    else:
        month = args.month

    runner = CHIRPSController(args.name, month, args.year, args.bbox, args.statistic, args.day_of_year)
    runner.run_model()

    if args.name == 'CHIRPS-GEFS':
        date = datetime.strptime(f"{args.year}-{args.day_of_year}", "%Y-%j").strftime("%m-%d-%Y")
    else:
        date = f"{month}/01/{args.year}"
    df = mix.raster2df('results/chirps.tiff', feature_name='rainfall', band=1, date=date)
    df['type'] = runner.features[args.statistic]['feature_name']
    df.to_csv('results/chirps.csv', index=False)