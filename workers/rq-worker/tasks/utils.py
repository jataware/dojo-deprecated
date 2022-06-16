import time
import os
from io import BytesIO
import logging

import boto3

# S3 OBJECT
# TODO PICK EITHER CLIENT OR RESOURCE
s3 = boto3.resource("s3")
s3_low = boto3.client("s3")


def get_rawfile(uuid, filename):
    # Get raw file from S3
    bucket = s3.Bucket(os.getenv("DMC_BUCKET"))
    file_location = bucket.Object(f"dev/indicators/{uuid}/{filename}")

    file_stream = BytesIO()
    file_location.download_fileobj(file_stream)

    file_stream.seek(0)

    return file_stream


def put_rawfile(uuid, filename, fileobj):
    bucket = os.getenv("DMC_BUCKET")
    file_location = f"dev/indicators/{uuid}/{filename}"
    s3_low.upload_fileobj(fileobj, bucket, file_location)
