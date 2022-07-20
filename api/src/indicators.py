from __future__ import annotations

import csv
import io
import time
import zlib
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import requests
import json
import pandas as pd
import traceback

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, status
from fastapi.logger import logger
from fastapi.responses import StreamingResponse

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
    indicator_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    data = get_ontologies(json.loads(body), type="indicator")

    logger.info(f"Sent indicator to UAZ")
    es.index(index="indicators", body=data, id=indicator_id)

    # Notify Causemos that an indicator was created
    notify_causemos(data, type="indicator")

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Created indicator with id = {indicator_id}",
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


@router.get("/indicators/{indicator_id}/download/csv")
def get_csv(indicator_id: str, request: Request):
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


    async def iter_csv():
        # Build single dataframe
        df = pd.concat(pd.read_parquet(file) for file in indicator["data_paths"])

        # Ensure pandas floats are used because vanilla python ones are problematic
        df = df.fillna('').astype( 
            { col : 'str' for col in df.select_dtypes(include=['float32','float64']).columns }, 
            # Note: This links it to the previous `df` so not a full copy
            copy=False 
        )

        # Prepare for writing CSV to a temporary buffer
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Write out the header row
        writer.writerow(df.columns)

        yield buffer.getvalue()
        buffer.seek(0)  # To clear the buffer we need to seek back to the start and truncate
        buffer.truncate()

        # Iterate over dataframe tuples, writing each one out as a CSV line one at a time
        for record in df.itertuples(index=False, name=None):
            writer.writerow(str(i) for i in record)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()


    async def compress(content):
        compressor = zlib.compressobj()
        async for buff in content:
            yield compressor.compress(buff.encode())
        yield compressor.flush()
 

    if "deflate" in request.headers.get("accept-encoding", ""):
        return StreamingResponse(
            compress(iter_csv()), 
            media_type="text/csv", 
            headers={'Content-Encoding': 'deflate'}
        )
    else:
        return StreamingResponse(
            iter_csv(), 
            media_type="text/csv", 
        )


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
