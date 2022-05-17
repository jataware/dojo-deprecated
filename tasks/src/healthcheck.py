from __future__ import annotations

from datetime import datetime
import requests

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger

from src.settings import settings

router = APIRouter()

es = Elasticsearch(
    [settings.ELASTICSEARCH_URL + ":" + str(settings.ELASTICSEARCH_PORT)]
)


@router.get("/healthcheck")
def get_health():

    # DOJO (actually ElasticSearch Health) Status
    try:
        dojo_status = es.cluster.health()["status"]
        print(f"Dojo: {dojo_status}")
    except Exception as e:
        logger.exception(e)
        dojo_status = "broken"

    status = {
        "dojo": "ok"
        if dojo_status == "yellow" or dojo_status == "green"
        else "Failed Health Check",
    }
    return status
