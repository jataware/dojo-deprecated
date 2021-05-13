from __future__ import annotations

import configparser
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import IndicatorSchema

router = APIRouter()


config = configparser.ConfigParser()
config.read("/api/config.ini")
es = Elasticsearch(
    [config["ELASTICSEARCH"]["URL"]], port=config["ELASTICSEARCH"]["PORT"]
)


@router.post("/indicators")
def create_indicator(payload: IndicatorSchema.IndicatorMetadata):
    indicator_id = payload.id
    payload.created = datetime.now()
    body = payload.json()
    es.index(index="indicators", body=body, id=indicator_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Created indicator with id = {indicator_id}",
    )

@router.put("/indicators")
def update_indicator(payload: IndicatorSchema.IndicatorMetadata):
    indicator_id = payload.id
    payload.created = datetime.now()
    body = payload.json()
    es.index(index="indicators", body=body, id=indicator_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Updated indicator with id = {indicator_id}",
    )


@router.get("/indicators")
def search_indicators(query: str = Query(None)) -> List[IndicatorSchema.IndicatorMetadata]:
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
