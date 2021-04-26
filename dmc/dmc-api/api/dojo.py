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

def search_by_model(model_id):
    q = {
    "query": {
        "match": {
        "model_id": {
            "query": model_id
        }
        }
    }
    }
    return q    

@router.post("/dojo/directive")
def create_directive(payload: DojoSchema.ModelDirective):
    es.index(index="directives", body=payload.json(), id=payload.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/directives/{payload.id}"},
        content=f"Created directive for model with id = {payload.id}",
    )

@router.get("/dojo/directive")
def get_directive(model_id: str) -> DojoSchema.ModelDirective:
    results = es.search(index="directives", body=search_by_model(model_id))
    try:
        directive = results["hits"]["hits"][0]["_source"]
        return directive
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Directive for model {model_id} not found."
        )

@router.post("/dojo/config")
def create_configs(payload: List[DojoSchema.ModelConfig]):
    for p in payload:
        es.index(index="configs", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/config/{p.id}"},
        content=f"Created config(s) for model with id = {p.model_id}",
    )

@router.get("/dojo/config")
def get_outputfiles(model_id: str) -> List[DojoSchema.ModelConfig]:
    results = es.search(index="configs", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Config(s) for model {model_id} not found."
        )    

@router.post("/dojo/outputfile")
def create_outputfiles(payload: List[DojoSchema.ModelOutputFile]):
    for p in payload:
        es.index(index="outputfiles", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/outputfile/{p.id}"},
        content=f"Created outputfile(s) for model with id = {p.model_id}",
    )

@router.get("/dojo/outputfile")
def get_outputfiles(model_id: str) -> List[DojoSchema.ModelOutputFile]:
    results = es.search(index="outputfiles", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Outputfile(s) for model {model_id} not found."
        )    