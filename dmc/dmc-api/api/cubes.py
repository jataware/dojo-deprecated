import json
import logging
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from tempfile import NamedTemporaryFile, TemporaryFile, mkstemp
from threading import Thread
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from validation import CubeSchema

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/cubes")
def get_cubes(
    models: List[str] = Query(None),
    dependent_vars: List[str] = Query(None),
    independent_vars: List[str] = Query(None),
    created_since: datetime = Query(None),
) -> List[str]:
    return


@router.post("/cubes")
def create_cube(payload: CubeSchema.CubeMetadata):
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/v1/cubes/{cube.id}"},
    )


@router.post("/cubes/open")
def empty_cube(payload: CubeSchema.CubeMetadata):
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/v1/cubes/{cube.id}"},
        content=f"Created cube with id = {cube.id}",
    )


def upload_frame(cube: str, df: pd.DataFrame, bucket: str, key=None) -> str:
    """
    Upload a (or a portion of a) cube to S3
    """
    return key


def store_intermediate(filename, cube_id):
    """
    Write a raw file to a special bucket, to preserve failed bulk uploads
    """
    return

def causemos_compliant(df: pd.DataFrame) -> bool:
    """
    The definition of causemos compliance for this function:
    Column headers include notions of time named "timestamp" and notions
      of place called either ("country") or ("lat" and "lng"), as well as
      columns called "feature" and "value"
    Timestamps are integral
    Values are floating-point
    """

    # per uncharted, the first is desirable but the second is acceptable
    # XXX: admin1-adminN?
    minimal_columns = {"timestamp", "lat", "lng", "feature", "value"} <= set(
        df.columns
    ) or {"timestamp", "country", "feature", "value"} <= set(df.columns)

    if "timestamp" in df.columns:
        # check that the type is somehow integral
        integral_timestamps = "int" in str(df["timestamp"].dtype)  # type: ignore
    else:
        # lack of a 'timestamp' column to begin with leads to noncompliance
        integral_timestamps = False

    if "value" in df.columns and len(df["value"]) > 0:
        # check that the type is floating point
        numeric_values = "float" in str(df["value"].dtype)  # type: ignore
    else:
        # lack of a 'values' column to begin with leads to noncompliance
        numeric_values = False

    logger.debug(f"columns?        {minimal_columns}")
    logger.debug(f"timestamps?     {integral_timestamps}")
    logger.debug(f"numeric values? {numeric_values}")
    return minimal_columns and integral_timestamps and numeric_values


def preview_frame(df: pd.DataFrame) -> List[List[Any]]:
    """
    Generate a preview of the provided DataFrame

    Use to automatically populate the `entries` field of cube metadata
    """
    subset = df[:10]  # type: ignore
    columns = list(subset.columns)
    values = subset.values.tolist()
    return [columns] + values


@router.post("/cubes/{cube_id}/bulk/{format}")
def upload_points(
    cube_id: int,
    format: str,
    upload: UploadFile = File(...),
):
    return Response(status_code=status.HTTP_201_CREATED)


@router.post("/cubes/{cube_id}/add-metadata")
def add_metadata(
    cube_id: int,
    metadata: Dict,
):
    return Response(status_code=status.HTTP_200_OK)

@router.post("/cubes/{cube_id}/close")
def close_cube(
    cube_id: int,
):
    return Response(status_code=status.HTTP_200_OK)


@router.get("/cubes/{cube_id}/data")
def download_data(
    cube_id: int,
):
    return
