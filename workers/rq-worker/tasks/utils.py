import time
import os
from io import BytesIO
import tempfile
from urllib.parse import urlparse
import logging

import boto3

# S3 OBJECT
s3 = boto3.client("s3")
DATASET_STORAGE_BASE_URL = os.environ.get("DATASET_STORAGE_BASE_URL")


def get_rawfile(uuid, filename):
    location_info = urlparse(DATASET_STORAGE_BASE_URL)
    file_dir = os.path.join(location_info.path, uuid)
    file_path = os.path.join(file_dir, filename)

    if location_info.scheme.lower() == "file":
        raw_file =  open(file_path, "rb")
        logging.debug(
            f"INFO from get raw file: Path: {file_path}"
        )
    elif location_info.scheme.lower() == "s3":
        file_path = file_path.lstrip("/")
        raw_file = tempfile.TemporaryFile()
        s3.download_fileobj(
            Bucket=location_info.netloc,
            Key=file_path,
            Fileobj=raw_file
        )
        raw_file.seek(0)
        logging.debug(
            f"INFO from get raw file: Bucket: {location_info.netloc} | File: {file_path}"
        )
    else:
        raise RuntimeError("File storage format is unknown")

    return raw_file


def put_rawfile(uuid, filename, fileobj):
    location_info = urlparse(DATASET_STORAGE_BASE_URL)
    output_dir = os.path.join(location_info.path, uuid)
    output_path = os.path.join(output_dir, filename)

    if location_info.scheme.lower() == "file":
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "wb") as output_file:
            output_file.write(fileobj.read())
        logging.debug(
            f"INFO from put raw file: Path: {file_path}"
        )
    elif location_info.scheme.lower() == "s3":
        output_path = output_path.lstrip("/")
        s3.put_object(
            Bucket=location_info.netloc,
            Key=output_path,
            Body=fileobj
        )
        logging.debug(
            f"INFO from put raw file: Bucket: {location_info.netloc} | File: {output_path}"
        )
    else:
        raise RuntimeError("File storage format is unknown")

