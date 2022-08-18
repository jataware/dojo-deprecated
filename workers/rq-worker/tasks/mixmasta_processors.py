import logging
import json
import os
import re
import requests
import shutil
from urllib.parse import urlparse

import pandas as pd

from utils import get_rawfile, put_rawfile, list_files
from mixmasta import mixmasta as mix
from tasks import (
    generate_mixmasta_files,
)
from base_annotation import BaseProcessor
from settings import settings


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

    if not filename.endswith(".csv"):
        filename = filename.split(".")[0] + ".csv"

    rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, uuid, filename)
    raw_file_obj = get_rawfile(rawfile_path)
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

    file_suffix_match = re.search(r'raw_data(_\d+)?\.', filename)
    if file_suffix_match:
        file_suffix = file_suffix_match.group(1) or ''
    else:
        file_suffix = ''

    data_files = []
    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    dest_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, uuid)
    for local_file in os.listdir(datapath):
        if local_file.endswith(".parquet.gzip"):
            local_file_match = re.search(rf'({uuid}(_str)?).parquet.gzip', local_file)
            if local_file_match:
                file_root = local_file_match.group(1)
            dest_file_path = os.path.join(dest_path, f"{file_root}{file_suffix}.parquet.gzip")
            with open(os.path.join(datapath, local_file), "rb") as fileobj:
                put_rawfile(path=dest_file_path, fileobj=fileobj)
            if dest_file_path.startswith("s3:"):
                # "https://jataware-world-modelers.s3.amazonaws.com/dev/indicators/6c9c996b-a175-4fa6-803c-e39b24e38b6e/6c9c996b-a175-4fa6-803c-e39b24e38b6e.parquet.gzip"
                location_info = urlparse(dest_file_path)
                data_files.append(f"https://{location_info.netloc}/{location_info.path}")
            else:
                data_files.append(dest_file_path)

    # Final cleanup of temp directory
    shutil.rmtree(datapath)

    dataset = context.get("datasets")
    if dataset.get("period", None):
        period = {
            "gte": max(int(mixmasta_result_df['timestamp'].max()), dataset.get("period", {}).get("gte", None)),
            "lte": min(int(mixmasta_result_df['timestamp'].min()), dataset.get("period", {}).get("lte", None)),
        }
    else:
        period = {
            "gte": int(mixmasta_result_df['timestamp'].max()),
            "lte": int(mixmasta_result_df['timestamp'].min()),
        }

    if dataset.get("geography", None):
        geography_dict = dataset.get("geography", {})
    else:
        geography_dict = {}
    for geog_type in ["admin1", "admin2", "admin3", "country"]:
        if geog_type not in geography_dict:
            geography_dict[geog_type] = []
        for value in mixmasta_result_df[mixmasta_result_df[geog_type].notna()][geog_type].unique():
            if value == "nan" or value in geography_dict[geog_type]:
                continue
            geography_dict[geog_type].append(value)

    response = {
        "preview": mixmasta_result_df.head(100).to_json(),
        "data_files": data_files,
        "period": period,
        "geography": geography_dict,
    }
    return response
