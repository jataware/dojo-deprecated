from os import mkdir
import json
import os
import logging
import requests
import shutil

import pandas as pd
from geotime_classify import geotime_classify as gc
import numpy as np

from utils import get_rawfile
from settings import settings

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def describe_data(context, filename=None):
    # If no filename is passed in, default to the converted raw_data file.
    if filename is None:
        filename = "raw_data.csv"

    # Load the data.
    rawfile_path = os.path.join(
        settings.DATASET_STORAGE_BASE_URL, context["uuid"], filename
    )
    file = get_rawfile(rawfile_path)
    df = pd.read_csv(file, delimiter=",")

    # Get the data description.
    description = df.describe()

    # Use Histogram functions
    histogram_data = generate_histogram_data(df)

    # Return the description.
    return description, json.loads(histogram_data)


def generate_histogram_data(dataframe):

    return dataframe.apply(histogram_data).to_json()


def histogram_data(x):
    logging.warn(f"Inside histogram_data: {x}, dtype: {x.dtype}")
    if x.dtype != np.dtype(np.object) and x.dtype != np.dtype(np.bool):
        hist, bins = np.histogram(x)
        logging.warn(f"Histogram: {hist}, bins: {bins}")
        bbins = np.char.mod("%.2f", bins)
        label = map("-".join, zip(bbins[:-1], bbins[1:]))
        return dict(zip(label, hist))
