import logging
import json
import os
import re
import requests
import shutil

import pandas as pd

from utils import get_rawfile, put_rawfile
from mixmasta import mixmasta as mix
from base_annotation import BaseProcessor
from settings import settings


def build_mixmasta_meta_from_context(context, filename=None):
    import pprint
    metadata = context["annotations"]["metadata"]
    mapping  = {
        'band': 'geotiff_band_count',
        'band_name': 'geotiff_value',
        'bands': 'geotiff_bands',
        'band_type': 'geotiff_band_type',
        'date': 'geotiff_date',
        'feature_name': 'geotiff_band',
        'null_val': 'geotiff_null_value',
        'sheet': 'excel_sheet_name',
    }
    mixmasta_meta = {}
    mixmasta_meta["ftype"] = metadata.get("ftype", "csv")

    for key, value in mapping.items():
        if value in metadata:
            mixmasta_meta[key] = metadata[value]
    return mixmasta_meta


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
    
    logging.warn(f"FILENAME: {filename}")

    # Copy raw data file into rq-worker
    # Could change mixmasta to accept file-like objects as well as filepaths.  
    if filename is None:
        filename = "raw_data.csv"
        rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, uuid, filename)

        file_suffix = ''
    else:
        rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, filename)

        file_suffix_match = re.search(r'raw_data(_\d+)?\.', filename)
        logging.warn(file_suffix_match)
        if file_suffix_match:
            file_suffix = file_suffix_match.group(1) or ''
        else:
            file_suffix = ''

    raw_file_obj = get_rawfile(rawfile_path)
    with open(f"{datapath}/raw_data.csv", "wb") as f:
        f.write(raw_file_obj.read())

    # Writing out the annotations because mixmasta needs a filepath to this data.
    # Should probably change mixmasta down the road to accept filepath AND annotations objects.
    mm_ready_annotations = context["annotations"]["annotations"]
    mm_ready_annotations['meta'] = build_mixmasta_meta_from_context(context)
    with open(f"{datapath}/mixmasta_ready_annotations.json", "w") as f:
        f.write(json.dumps(mm_ready_annotations))
    f.close()

    # Main Call
    mixmasta_result_df = processor.run(context, datapath)

    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    for file in os.listdir(datapath):
        if file.endswith(".parquet.gzip"):
            logging.warn(file)
            logging.warn(file_suffix)
            output_file_name = f'{file.split(".")[0]}{file_suffix}.parquet.gzip'
            logging.warn(output_file_name)
            with open(os.path.join(datapath, file), "rb") as fileobj:
                dest_path = os.path.join(os.path.dirname(rawfile_path), output_file_name)
                put_rawfile(path=dest_path, fileobj=fileobj)

    # Run the indicator update via post to endpoint
    api_url = os.environ.get("DOJO_HOST")
    request_response = requests.post(f"{api_url}/indicators/mixmasta_update/{uuid}")

    # Final cleanup of temp directory
    shutil.rmtree(datapath)

    return generate_post_mix_preview(mixmasta_result_df), request_response


def generate_post_mix_preview(mixmasta_result):

    return mixmasta_result.head(100).to_json()


def run_dataset_mixmasta(context, filename=None):
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
        rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, uuid, filename)
    else:
        rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, filename)
    raw_file_obj = get_rawfile(rawfile_path)
    with open(f"{datapath}/raw_data.csv", "wb") as f:
        f.write(raw_file_obj.read())

    # Writing out the annotations because mixmasta needs a filepath to this data.
    # Should probably change mixmasta down the road to accept filepath AND annotations objects.
    mm_ready_annotations = context["annotations"]["annotations"]
    mm_ready_annotations['meta'] = build_mixmasta_meta_from_context(context)
    with open(f"{datapath}/mixmasta_ready_annotations.json", "w") as f:
        f.write(json.dumps(mm_ready_annotations))
    f.close()

    # Main Call
    mixmasta_result_df = processor.run(context, datapath)

    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    for file in os.listdir(datapath):
        if file.endswith(".parquet.gzip"):
            with open(os.path.join(datapath, file), "rb") as fileobj:
                dest_path = os.path.join(os.path.dirname(rawfile_path), file)
                put_rawfile(path=dest_path, fileobj=fileobj)

    # Run the indicator update via post to endpoint
    api_url = os.environ.get("DOJO_HOST")
    request_response = requests.post(f"{api_url}/indicators/mixmasta_update/{uuid}")

    # Final cleanup of temp directory
    shutil.rmtree(datapath)

    return generate_post_mix_preview(mixmasta_result_df), request_response


def run_model_mixmasta(context, *args, **kwargs):
    metadata = context['annotations']['metadata']
    processor = MixmastaProcessor()
    datapath = os.path.join(settings.DATASET_STORAGE_BASE_URL, 'model-output-samples', context['uuid'])
    sample_path = os.path.join(datapath, f"{metadata['file_uuid']}.csv")
    # Creating folder for temp file storage on the rq worker since following functions are dependent on file paths
    localpath = f"/datasets/processing/{context['uuid']}"
    if not os.path.isdir(localpath):
        os.makedirs(localpath)

    # filename = context.get('')
    # Copy raw data file into rq-worker
    # Could change mixmasta to accept file-like objects as well as filepaths.
    # rawfile_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, filename)
    raw_file_obj = get_rawfile(sample_path)
    with open(f"{localpath}/raw_data.csv", "wb") as f:
        f.write(raw_file_obj.read())

    # Writing out the annotations because mixmasta needs a filepath to this data.
    # Should probably change mixmasta down the road to accept filepath AND annotations objects.
    mm_ready_annotations = context["annotations"]["annotations"]
    mm_ready_annotations['meta'] = build_mixmasta_meta_from_context(context)

    # annotation_file = get_rawfile(os.path.join(datapath), )
    with open(f"{localpath}/mixmasta_ready_annotations.json", "w") as f:
        f.write(json.dumps(mm_ready_annotations))
    f.close()

    # Main Call
    mixmasta_result_df = processor.run(context, localpath)

    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    for file in os.listdir(localpath):
        if file.endswith(".parquet.gzip"):
            with open(os.path.join(localpath, file), "rb") as fileobj:
                dest_path, parquet_filename = os.path.split(sample_path)
                dest = os.path.join(dest_path, f"{metadata['file_uuid']}.parquet.gzip")
                put_rawfile(path=dest, fileobj=fileobj)

    # Final cleanup of temp directory
    shutil.rmtree(localpath)

    return generate_post_mix_preview(mixmasta_result_df)
