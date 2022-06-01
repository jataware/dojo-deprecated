from os import mkdir
from .base_annotation import BaseProcessor
import json
import os
from geotime_classify import geotime_classify as gc
import logging


class GeotimeProcessor(BaseProcessor):
    @staticmethod
    def run(df, context):
        """apply gc to df and write"""
        logging.info(
            f"{context.get('logging_preface', '')} - Applying geotime classification"
        )

        def convert_gc(c):
            ret = {}
            for x in c:
                ret[x["column"]] = x
                del ret[x["column"]]["column"]
            return ret

        GeoTimeClass = gc.GeoTimeClassify(50)
        os.makedirs(f"./data/{context['uuid']}")
        df.head(50).to_csv(f"data/{context['uuid']}/raw_data_geotime.csv", index=False)
        c_classified = GeoTimeClass.columns_classified(
            f"data/{context['uuid']}/raw_data_geotime.csv"
        )
        c_classified = convert_gc(c_classified.dict()["classifications"])
        json.dump(
            c_classified,
            open(f"data/{context['uuid']}/geotime_classification.json", "w"),
        )
        return df
