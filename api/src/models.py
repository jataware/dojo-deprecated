from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, Body
from fastapi.logger import logger
from validation import ModelSchema, DojoSchema

from src.settings import settings

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.post("/models")
def create_model(payload: ModelSchema.ModelMetadataSchema):
    model_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    es.index(index="models", body=body, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )

@router.put("/models/{model_id}")
def update_model(model_id: str, payload: ModelSchema.ModelMetadataSchema):
    payload.created_at = current_milli_time()
    body = payload.json()
    es.index(index="models", body=body, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Updated model with id = {model_id}",
    )

@router.patch("/models/{model_id}")
def modify_model(model_id: str, payload: dict = Body(...)):
    es.update(index="models", body={"doc": payload}, id=model_id)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Modified model with id = {model_id}",
    )


@router.get("/models", response_model=DojoSchema.ModelSearchResult)
def search_indicators(
    query: str = Query(None),
    size: int = 10,
    scroll_id: str = Query(None)
) -> DojoSchema.ModelSearchResult: 
    if query:
        q = {
            "query": {
                "query_string": {
                    "query": query,
                }
            },
        }
    else:
        q = {"query": {"match_all": {}}}
    if not scroll_id:
        # we need to kick off the query
        results = es.search(index="models", body=q, scroll='2m', size=size)
    else:
        # otherwise, we can use the scroll
        results = es.scroll(scroll_id=scroll_id, scroll='2m')

    # get count
    count = es.count(index="models", body=q)

    # if results are less than the page size (10) don't return a scroll_id
    if len(results["hits"]["hits"]) < size:
        scroll_id = None
    else:
        scroll_id = results.get('_scroll_id', None)
    return {
        "hits": count['count'],
        "scroll_id": scroll_id,
        "results": [i["_source"] for i in results["hits"]["hits"]]
    }


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    try:
        model = es.get(index="models", id=model_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model
