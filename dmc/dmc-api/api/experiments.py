import json
import logging
import pathlib
import sys
from threading import Thread, current_thread
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.logger import logger
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

from validation import ExperimentSchema

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/experiments")
def get_experiments():
    return


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    return


@router.post("/experiments")
def create_experiment(
    payload: ExperimentSchema.ExperimentMetadata,
):
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/experiments/{experiment.id}"},
    )
