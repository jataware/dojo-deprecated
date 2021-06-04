from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger

from validation import IndicatorSchema
from src.settings import settings

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
    es.index(index="indicators", body=body, id=indicator_id)
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


@router.get("/indicators")
def search_indicators(query: str = Query(None)) -> List[IndicatorSchema.IndicatorMetadataSchema]:
    if query:
        q = {
            "size": 100,
            "query": {
                "query_string": {
                    "query": query,
                }
            }
        }
    else:
        q = {"size": 10000, "query": {"match_all": {}}}
    results = es.search(index="indicators", body=q)
    return [i["_source"] for i in results["hits"]["hits"]]


@router.get("/indicators/{indicator_id}")
def get_indicators(indicator_id: str) -> Indicator:
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return indicator
