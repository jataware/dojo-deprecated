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
    model = get_ontologies(payload)
    es.update(index="models", body={"doc": model}, id=model_id)
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
    model = es.get(index="models", id=model_id)["_source"]

    # Notify Causemos that a model was created
    notify_causemos(model, type="model")

    # Send CauseMos a default run
    submit_run(model)

    return Response(
        status_code=status.HTTP_201_CREATED,
        content=f"Registered model to CauseMos with id = {model_id}"
    )