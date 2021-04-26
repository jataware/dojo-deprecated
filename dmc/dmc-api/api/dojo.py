from __future__ import annotations

import configparser
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import DojoSchema

router = APIRouter()


config = configparser.ConfigParser()
config.read("/dmc-api/config.ini")
es = Elasticsearch(
    [config["ELASTICSEARCH"]["URL"]], port=config["ELASTICSEARCH"]["PORT"]
)


@router.post("/dojo/directive")
def create_directive(payload: DojoSchema.ModelDirective):
    es.index(index="directives", body=payload.json(), id=payload.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/directives/{payload.id}"},
        content=f"Created directive for model with id = {payload.id}",
    )

@router.get("/dojo/directive")
def get_directive(query: str = Query(str)) -> DojoSchema.ModelDirective:
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

@router.get("/dojo/config")
def create_configs(payload: List[DojoSchema.ModelConfig]):
    for p in payload:
        es.index(index="configs", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/config/{payload.id}"},
        content=f"Created config(s) for model with id = {payload.id}",
    )


@router.get("/dojo/outputfile")
def create_outputfiles(payload: List[DojoSchema.ModelOutputFile]):
    for p in payload:
        es.index(index="outputfiles", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/outputfile/{payload.id}"},
        content=f"Created outputfile(s) for model with id = {payload.id}",
    )