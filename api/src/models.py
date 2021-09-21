from __future__ import annotations

import time
from datetime import datetime
import json
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, Body
from fastapi.logger import logger
from validation import ModelSchema, DojoSchema

from src.settings import settings
from src.dojo import search_and_scroll
from src.ontologies import get_ontologies
from src.causemos import notify_causemos, submit_run

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
    
    model = get_ontologies(json.loads(body), type="model")
    logger.info(f"Sent model to UAZ")
    es.index(index="models", body=model, id=model_id)

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )


@router.put("/models/{model_id}")
def update_model(model_id: str, payload: ModelSchema.ModelMetadataSchema):
    payload.created_at = current_milli_time()
    body = payload.json()
    model = get_ontologies(json.loads(body))
    es.index(index="models", body=model, id=model_id)
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
def search_models(
    query: str = Query(None), size: int = 10, scroll_id: str = Query(None)
) -> DojoSchema.ModelSearchResult:
    return search_and_scroll(
        index="models", size=size, query=query, scroll_id=scroll_id
    )


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    try:
        model = es.get(index="models", id=model_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model


@router.post("/models/register/{model_id}")
def register_model(model_id: str):
    """
    This endpoint finalizes the registration of a model by notifying 
    Uncharted and submitting to them a default run for the model.
    """
    logger.info("Updating model with latest ontologies.")
    model = es.get(index="models", id=model_id)["_source"]
    model = get_ontologies(model)
    model_obj = ModelSchema.ModelMetadataSchema.parse_obj(model)
    update_model(model_id=model_id, payload=model_obj)


    # Notify Causemos that a model was created
    logger.info("Notifying CauseMos of model registration")
    notify_causemos(model, type="model")

    # Send CauseMos a default run
    logger.info("Submitting defualt run to CauseMos")
    submit_run(model)

    return Response(
        status_code=status.HTTP_201_CREATED,
        content=f"Registered model to CauseMos with id = {model_id}"
    )


@router.put("/models/version/{model_id}/{version_name}")
def version_model(model_id : str, version_name :str, payload : dict):
    #payload structure delete non present fields?
    #endpoint to version a model, model_id = original_id - version_name
    model = get_model(model_id)
    
    original_model_change = {}
    original_model_change['original_id'] = model.get('original_id', model_id)
    prev_version = model.get('version', '')
    original_model_change['next_version'] = version_name
    modify_model(model_id, original_model_change)
    
    model['id'] = f'{original_model_change["original_id"]}-{original_model_change["next_version"]}'
    model['original_id'] = model.get('original_id' , model_id)
    model['version'] = version_name
    
    for x in payload.keys():
        model[x] = payload[x]
    
    if model.get('next_version', False):
        del model['next_version']
    
    model['prev_version'] = prev_version
    es.index(index="models", body=model, id=model['id'])
    return True

@router.get("/models/latest/{model_id}")
def get_latest_model(model_id: str):
    model = es.get(index="models", id=model_id)["_source"]
    while model.get('next_version', False):
        
        model = es.get(index="models", id=f"{model_id}-{model['next_version']}")["_source"]
    return model

@router.get("/models/latest/")
def get_latest_models(scroll_id=None, size=100):
    search_param = {
        'query': {
            'bool':{
            'must_not': {
                'exists': {'field' : 'next_version'}
            }}
        }
    }
    
    if not scroll_id:
        # we need to kick off the query
        results = es.search(index="models", size=size, scroll="2m", body=search_param)

    else:
        # otherwise, we can use the scroll
        results = es.scroll(scroll_id=scroll_id, scroll="2m")

    # get count


    # if results are less than the page size (10) don't return a scroll_id
    if len(results["hits"]["hits"]) < size:
        scroll_id = None
    else:
        scroll_id = results.get("_scroll_id", None)
    return {
        "hits": len([i["_source"] for i in results["hits"]["hits"]]),
        "scroll_id": scroll_id,
        "results": [i["_source"] for i in results["hits"]["hits"]],
    }