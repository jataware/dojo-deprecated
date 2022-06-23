from __future__ import annotations
import logging
import time
import tempfile
from multiprocessing import context
import os
from io import BytesIO
from typing import List


import pandas as pd
from sqlite3 import connect
from fastapi import APIRouter, Response, File, UploadFile, status
from elasticsearch import Elasticsearch
from rq import Worker, Queue
from rq.job import Job
from redis import Redis
from rq.exceptions import NoSuchJobError
from rq import job
import boto3

from src.utils import get_rawfile, put_rawfile
from src.indicators import get_indicators, get_annotations

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

# FAST API ROUTER
router = APIRouter()

# REDIS CONNECTION AND QUEUE OBJECTS
redis = Redis(
    os.environ.get("REDIS_HOST", "redis.world-modelers"),
    os.environ.get("REDIS_PORT", "6379"),
)
q = Queue(connection=redis)

# S3 OBJECT
s3 = boto3.resource("s3")


# Main MixMasta API Endpoint
@router.post("/data/mixmasta_process/{uuid}")
def run_mixmasta(uuid: str):
    context = get_context(uuid=uuid)
    job = q.enqueue("mimasta_processors.process", context)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"msg": "Mixmasta job running"},
        content=f"Job ID: {job.id}",
    )


# Geotime classify endpoint
@router.post("/data/geotimeclass/{uuid}")
async def geotime_classify(uuid: str, payload: UploadFile = File(...)):
    try:
        context = get_context(uuid)

        payload_wrapper = tempfile.TemporaryFile()
        payload_wrapper.write(await payload.read())
        payload_wrapper.seek(0)

        df = pd.read_csv(payload_wrapper, delimiter=",")

        job = q.enqueue("geotime_processors.process", context, df)

        return Response(
            status_code=status.HTTP_200_OK,
            headers={"msg": "Submitted to geotime classify"},
            content=f"Job ID: {job.id}",
        )

    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"Queue could not be deleted.",
        )


@router.post("/data/preview/{lines}")
async def create_preview(number_of_lines: int, data: UploadFile = File(...)):

    try:
        payload_wrapper = tempfile.TemporaryFile()
        payload_wrapper.write(await data.read())
        payload_wrapper.seek(0)

        df = pd.read_csv(payload_wrapper, delimiter=",")

        preview = df.head(number_of_lines).to_json(orient="records")

        return preview

    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"Queue could not be deleted.",
        )


def convert_data_to_tabular(uuid, payload):
    if payload.filename.endswith(".csv"):

        # STUB FOR PUSH TO S3
        s3.upload_fileobj(
            payload, f"{bucket_name}/dev/indicators/{uuid}", "raw_data.csv"
        )
        return payload

    elif payload.filename.endswith(".xlsx"):
        read_file = pd.read_excel(payload)

        read_file.to_csv("xlsx_to.csv", index=None, header=True)

        # STUB FOR PUSH TO S3
        bucket_name = os.getenv("DMC_BUCKET")
        s3.upload_fileobj(
            read_file, f"{bucket_name}/dev/indicators/{uuid}", "raw_data.csv"
        )
        return read_file

    elif payload.filename.endswith(".tif"):
        # STUB FOR CONVERT TIF TO CSV

        # STUB FOR PUSH TO S3
        return payload

    elif payload.filename.endswith(".netcdf"):
        # STUB FOR CONVERT NETCDF TO CSV

        # STUB FOR PUSH TO S3
        return payload


def get_context(uuid):
    try:
        annotations = get_annotations(uuid)
    except:
        annotations = {}
    try:
        meta = get_indicators(uuid)
    except:
        meta = {}

    context = {"uuid": uuid, "metadata": meta, "annotations": annotations}

    return context


def get_datapath_from_indicator(uuid):
    indicator = get_indicators(uuid)

    datapath = indicator["_source"]["datapath"]

    return datapath


# RQ ENDPOINTS

@router.post("/job/enqueue/{job_string}")
def enqueue_job(job_string: str, uuid: str, job_id: str = None):
    context = get_context(uuid=uuid)
    if job_id is None:
        job = q.enqueue_call(func=job_string, args=[context])
    else:
        job = q.enqueue_call(func=job_string, args=[context], job_id=job_id)

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"msg": "Job enqueued"},
        content=f"Job ID: {job.id}",
    )


@router.post("/job/synchronous_enqueue/{job_string}")
def enqueue_job_sync(job_string: str, uuid: str, job_id: str = None):
    context = get_context(uuid=uuid)
    if job_id is None:
        job = q.enqueue_call(func=job_string, args=[context])
    else:
        job = q.enqueue_call(func=job_string, args=[context], job_id=job_id)

    while job.get_status(refresh=True) != "finished":
        print(job.get_status(refresh=True))
        time.sleep(0.5)

        if job.get_status(refresh=True) == "failed":
            return Response(
                status_code=status.HTTP_200_OK,
                headers={"msg": "Job failed"},
                content=f"Job Failed! Job ID: {job.id}",
            )

    results = job.result

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"msg": "Job finished"},
        content=f"Result: {results}",
    )


@router.post("/job/fetch/{job_id}")
def get_rq_job_results(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis)
        result = job.result
        return Response(
            status_code=status.HTTP_200_OK,
            content=f"Result: {result}",
        )
    except NoSuchJobError:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Job with id = {job_id} not found",
        )


@router.get("/job/queue/length")
def queue_length():
    return len(q)


@router.post("/job/queue/empty")
def empty_queue():
    try:
        deleted = q.empty()
        return Response(
            status_code=status.HTTP_200_OK,
            headers={"msg": f"deleted: {deleted}"},
            content=f"Queue deleted, {deleted} items removed",
        )
    except:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"Queue could not be deleted.",
        )


def cancel_job(job_id):
    job = Job.fetch(job_id, connection=redis)
    job.cancel()

    return job.get_status()

# Last to not interfere with other routes
@router.post("/job/{uuid}/{job_string}")
def job(uuid: str, job_string: str):

    job_id = f'{uuid}_{job_string}'

    job = q.fetch_job(job_id)
    if not job:
        try:
            context = get_context(uuid=uuid)
        except Exception as e:
            logging.error(e)
        job = q.enqueue_call(func=job_string, args=[context], job_id=job_id)
    
    status = job.get_status()
    if status in ("finished", "failed"):
        job_error = job.exc_info
        job.cleanup(ttl=0)  # Cleanup/remove data immediately
    else:
        job_error = None

    response = {
        "id": job_id,
        "created_at": job.created_at,
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "status": status,
        "job_error": job_error,
    }
    return response


# TEST ENDPOINTS


def test_job():
    # Test RQ job
    time.sleep(5)

    print("Job Job")


@router.post("/data/test/{num_of_jobs}")
def run_test_jobs(num_of_jobs):
    for n in range(int(num_of_jobs)):
        q.enqueue("tasks.test_job")


@router.get("/data/test/s3_grab/{uuid}")
def test_s3_grab(uuid):
    file = get_rawfile(uuid, "raw_data.csv")

    df = pd.read_csv(file, delimiter=",")

    preview = df.head(5).to_json(orient="records")

    return preview


@router.post("/data/test/s3_upload/{uuid}")
async def test_s3_upload(uuid: str, filename: str, payload: UploadFile = File(...)):
    try:
        await put_rawfile(uuid, filename, payload)
        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"msg": "File uploaded"},
            content=f"File uploaded to S3 as {filename}",
        )
    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"File could not be uploaded.",
        )


@router.get("/data/test/job_cancel_redo")
def job_cancel_redo_test(uuid: str, job_id: str):
    response = enqueue_job("geotime_processors.process", uuid, job_id)

    time.sleep(5)

    cancel_status = cancel_job(job_id)

    response2 = enqueue_job("geotime_processors.process", uuid, job_id)

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"msg": "Job cancelled and restarted"},
        content=f"Job cancelled and restarted. Cancel status: {cancel_status}",
    )
