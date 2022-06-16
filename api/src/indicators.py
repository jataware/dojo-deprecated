from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlparse

import requests
import json
import traceback

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field
import boto3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, UploadFile, File
from fastapi.logger import logger

from validation import IndicatorSchema, DojoSchema
from src.settings import settings

from src.dojo import search_and_scroll
from src.ontologies import get_ontologies
from src.causemos import notify_causemos
from src.causemos import deprecate_dataset

import os

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.post("/indicators")
def create_indicator(payload: IndicatorSchema.IndicatorMetadataSchema):
    indicator_id = str(uuid.uuid4())
    payload.id = indicator_id
    payload.created_at = current_milli_time()
    body = payload.json()
    payload.published = False

    es.index(index="indicators", body=body, id=indicator_id)
    # TODO: Move this to publish
        # data = get_ontologies(json.loads(body), type="indicator")
        # logger.info(f"Sent indicator to UAZ")

        # Notify Causemos that an indicator was created
        # notify_causemos(data, type="indicator")

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={
            "location": f"/api/indicators/{indicator_id}",
            "content-type": "application/json",
        },
        content=body,
    )


@router.put("/indicators")
def update_indicator(payload: IndicatorSchema.IndicatorMetadataSchema):
    indicator_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    es.index(index="indicators", body=body, id=indicator_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Updated indicator with id = {indicator_id}",
    )


@router.get(
    "/indicators/latest", response_model=List[IndicatorSchema.IndicatorsSearchSchema]
)
def get_latest_indicators(size=10000):
    q = {
        "_source": [
            "description",
            "name",
            "id",
            "created_at",
            "deprecated",
            "maintainer.name",
            "maintainer.email",
        ],
        "query": {"match_all": {}},
    }
    results = es.search(index="indicators", body=q, size=size)["hits"]["hits"]
    IndicatorsSchemaArray = []
    for res in results:
        IndicatorsSchemaArray.append(res.get("_source"))
    return IndicatorsSchemaArray


@router.get("/indicators", response_model=DojoSchema.IndicatorSearchResult)
def search_indicators(
    query: str = Query(None),
    size: int = 10,
    scroll_id: str = Query(None),
    include_ontologies: bool = True,
    include_geo: bool = True,
) -> DojoSchema.IndicatorSearchResult:
    indicator_data = search_and_scroll(
        index="indicators", size=size, query=query, scroll_id=scroll_id
    )
    # if request wants ontologies and geo data return all
    if include_ontologies and include_geo:
        return indicator_data
    else:
        for indicator in indicator_data["results"]:
            if not include_ontologies:
                for q_output in indicator["qualifier_outputs"]:
                    try:
                        q_output["ontologies"] = {
                            "concepts": None,
                            "processes": None,
                            "properties": None,
                        }
                    except Exception as e:
                        print(e)
                for outputs in indicator["outputs"]:
                    try:
                        outputs["ontologies"] = {
                            "concepts": None,
                            "processes": None,
                            "properties": None,
                        }
                    except Exception as e:
                        print(e)
            if not include_geo:
                indicator["geography"]["country"] = []
                indicator["geography"]["admin1"] = []
                indicator["geography"]["admin2"] = []
                indicator["geography"]["admin3"] = []

        return indicator_data


@router.get(
    "/indicators/{indicator_id}", response_model=IndicatorSchema.IndicatorMetadataSchema
)
def get_indicators(indicator_id: str) -> IndicatorSchema.IndicatorMetadataSchema:
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return indicator


@router.put("/indicators/{indicator_id}/deprecate")
def deprecate_indicator(indicator_id: str):
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
        indicator["deprecated"] = True
        es.index(index="indicators", id=indicator_id, body=indicator)

        # Tell Causemos to deprecate the dataset on their end
        deprecate_dataset(indicator_id)
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Deprecated indicator with id {indicator_id}",
    )


@router.post("/indicators/{indicator_id}/upload")
def upload_file(indicator_id: str, file: UploadFile = File(...)):
    location_info = urlparse(settings.DATASET_STORAGE_BASE_URL)
    original_filename = file.filename
    _, ext= os.path.splitext(original_filename)
    filename = f"raw_data{ext}"
    output_dir = os.path.join(location_info.path, indicator_id)
    output_path = os.path.join(output_dir, filename)


    if location_info.scheme.lower() == "file":
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "wb") as output_file:
            output_file.write(file.file.read())
    elif location_info.scheme.lower() == "s3":
        output_path = output_path.lstrip("/")
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=location_info.netloc,
            Key=output_path,
            Body=file.file
        )
    else:
        raise RuntimeError("Upload destination format is unknown")

    # TODO Store original filename in metadata & update metadata with file location

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Uploaded file to with id {indicator_id}",
    )
    
