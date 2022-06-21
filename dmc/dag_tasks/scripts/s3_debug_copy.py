import argparse
from contextlib import contextmanager
from pathlib import Path

import boto3


@contextmanager
def s3_session():
    session = boto3.Session()
    try:
        yield session.client("s3")
    except Exception:
        raise


def s3_debug_copy(model_id, run_id, s3_bucket, s3_bucket_dir, upload=False):

    print(f"s3 {upload=}")
    with s3_session() as s3:
        for p in Path("/results").rglob("*"):
            if not p.is_file():
                continue

            print(f"{p=}")
            key_part = str(p).replace("/results/", "", 1)
            print(f"{key_part=}")

            # NOTE: objects stored to dmc_results are automatically made public
            # per the S3 bucket's policy
            # TODO: may need to address this with more fine grained controls in the future

            key = f"{s3_bucket_dir}/debug/{run_id}/{key_part}"
            print(f"Upload {key=}")
            if upload:
                s3.upload_file(
                    str(p.absolute()),
                    s3_bucket,
                    key,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="s3_copy")
    parser.add_argument("model_id", help="model_id")
    parser.add_argument("run_id", help="run_id")
    parser.add_argument("s3_bucket", help="s3 bucket")
    parser.add_argument("s3_bucket_dir", help="s3 bucket dir")
    parser.add_argument("--upload", action=argparse.BooleanOptionalAction)

    args = parser.parse_args()
    s3_debug_copy(args.model_id, args.run_id, args.s3_bucket, args.s3_bucket_dir, args.upload)
