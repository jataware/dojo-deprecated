import argparse
import glob
import json
import logging
import os
from contextlib import contextmanager
from logging import Logger

import boto3
import requests

logger: Logger = logging.getLogger(__name__)


@contextmanager
def s3_session():
    session = boto3.Session()
    yield session.client("s3")


def accessory(model_id, run_id, dojo_url, s3_bucket, s3_bucket_dir):
    """
    If anything is in /results/{run.id}/accessories, push it to S3.
    """
    accessories_path = f"/results/{run_id}/accessories"
    logger.info(f"accessories_path: {accessories_path}")

    # get the model accessories
    req = requests.get(f"{dojo_url}/dojo/accessories/{model_id}")
    accessories = json.loads(req.content)

    with s3_session() as s3:

        for accessory in accessories:
            fp_ = accessory.get("path", "").split("/")[-1]
            logger.info(f"fpath raw:{accessories_path}/{fp_}")
            matches = glob.glob(f"{accessories_path}/{fp_}")

            # if no accessory files are found, just return nothing
            # I don't believe this should cause the task to fail, since the model outputs may
            # have successfuly been transformed and might still have utility, even if the accessories
            # were dropped
            if len(matches) == 0:
                logger.error(f"No accessory files were found matching: {accessories_path}/{fp_}")
                continue

            fpath = matches[0]
            logger.info(f"fpath ready:{fpath}")

            fn = fpath.split("/")[-1]
            logger.info(f"fn:{fn}")

            # move accessory and inject id into filepath
            fpath_new = f"{accessories_path}/{accessory['id']}__dojo__{fn}"
            os.rename(fpath, fpath_new)

            # NOTE: objects stored to dmc_results are automatically made public
            # per the S3 bucket's policy
            # TODO: may need to address this with more fine grained controls in the future
            key = f"{s3_bucket_dir}/{run_id}/{fn}"

            logger.info("key:" + key)

            s3.upload_file(
                filename=fpath_new,
                bucket_name=s3_bucket,
                key=key,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="accessory")
    parser.add_argument("model_id", help="model_id")
    parser.add_argument("run_id", help="run_id")
    parser.add_argument("dojo_url", help="dojo_url")
    parser.add_argument("s3_bucket", help="s3 bucket")
    parser.add_argument("s3_bucket_dir", help="s3 bucket dir")

    args = parser.parse_args()
    accessory(args.model_id, args.run_id, args.dojo_url, args.s3_bucket, args.s3_bucket_dir)
