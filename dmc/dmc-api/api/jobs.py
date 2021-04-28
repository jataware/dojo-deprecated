import json
import logging
import pathlib
import re
import sys
import time
from threading import Thread, current_thread
from typing import Any, Dict

import configparser
from elasticsearch import Elasticsearch

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from typing_extensions import final

from validation import JobSchema

from api.models import get_model

logger = logging.getLogger(__name__)

router = APIRouter()

config = configparser.ConfigParser()
config.read("/dmc-api/config.ini")
es = Elasticsearch(
    [config["ELASTICSEARCH"]["URL"]], port=config["ELASTICSEARCH"]["PORT"]
)

@router.get("/jobs")
def get_jobs():
    return 

@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    return

def dispatch_job(job):
    return

@router.post("/jobs")
def create_job(job: JobSchema.JobMetadata):
    model = get_model(job.model_id)
    es.index(index="jobs", body=job, id=job.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/jobs/{job.id}"},
        content=f"Created job with id = {job.id}",
    )

@router.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: int):
    return


@router.put("/jobs/{job_id}/kill")
def stop_job(job_id: int):

    return Response(
        status_code=status.HTTP_200_OK,
    )

@router.patch("/jobs/{job_id}", response_model=Dict[str, Any])
def add_metadata(
    job_id: int,
    patch_attributes: Dict[str, Any],
):
    """
    Insert some key-value pair into the `attributes` field of a job's metadata.
    As an example, suppose we use this endpoint to insert `{ "file": "foo.png" }`:

    * If the `attributes` do not yet contain `"file"`, then a new key-value pair
      is inserted into `attributes`, where the key is `"file"` and the value is
      `["foo.png"]`.

    * If the `attributes` *do* contain `"file"`, then the value `"foo.png"` is
      appended to the end of the list that `"file"` maps to in the `attributes`.
      For instance, if the `attributes` previously contained
      `{ "file": ["hi.txt"] }`, then it would contain
      `{ "file": ["hi.txt", "foo.png"] }` after the `PATCH` request.
    """
    return Response(status_code=status.HTTP_200_OK)


@router.get("/jobs/{job_id}/file", include_in_schema=False)
def get_file(
    job_id: int,
):
    return