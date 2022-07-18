import logging
import json
import os
import requests

import pandas as pd

from utils import put_rawfile
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
        admin_level = "admin1"  # TODO: This should come from context but it's not being set currently.
        uuid = context["uuid"]
        context["mapper_fp"] = mapper_fp

        open(f"{output_path}/mixmasta_processed_writing", "w").close()

        # Mixmasta output path (it needs the filename attached to write parquets)
        mix_output_path = f"{output_path}/{uuid}"
        # Main mixmasta processing call
        ret, rename = mix.process(raw_data_fp, mapper_fp, admin_level, mix_output_path)

        open(f"{output_path}/mixmasta_processed_writing", "w").close()
        ret.to_csv(f"{output_path}/mixmasta_processed_df.csv", index=False)
        os.remove(f"{output_path}/mixmasta_processed_writing")

        return ret


def run_mixmasta(context):
    file_generator = MixmastaFileGenerator()
    processor = MixmastaProcessor()
    uuid = context["uuid"]
    # Creating folder for temp file storage on the rq worker
    datapath = f"/datasets/{uuid}"
    if not os.path.isdir(datapath):
        os.makedirs(datapath)

    # Writing out the annotations because mixmasta needs a filepath to this data.
    # Should probably change mixmasta down the road to accept filepath AND annotations objects.
    mm_ready_annotations = context["annotations"]["annotations"]
    with open(f"{datapath}/mixmasta_ready_annotations.json", "w") as f:
        f.write(json.dumps(mm_ready_annotations))
    f.close()

    mixmasta_result_df = processor.run(context, datapath)
    # Takes all parquet files and puts them into the DATASET_STORAGE_BASE_URL which will be S3 in Production
    for file in os.listdir(datapath):
        if file.endswith(".parquet.gzip"):
            with open(os.path.join(datapath, file), "rb") as fileobj:
                put_rawfile(uuid=uuid, filename=f"final_{file}", fileobj=fileobj)

    # Run the indicator update
    api_url = os.environ.get("DOJO_HOST")
    request_response = requests.post(f"{api_url}/indicators/mixmasta_update/{uuid}")
    logging.info(f"Response: {request_response}")

    return generate_post_mix_preview(mixmasta_result_df), request_response


def generate_post_mix_preview(mixmasta_result):

    return mixmasta_result.head(100).to_json()
