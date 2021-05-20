#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
from datetime import datetime
import glob
import json
from requests import get
import os
import time
import random


#### Causemosify the DM csv files ####
def causemosify(df_in):

    df = df_in.copy(deep=True)

    # "time" (%Y-%m-%dT%H:%M:%SZ) to "timestamp" (epoch time)
    df["timestamp"] = df.time.apply(
        lambda x: round(pd.to_datetime(x, format="%Y-%m-%dT%H:%M:%SZ").timestamp())
    )

    # add lat/lng with NaN
    df["lat"] = np.nan
    df["lng"] = np.nan

    # Rename feature column
    df.rename(columns={"variable_id": "feature"}, inplace=True)

    # Newd df with proper CM order
    CM_headers = [
        "timestamp",
        "country",
        "admin1",
        "admin2",
        "admin3",
        "lat",
        "lng",
        "feature",
        "value",
    ]

    return df[CM_headers].copy()


for file in sorted(glob.glob("datamart-dump/*.csv")):
    try:
        #Datamart df to cm
        df_DM = pd.read_csv(file)

        # Convert to Friend of Causemos
        df_DM = pd.read_csv(file)
        df = causemosify(df_DM)

        # Convert to gzip parquet file
        print("Causemosifing and gzipping into parquet")
        print(file)
        fn_gz = file.split("/")[1].split(".")[0]
        gz_path = f'causemosified/{fn_gz}.parquet.gzip'
        df.to_parquet(gz_path, compression="gzip")

    except Exception as e:
        print(e)
