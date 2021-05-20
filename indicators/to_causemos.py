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
