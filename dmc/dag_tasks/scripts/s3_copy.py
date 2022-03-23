import argparse
import glob
from contextlib import contextmanager

import boto3


@contextmanager
def s3_session():
    session = boto3.Session()
    try:
        yield session.client("s3")
    except Exception:
        raise


def s3_copy(model_id, run_id, s3_bucket, s3_bucket_dir):

    with s3_session() as s3:
        for fpath in glob.glob("/results/*.parquet.gzip"):
            print(f"fpath:{fpath}")
            fn = fpath.split("/")[-1]
            print(f"fn:{fn}")

            # NOTE: objects stored to dmc_results are automatically made public
            # per the S3 bucket's policy
            # TODO: may need to address this with more fine grained controls in the future

            key = f"{s3_bucket_dir}/{run_id}/{fn}"
            s3.upload_file(
                fpath,
                s3_bucket,
                key,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="s3_copy")
    parser.add_argument("model_id", help="model_id")
    parser.add_argument("run_id", help="run_id")
    parser.add_argument("s3_bucket", help="s3 bucket")
    parser.add_argument("s3_bucket_dir", help="s3 bucket dir")

    args = parser.parse_args()
    s3_copy(args.model_id, args.run_id, args.s3_bucket, args.s3_bucket_dir)
