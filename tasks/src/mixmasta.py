import logging
from multiprocessing import context
import os
from sqlite3 import connect
from unittest import result

from fastapi import APIRouter, Response, status
from rq import Worker, Queue
from rq.job import Job
from redis import Redis
from rq.exceptions import NoSuchJobError
import json
from rq import job

from src.tasks import generate_mixmasta_files, post_mixmasta_annotation_processing


router = APIRouter()

redis = Redis(
    os.environ.get("REDIS_HOST", "redis-spacetag"), os.environ.get("REDIS_PORT", "6379")
)
q = Queue(connection=redis)


@router.get("/mixmasta/file_generator")
def mixmasta_file_generator(
    context={
        "uuid": 000,
        "mode": "byom",
        "gadm_level": 3,
        "output_directory": "./output",
    }
):
    result = q.enqueue(generate_mixmasta_files, context)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Result": result.to_dict()},
        content=f"Result: {result.to_dict()}",
    )


@router.get("/mixmasta/processor")
def mixmasta_processor():
    # post_mixmasta_annotation_processing()
    result = "Done!"
    return result
