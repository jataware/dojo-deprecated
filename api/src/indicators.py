from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import requests
import json
import traceback

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
import logging


from validation import IndicatorSchema, DojoSchema
from src.settings import settings

from src.dojo import search_and_scroll

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)

# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


def get_ontology(data):
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    url = f"http://linking.cs.arizona.edu/v1/groundIndicator?maxHits=10&threshold=0.7&compositional=true"

    try:
        response = requests.put(url, json=data, headers=headers)
        logger.debug(f"response: {response}")
        logger.debug(f"response reason: {response.raw.reason}")

        # Ensure good response and not an empty response
        if response.status_code == 200:
            resp_str = response.content.decode("utf8")
            ontologies = json.loads(resp_str)

            # Capture UAZ ontology data
            ontology_dict = {}
            for ontology in ontologies["outputs"]:
                key = ontology["name"]
                datuh = ontology["ontologies"]
                ontology_dict[key] = datuh

            return ontology_dict
            
        else:
            logger.debug(f"else response: {response}")
            return response

    except Exception as e:
        logger.debug(f"get_ontology exception: {str(e)}")
        logger.debug(f"get_ontology traceback: {traceback.format_exc()}")


@router.post("/indicators")
def create_indicator(payload: IndicatorSchema.IndicatorMetadataSchema):
    indicator_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    data = json.loads(body)

    # UAZ API Does not return ontologies for "qualifier_outputs" so work on just "outputs" for now
    try:
        ontology_dict = get_ontology(data)
        for output in data["outputs"]:
            output["ontologies"] = ontology_dict[output["name"]]

        logger.debug(f"Data with UAZ: {data}")

    except Exception as e:
        logger.debug(f"create_indicator exception: {str(e)}")
        logger.debug(f"create traceback: {traceback.format_exc()}")

    try:
        body = json.dumps(data)
        es.index(index="indicators", body=body, id=indicator_id)

    except Exception as e:
        logger.debug(f"elastic search traceback: {traceback.format_exc()}")

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


@router.get("/indicators", response_model=DojoSchema.IndicatorSearchResult)
def search_indicators(
    query: str = Query(None), size: int = 10, scroll_id: str = Query(None)
) -> DojoSchema.IndicatorSearchResult:
    return search_and_scroll(
        index="indicators", size=size, query=query, scroll_id=scroll_id
    )


@router.get("/indicators/{indicator_id}")
def get_indicators(indicator_id: str) -> IndicatorSchema.IndicatorMetadataSchema:
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return indicator
