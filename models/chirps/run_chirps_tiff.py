'''
Usage: 
    HELP
    ----
    python run_chirps_tiff.py --help

    CHIRPS
    ------
    Returns data for 1st day of specified month/year.
    python run_chirps_tiff.py --name=CHIRPS --month=01 --year=2021 --bbox='[[33.512234, 2.719907], [49.98171,16.501768]]'

    CHIRPS-GEFS
    -----------
    Returns data for 1st and 16th of specified month/year.
    python run_chirps_tiff.py --name=CHIRPS-GEFS --month=09 --year=2021 --bbox='[[33.512234, 2.719907], [49.98171,16.501768]]'

    CHIRTSmax
    ----------
    Returns data for 1st day of specified month/year.
    python3 run_chirps_tiff.py --name=CHIRTSmax --month=09 --year=2016 --bbox='[[33.512234, 2.719907], [49.98171,16.501768]]'


Requirements:
    pyproj==2.6.1.post1
    rioxarray==0.8.0
    mixmasta>=0.5.19
'''

import requests
import logging
from pyproj import Proj, transform
import argparse
import json
import sys
import warnings
from datetime import datetime
import pandas as pd
import numpy as np
import rioxarray as rxr
import os

if not sys.warnoptions:
    warnings.simplefilter("ignore")

# Product : {units_stat: column name } dictionary.
product_data = {
    'CHIRPS': { 'mm_data': 'rainfall', 'mm_anomaly': 'anomaly', 'none_z-score': 'z-score'},
    'CHIRPS-GEFS':  { 'mm_data': 'rainfall', 'mm_anomaly': 'anomaly', 'none_z-score': 'z-score'},
    'CHIRTSmax':  { 'C_data': 'temperature', 'C_anomaly': 'anomaly', 'none_z-score': 'z-score'}
}

class CHIRPSController(object):
    """
    A controller to manage CHIRPS model execution.
    """

    def __init__(self, name, month, year, bbox):
        logging.basicConfig(level=logging.INFO)  

        if not os.path.exists('results'):
            os.makedirs('results')

        # The controller objects methods use the object properties,
        # so these are set prior to calling self methods like run_model()

        # Ensure month is 2-digits
        if len(str(month)) == 1:
            self.month = f"0{month}"
        else:
            self.month = month
        self.day_of_year = None
        self.name = name
        self.year = year
        self.bbox = json.loads(bbox)
        self.min_pt, self.max_pt = self.convert_bbox(self.bbox)

        '''
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
        '''

    def convert_bbox(self, bb):
        """
        Convert WGS84 coordinate system to Web Mercator
        Initial bbox is in format [xmin, ymin, xmax, ymax].
        New bbox box format is [[xmin, ymin], [xmax, ymax]]
        x is longitude, y is latitude.
        Output is Web Mercator min/max points for a bounding box.
        """

        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:3857')

        if len(bb) == 2:
            # Convert new bbox format to old bbox format.
            bb = bb[0] + bb[1]
        
        min_pt = transform(in_proj, out_proj, bb[0], bb[1])
        max_pt = transform(in_proj, out_proj, bb[2], bb[3])
     
        return min_pt, max_pt  

    def process_download(self, df: pd.DataFrame, date: str):
        """
        Description
        -----------
            Read the file downloaded by run_model (which sets the download_filename)
            and add to the DataFrame parameter.

        Parameters
        ----------
            df: pd.DataFrame
                Working output dataframe of combined downloads.
            date: str
                Date string for the first download df or adding a df on axis 0 (rows).        

        Returns
        -------
            pd.DataFrame: the modified dataframe.

        """
        # Open the downloaded .tiff and convert to a dataframe; remove 'spatial-ref' column.
        ds = rxr.open_rasterio(self.download_filename, masked=True)
        feature_name = product_data[self.name][self.stat]
        df_model1 = ds.to_dataframe(name=feature_name)
        del df_model1['spatial_ref']

        # Add the date col or concatenate if not the first download.
        if df.empty:
            df_model1['date'] = date
            df = df_model1
        else:
            df = pd.concat([df, df_model1], axis = 1)

        # Remove download file.
        os.remove(self.download_filename)
        return df

    def run_model(self):
        """
        Description
        -----------
            Obtain CHIRPS data from URL. Writes to self.download_filename.
        
        Returns
        -------
            bool: False on failure, else True.
        """

        try:
            #logging.info(f'{self.url}\n')
            data = requests.get(self.url)        

            if 'ServiceException' in data.text:
                logging.error(f"Model {self.name} (run stat:{self.stat} day_of_year:{self.day_of_year} year: {self.year} month: {self.month}): FAILED\n")
                logging.error(f'{self.url}\n')
                logging.error(f'{data.content}\n')
                return False
            else:
                logging.info(f"Model {self.name} (run stat:{self.stat} day_of_year:{self.day_of_year} year: {self.year} month: {self.month}): SUCCESS\n")

                with open(self.download_filename, "wb") as f:
                    f.write(data.content)
                
                return True

        except Exception as e:
            logging.error(f"{self.name} Fail: {e}")
            return False

    def run_models(self):
        """
        Description
        -----------
            (1)
            Get geotiffs for the three stats using the existing self.run_model() method
            modified to append the saved filename with the current stat 
            e.g. results/chirps-mm_data.tiff.

            (2)
            Convert each saved tiff to a dataframe and append columns to earlier df.

            (3) 
            Flow control is by self.name i.e. CHIRPS, CHIRPS-GEFS, or CHIRTS-MAX

            (4) 
            CHIRPS-GEFS calculates the day-of-year for the 1st and 16th of the month, and 
            makes a call for each statistic for both day-of-years. The day-of-year DataFrames
            are concatenated by row. Therefore, the 'date' column will contain two unique dates.

        Output
        ------
            Saves concatenated dataframe to results/chirps.csv.
        """

        if self.name == 'CHIRPS-GEFS':
            # For CHIRPS-GEFS we download the 1st and 16th of the month,
            
            # set_days_of_year() returns a tuple of the day_of_year for the
            # 1st and 16th of self.month.
            self.set_days_of_year()

            # Init the two dataframes.
            df1 = pd.DataFrame()
            df16 = pd.DataFrame()

            # Cycle the two days_of_year
            for idx, doy in enumerate(self.days_of_year):
                # CHIRPS-GEFS has two unique date values.
                date = datetime.strptime(f"{self.year}-{doy}", "%Y-%j").strftime("%m-%d-%Y")
                
                # Cycle through the statistical data we want.
                for stat in product_data[self.name].keys():
                    # Set the temporary download filename.
                    self.download_filename = f"results/chirps-{stat}.tiff"
                    
                    # Set the runner's stat, doy and then the URL for CHIRPS-GEF.
                    self.stat = stat
                    self.day_of_year = doy
                    self.set_url_chirps_gefs()

                    # Retrieve the CHIRPS data for this statistic.
                    if not self.run_model():
                        logging.error('Run model failed to download data.')
                        continue
                    
                    # Process the downloaded file into the day_of_year dataframe. 
                    if idx == 0:
                        df1 = self.process_download(df1, date)
                    else:
                        df16 = self.process_download(df16, date)

            # Concat the two day_of_year dataframes by row.
            df = pd.concat([df1, df16], axis=0)

        elif self.name in ['CHIRPS', 'CHIRTSmax']:
            # For these we download only the 1st of the month, so that is
            # the only value in the date column.
            date = f"{self.month}/01/{self.year}"

            # Init the result dataframe.
            df = pd.DataFrame()

            # Cycle through the statistical data we want.
            for stat in product_data[self.name].keys():
                # Set temporary download filename.
                self.download_filename = f"results/chirps-{stat}.tiff"                
                
                # Set the runner's stat.
                self.stat = stat

                # Set the url for the product.
                if self.name == 'CHIRPS':
                    self.set_url_chirps()
                elif self.name == 'CHIRTSmax':
                    self.set_url_chirts_max()
                else:
                    logging.error(f'No URL set for product {self.name}.')
                    return

                # Retrieve the CHIRPS data for this statistic.
                if not self.run_model():
                    logging.error('Run model failed: stopping.')
                    return

                # Process the downloaded file into the dataframe.
                df = self.process_download(df, date)
        else:
            logging.error(f'{self.name} is not a recognized product.')
            return

        # Process the dataframe produced above.
        if not df.empty:
            # (1) Convert the MultiIndex to columns.
            df.reset_index(inplace=True)
            # (2) Remove the 'band' column
            del df['band']
            # (3) Reorder the columns for those product columns for which we have data.
            cols = list(set(df.columns) & set(product_data[self.name].values()))
            cols = ['x','y','date'] + cols
            df = df[cols]

        # Replace CHIRPS specific null value (-9999) with NaN
        df = df.replace(-9999, np.nan)

        # Write output and log completion with header and tail previews.
        df.to_csv('results/chirps.csv')
        logging.info('Processing completed. Output to results/chirps.csv. Header and tail preview:')
        logging.info(df.head())
        logging.info(df.tail())

    def set_days_of_year(self):
        """
        Description
        -----------
            Used for CHIRP-GEFS when month is passed. 
            Set list of day-of-years for the 1st and 16th of the self.month or self.day_of_year.

        Returns
        -------
            [int] : array of day-of-year ints.
        """
        if self.month != None:
            date = datetime.strptime(f"{self.month}/01/{self.year}", "%m/%d/%Y")
            
        else:
            # day_of_year passed
            date = datetime.strptime(f"{self.year}-{self.day_of_year}", "%Y-%j").strftime("%m-1-%Y")

        doy = date.timetuple().tm_yday
        self.days_of_year = [doy, doy + 15]

    def set_url_chirts_max(self):
        self.url = f"https://chc-ewx2.chc.ucsb.edu/proxies/wcsProxy.php?layerNameToUse=chirtsmax:"\
            f"chirtsmax_africa_1-month-{self.month}-{self.year}_{self.stat}" \
            f"&lowerLeftXToUse={self.min_pt[0]}&lowerLeftYToUse={self.min_pt[1]}" \
            f"&upperRightXToUse={self.max_pt[0]}&upperRightYToUse={self.max_pt[1]}" \
            f"&wcsURLToUse=https://chc-ewx2.chc.ucsb.edu:8443/geoserver/wcs?"\
            f"&resolution=0.05&srsToUse=EPSG:3857&outputSrsToUse=EPSG:4326"

    def set_url_chirps(self):
        self.url = f"https://chc-ewx2.chc.ucsb.edu/proxies/wcsProxy.php?layerNameToUse=chirps:"\
                   f"chirps_africa_1-month-{self.month}-{self.year}_{self.stat}"\
                   f"&lowerLeftXToUse={self.min_pt[0]}&lowerLeftYToUse={self.min_pt[1]}"\
                   f"&upperRightXToUse={self.max_pt[0]}&upperRightYToUse={self.max_pt[1]}"\
                   f"&wcsURLToUse=https://chc-ewx2.chc.ucsb.edu:8443/geoserver/wcs?&resolution=0.05&srsToUse=EPSG:3857&outputSrsToUse=EPSG:4326"

    def set_url_chirps_gefs(self):
        self.url = f"https://chc-ewx2.chc.ucsb.edu/proxies/wcsProxy.php?layerNameToUse=chirpsgefs15day2:"\
                    f"chirpsgefs15day2_africa_1"\
                    f"-day-{self.day_of_year}-{self.year}_{self.stat}"\
                    f"&lowerLeftXToUse={self.min_pt[0]}&lowerLeftYToUse={self.min_pt[1]}"\
                    f"&upperRightXToUse={self.max_pt[0]}&upperRightYToUse={self.max_pt[1]}"\
                    f"&wcsURLToUse=https://chc-ewx2.chc.ucsb.edu:8443/geoserver/wcs?&resolution=0.05&srsToUse=EPSG:3857&outputSrsToUse=EPSG:4326"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CHIRPS runner')
    parser.add_argument('--name',  type=str, help='CHIRPS, CHIRPS-GEFS, or CHIRTSmax')
    parser.add_argument('--month', type=int, help='Month')
    parser.add_argument('--year',  type=int, help='Year')
    parser.add_argument('--bbox',  type=str, help="The bounding box of corners to obtain e.g. '[[33.512234, 2.719907], [49.98171,16.501768]]'")
    
    args = parser.parse_args()    
    runner = CHIRPSController(args.name, args.month, args.year, args.bbox)
    runner.run_models()
