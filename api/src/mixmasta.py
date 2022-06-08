from __future__ import annotations
import logging
import time
import tempfile
from multiprocessing import context
import os
from sqlite3 import connect
from unittest import result
from io import StringIO
import pandas as pd

from fastapi import APIRouter, Response, File, UploadFile, status
from elasticsearch import Elasticsearch
from rq import Worker, Queue
from rq.job import Job
from redis import Redis
from rq.exceptions import NoSuchJobError
import json
from rq import job

# from src.tasks import generate_mixmasta_files, post_mixmasta_annotation_processing
from src.annotations import get_annotations
from src.indicators import get_indicators

# from src.processing.geotime_processors import GeotimeProcessor


router = APIRouter()

redis = Redis(
    os.environ.get("REDIS_HOST", "redis.world-modelers"),
    os.environ.get("REDIS_PORT", "6379"),
)
q = Queue(connection=redis)


@router.get("/mixmasta/file_generator")
def mixmasta_file_generator(uuid: str):
    #     context={
    #     "uuid": 000,
    #     "mode": "byom",
    #     "gadm_level": 3,
    #     "output_directory": "./output",
    # }
    context = get_context(uuid=uuid)
    job = q.enqueue("tasks.generate_mixmasta_files", context)
    result = job.result
    return Response(
        status_code=status.HTTP_201_CREATED,
        content=f"Result: {result.to_dict()}",
    )


@router.get("/mixmasta/queue/length")
def queue_length():
    return len(q)


@router.post("/mixmasta/queue/empty")
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


@router.get("/mixmasta/processor")
def mixmasta_processor():
    # post_mixmasta_annotation_processing()
    result = "Done!"
    return result


# Should this even be an API endpoint?
@router.post("/mixmasta/geotimeclass/{uuid}")
async def geotime_classify(uuid: str, payload: UploadFile = File(...)):
    try:
        context = get_context(uuid)

        # csv_text = StringIO(payload)
        print(payload.filename)

        payload_wrapper = tempfile.TemporaryFile()
        payload_wrapper.write(await payload.read())
        payload_wrapper.seek(0)

        df = pd.read_csv(payload_wrapper, delimiter=",")

        job = q.enqueue("geotime_processors.process", df, context)

        while job.get_status(refresh=True) != "finished":
            print(job.get_status(refresh=True))
            time.sleep(0.5)

        geoclass_json = job.result

        return Response(
            status_code=status.HTTP_200_OK,
            headers={"msg": "Submitted to geotime classify"},
            content=f"Data returned {geoclass_json}",
        )

    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"Queue could not be deleted.",
        )


def get_context(uuid):
    annotations = get_annotations(uuid)
    meta = get_indicators(uuid)

    context = {"uuid": uuid, "metadata": meta, "annotations": annotations}

    return context


def test_job():
    # Test RQ job
    time.sleep(5)

    print("Job Job")


@router.post("/mixmasta/test/{num_of_jobs}")
def run_test_jobs(num_of_jobs):
    for n in range(int(num_of_jobs)):
        q.enqueue("tasks.test_job")