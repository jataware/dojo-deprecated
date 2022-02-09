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


from validation import IndicatorSchema, DojoSchema
from src.settings import settings

from src.dojo import search_and_scroll
from src.ontologies import get_ontologies
from src.causemos import notify_causemos

import os

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

    data = get_ontologies(json.loads(body), type="indicator")
    logger.info(f"Sent indicator to UAZ")
    es.index(index="indicators", body=data, id=indicator_id)

    # Notify Causemos that an indicator was created
    notify_causemos(data, type="indicator")
    
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

@router.get("/indicators/latest")
def get_latest_indicators(size=10000) -> DojoSchema.IndicatorSearchResult:
    q =  { "_source": ["description", "name", "id", "created_at","maintainer.name"],
         "query": {
        "match_all":{}
            }
           }
    results = es.search(index='indicators', body=q,size=size)
    print(results)

    return {
        "results": results,
    }

@router.get("/indicators" )
def search_indicators(
    query: str = Query(None), size: int = 10, scroll_id: str = Query(None),ontologies:bool=True ,geo:bool=True
) -> DojoSchema.IndicatorSearchResult:
    print(ontologies, geo)
    resp= search_and_scroll(
        index="indicators", size=size, query=query, scroll_id=scroll_id
    )
    #if request wants ontologies and geo data return all
    if ontologies and geo:
        return resp

    reducedData = resp

    if not ontologies or geo:
        print('try to remove on tologies')
        for i,indicator in enumerate(reducedData['results']):
            if not ontologies:
                for ind, ontology in enumerate(indicator['qualifier_outputs']):
                    try:
                        reducedData['results'][i]['qualifier_outputs'][ind]['ontologies']={
                                                "concepts": None,
                                                "processes": None,
                                                "properties":None
                                                }
                    except Exception as e:
                        print(e)
                for ind_out, ontology_out in enumerate(indicator['outputs']):
                    try:
                        reducedData['results'][i]['outputs'][ind_out]['ontologies']={
                                                "concepts": None,
                                                "processes": None,
                                                "properties":None
                                                }
                    except Exception as e:
                        print(e)
            if not geo:
                reducedData['results'][i]['geography']['country']=[]
                reducedData['results'][i]['geography']['admin1'] = []
                reducedData['results'][i]['geography']['admin2'] = []
                reducedData['results'][i]['geography']['admin3'] = []
    else:
        print('did not try anythin')


    return reducedData


@router.get("/indicators/{indicator_id}")
def get_indicators(indicator_id: str) -> IndicatorSchema.IndicatorMetadataSchema:
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return indicator


@router.put("/indicators/{indicator_id}/deprecate")
def deprecate_indicator(indicator_id: str):
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
        indicator["deprecated"] = True
        es.index(index="indicators", id=indicator_id, body=indicator)
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Deprecated indicator with id {indicator_id}",
    )




