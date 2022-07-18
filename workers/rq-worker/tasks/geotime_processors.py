from os import mkdir
import json
import os
import logging
import requests

import pandas as pd
from geotime_classify import geotime_classify as gc

from base_annotation import BaseProcessor
from utils import get_rawfile, put_rawfile

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


class GeotimeProcessor(BaseProcessor):
    @staticmethod
    def run(context, df):
        """apply gc to df and write"""
        logging.info(
            f"{context.get('logging_preface', '')} - Applying geotime classification"
        )

        def convert_gc(classifications):
            ret = {}
            for classification in classifications.classifications:
                col_name = classification.column
                logging.warn(f"Inside converter: {classification}")
                ret[col_name] = classification.dict()
                del ret[col_name]["column"]
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


def geotime_classify(context):

    file = get_rawfile(context["uuid"], "raw_data.csv")
    df = pd.read_csv(file, delimiter=",")
    gc = GeotimeProcessor()

    final = gc.run(df=df, context=context)

    # Constructs data object for patch that updates the metadata dictionary for the MetadataModel
    json_final = json.loads(json.dumps(final))
    data = {"metadata": {"geotime_classify": json_final}}
    api_url = os.environ.get("DOJO_HOST")
    request_response = requests.patch(
        f"{api_url}/indicators/{context['uuid']}/annotations",
        json=data,
    )
    return json_final, request_response
