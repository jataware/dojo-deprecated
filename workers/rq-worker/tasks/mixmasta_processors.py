import pandas as pd
from mixmasta import mixmasta as mix
from tasks import (
    generate_mixmasta_files,
    post_mixmasta_annotation_processing,
)
import logging
import os
from .base_annotation import BaseProcessor


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
    def run(df, context) -> pd.DataFrame:
        """final full mixmasta implementation"""
        logging.info(
            f"{context.get('logging_preface', '')} - Running mixmasta processor"
        )
        gadm_level = None  # can maybe be left off
        output_path = (
            f"{context['output_directory']}/{context['uuid']}"  # S3 bucket now.
        )
        mapper_fp = context[
            "mapper_fp"
        ]  # Filename for json info, will eventually be in Elasticsearch, needs to be written to disk until mixmasta is updated
        raw_data_fp = context["raw_data_fp"]  # Raw data
        admin_level = context["admin_level"]  # This comes from annotations file.
        uuid = context["uuid"]

        open(f"data/{uuid}/mixmasta_processed_writing", "w").close()

        ret, rename = mix.process(
            raw_data_fp, mapper_fp, admin_level, output_path, gadm=gadm_level
        )

        post_mixmasta_annotation_processing(rename, context)

        open(f"data/{uuid}/mixmasta_processed_writing", "w").close()
        ret.to_csv(f"data/{uuid}/mixmasta_processed_df.csv", index=False)
        os.remove(f"data/{uuid}/mixmasta_processed_writing")
        return df


def process(df, context):
    file_generator = MixmastaFileGenerator()
    processor = MixmastaProcessor()

    if not os.path.exists(f"./data/{context['uuid']}"):
        os.makedirs(f"./data/{context['uuid']}")

    mm_ready_annotations = file_generator.run(context)
