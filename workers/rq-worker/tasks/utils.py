import time
import os
from io import BytesIO
import tempfile
from urllib.parse import urlparse
import logging

import boto3
from settings import settings

# S3 OBJECT
s3 = boto3.client("s3")
DATASET_STORAGE_BASE_URL = os.environ.get("DATASET_STORAGE_BASE_URL")


def get_rawfile(uuid, filename):
    location_info = urlparse(settings.DATASET_STORAGE_BASE_URL)
    file_dir = os.path.join(location_info.path, uuid)
    file_path = os.path.join(file_dir, filename)

    if location_info.scheme.lower() == "file":
        raw_file = open(file_path, "rb")
    elif location_info.scheme.lower() == "s3":
        file_path = file_path.lstrip("/")
        raw_file = tempfile.TemporaryFile()
        s3.download_fileobj(
            Bucket=location_info.netloc, Key=file_path, Fileobj=raw_file
        )
        raw_file.seek(0)
    else:
        raise RuntimeError("File storage format is unknown")

    return raw_file


def put_rawfile(uuid, filename, fileobj):
    if filename is None:
        filename = settings.CSV_FILE_NAME
    location_info = urlparse(settings.DATASET_STORAGE_BASE_URL)
    output_dir = os.path.join(location_info.path, uuid)
    output_path = os.path.join(output_dir, filename)

    if location_info.scheme.lower() == "file":
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "wb") as output_file:
            output_file.write(fileobj.read())
    elif location_info.scheme.lower() == "s3":
        output_path = output_path.lstrip("/")
        s3.put_object(Bucket=location_info.netloc, Key=output_path, Body=fileobj)
    else:
        raise RuntimeError("File storage format is unknown")
