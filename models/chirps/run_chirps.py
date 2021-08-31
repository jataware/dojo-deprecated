'''
Usage:

python3 run_chirps.py --admin_level=1 --country='United Republic of Tanzania' --admin1='Tanga' --statistic='data'

requires:
    requests==2.25.1
    pandas==1.2.4
'''

import os
import pandas as pd
import requests
import argparse
import logging
import json
import urllib.parse

logging.basicConfig(level=logging.INFO)

locales = json.load(open("locales.json", "r"))

def get_chirps(url, locale):
    country, admin1, admin2 = locale.split('+')
    out = requests.get(url)
    try:
        logging.info(out.json())
        data = out.json()['chirps']['time_series']['values']
        tx = []
        for kk, vv in data.items():
            for v_ in vv:
                v_['year'] = kk
                v_['month'] = v_.pop('x')
                v_['rainfall'] = v_.pop('y')
                tx.append(v_)
        df = pd.DataFrame(tx)
        df['country'] = country
        df['admin1'] = admin1
        df['admin2'] = admin2
        return df
    except Exception as e:
        obj = {'year': None, 'month': None, 'rainfall': None, 'country': None, 'admin1': None, 'admin2': None}
        df = pd.DataFrame([obj])
        logging.error(f'Error encountered while fetching CHIRPS data: {e}')
        return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CHIRPS runner')
    parser.add_argument('--country', type=str, help='the country of interest')
    parser.add_argument('--statistic', type=str, help='either data, anomaly, or z_score')
    args = parser.parse_args()

    if not os.path.exists('results'):
        os.makedirs('results')

    df = []
    for locale in locales[args.country][:4]:
        # locale_ = urllib.parse.quote_plus(locale)   
        locale_ = locale.replace(' ','%20')
        logging.info(f"Processing {locale}")
        url = f"http://chg-ewxtest.chc.ucsb.edu:8910/rest/timeseries/version/2.0/vector_dataset/africa:g2008_2/raster_dataset/chirps/region/africa/periodicity/1-month/statistic/{args.statistic}/zone/{locale_}/seasons/2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,stm/calculation_type/mean"
        df_ = get_chirps(url, locale)
        logging.info(df_.head())
        if len(df) == 0:
            df = df_
        else:
            df = df.append(df_)
    logging.info(df.head())
    df.to_csv('results/chirps.csv', index=False)