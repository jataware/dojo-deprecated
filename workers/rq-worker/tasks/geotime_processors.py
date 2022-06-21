from os import mkdir
import json
import os
import logging

import pandas as pd
from geotime_classify import geotime_classify as gc

from base_annotation import BaseProcessor
from utils import get_rawfile


class GeotimeProcessor(BaseProcessor):
    @staticmethod
    def run(context, df):
        """apply gc to df and write"""
        logging.info(
            f"{context.get('logging_preface', '')} - Applying geotime classification"
        )

        def convert_gc(c):
            ret = {}
            for x in c:
                logging.warn(f"Inside converter: {x}")
                ret[x["column"]] = x
                del ret[x["column"]]["column"]
            return ret

        GeoTimeClass = gc.GeoTimeClassify(50)
        if not os.path.exists(f"./data/{context['uuid']}"):
            os.makedirs(f"./data/{context['uuid']}")

        df.head(50).to_csv(f"data/{context['uuid']}/raw_data_geotime.csv", index=False)
        c_classified = GeoTimeClass.columns_classified(
            f"data/{context['uuid']}/raw_data_geotime.csv"
        )
        try:
            c_classifiedConverted = convert_gc(c_classified)
        except Exception as e:
            logging.error(f"Error: {e}, Classified object: {c_classified}")
        json.dump(
            c_classifiedConverted,
            open(f"data/{context['uuid']}/geotime_classification.json", "w"),
        )
        return c_classifiedConverted


def process(context):

    file = get_rawfile(context["uuid"], "raw_data.csv")
    df = pd.read_csv(file, delimiter=",")
    gc = GeotimeProcessor()

    final = gc.run(df=df, context=context)
    return final