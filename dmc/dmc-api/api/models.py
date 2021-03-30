from __future__ import annotations

import configparser
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import schemas

router = APIRouter()


config = configparser.ConfigParser()
config.read("/dmc-api/config.ini")
es = Elasticsearch(
    [config["ELASTICSEARCH"]["URL"]], port=config["ELASTICSEARCH"]["PORT"]
)


@router.post("/models")
def create_model(payload: schemas.ModelMetadata):
    model_id = payload.name + str(time.time()).split(".")[0]
    payload.created_at = datetime.now()
    body = payload.json()
    es.index(index="models", body=body, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )


@router.get("/models")
def search_models(query: str = Query(None)) -> List[schemas.ModelMetadata]:
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
