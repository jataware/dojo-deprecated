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

def get_chirps(url, country, admin1):
    out = requests.get(url)
    try:
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
        df.to_csv('results/chirps.csv', index=False)
    except Exception as e:
        raise SystemExit(f'Error encountered while fetching CHIRPS data: {e}')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CHIRPS runner')
    parser.add_argument('--admin_level', type=int, help='either 1 or 2')
    parser.add_argument('--country', type=str, help='the country of interest')
    parser.add_argument('--admin1', type=str, help='the admin 1 area of interest')
    parser.add_argument('--admin2', type=str, help='the admin 2 area of interest')
    parser.add_argument('--statistic', type=str, help='either data, anomaly, or z_score')
    args = parser.parse_args()

    if not os.path.exists('results'):
        os.makedirs('results')

    if args.admin_level == 1:
        url = f"http://chg-ewxtest.chc.ucsb.edu:8910/rest/timeseries/version/2.0/vector_dataset/africa:g2008_{args.admin_level}/raster_dataset/chirps/region/africa/periodicity/1-month/statistic/{args.statistic}/zone/{args.country}+{args.admin1}/seasons/2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020/calculation_type/mean"
    else:
        url = f"http://chg-ewxtest.chc.ucsb.edu:8910/rest/timeseries/version/2.0/vector_dataset/africa:g2008_{args.admin_level}/raster_dataset/chirps/region/africa/periodicity/1-month/statistic/{args.statistic}/zone/{args.country}+{args.admin1}+{args.admin2}/seasons/2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020/calculation_type/mean"
    
    get_chirps(url, args.country, args.admin1)