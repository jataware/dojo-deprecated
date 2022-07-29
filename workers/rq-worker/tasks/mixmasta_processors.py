import logging
import json
import os
import requests
import shutil

import pandas as pd

from utils import get_rawfile, put_rawfile
from mixmasta import mixmasta as mix
from tasks import (
    generate_mixmasta_files,
)
from base_annotation import BaseProcessor


class MixmastaFileGenerator(BaseProcessor):
    @staticmethod
    def run(context):
        """generate the files to run mixmasta"""
        logging.info(
            f"{context.get('logging_preface', '')} - Generating mixmasta files"
        )
        mm_ready_annotations = generate_mixmasta_files(context)
        return mm_ready_annotations


class MixmastaProcessor(BaseProcessor):
    @staticmethod
    def run(context, datapath) -> pd.DataFrame:
        """final full mixmasta implementation"""
        logging.info(
            f"{context.get('logging_preface', '')} - Running mixmasta processor"
        )
        output_path = datapath
        mapper_fp = f"{output_path}/mixmasta_ready_annotations.json"  # Filename for json info, will eventually be in Elasticsearch, needs to be written to disk until mixmasta is updated
        raw_data_fp = f"{output_path}/raw_data.csv"  # Raw data
        # Getting admin level to resolve to from annotations
        admin_level = "admin1"  # Default to admin1
        geo_annotations = context["annotations"]["annotations"]["geo"]
        for annotation in geo_annotations:
            if annotation["primary_geo"]:
                admin_level = annotation["gadm_level"]
                break
        uuid = context["uuid"]
        context["mapper_fp"] = mapper_fp

        # Mixmasta output path (it needs the filename attached to write parquets, and the file name is the uuid)
        mix_output_path = f"{output_path}/{uuid}"
        # Main mixmasta processing call
        ret, rename = mix.process(raw_data_fp, mapper_fp, admin_level, mix_output_path)

        ret.to_csv(f"{output_path}/mixmasta_processed_df.csv", index=False)

        return ret


def run_mixmasta(context, filename=None):
    processor = MixmastaProcessor()
    uuid = context["uuid"]
    # Creating folder for temp file storage on the rq worker since following functions are dependent on file paths
    datapath = f"./{uuid}"
    if not os.path.isdir(datapath):
        os.makedirs(datapath)

    # Copy raw data file into rq-worker
    # Could change mixmasta to accept file-like objects as well as filepaths.
    if filename is None:
        filename = "raw_data.csv"
    raw_file_obj = get_rawfile(context["uuid"], filename)
    with open(f"{datapath}/raw_data.csv", "wb") as f:
        f.write(raw_file_obj.read())

    # Writing out the annotations because mixmasta needs a filepath to this data.
    # Should probably change mixmasta down the road to accept filepath AND annotations objects.
    mm_ready_annotations = context["annotations"]["annotations"]
    with open(f"{datapath}/mixmasta_ready_annotations.json", "w") as f:
        f.write(json.dumps(mm_ready_annotations))
    f.close()

    # Main Call
    mixmasta_result_df = processor.run(context, datapath)

    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    for file in os.listdir(datapath):
        if file.endswith(".parquet.gzip"):
            with open(os.path.join(datapath, file), "rb") as fileobj:
                put_rawfile(uuid=uuid, filename=file, fileobj=fileobj)

    # Run the indicator update via post to endpoint
    api_url = os.environ.get("DOJO_HOST")
    request_response = requests.post(f"{api_url}/indicators/mixmasta_update/{uuid}")
    logging.info(f"Response: {request_response}")

    # Final cleanup of temp directory
    shutil.rmtree(datapath)

    return generate_post_mix_preview(mixmasta_result_df), request_response


def generate_post_mix_preview(mixmasta_result):

    return mixmasta_result.head(100).to_json()
