from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import ModelSchema

from src.settings import settings

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)

@router.post("/models")
def create_model(payload: ModelSchema.ModelMetadata):
    model_id = payload.id
    payload.created = datetime.now()
    body = payload.json()
    es.index(index="models", body=body, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )

@router.put("/models")
def update_model(payload: ModelSchema.ModelMetadata):
    model_id = payload.id
    payload.created = datetime.now()
    body = payload.json()
    es.index(index="models", body=body, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Updated model with id = {model_id}",
    )


@router.get("/models")
def search_models(query: str = Query(None)) -> List[ModelSchema.ModelMetadata]:
    if query:
        q = {
            "query": {
                "query_string": {
                    "query": query,
                }
            }
        }
    else:
        q = {"query": {"match_all": {}}}
    results = es.search(index="models", body=q)
    return [i["_source"] for i in results["hits"]["hits"]]


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    try:
        model = es.get(index="models", id=model_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model
