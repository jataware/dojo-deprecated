################################################################
# Cubes
################################################################

from enum import Enum
from typing import Any, Dict, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

from validation.ModelSchema import Geography

class Period(BaseModel):
    gte: str = Field(
        title="Start Time",
        description="Start time (inclusive)",
        example="2019-01-01T00:00:00Z"
    )
    lte: str = Field(
        title="End Time",
        description="End time (inclusive)",
        example="2020-01-01T00:00:00Z"
    )
    resolution: str = Field(
        title="Temporal Resolution",
        enum=["annual", "monthly", "dekad", "weekly", "daily", "other"]
    )

class Parameter(BaseModel):
    id: str = Field(
        title="Parameter ID",
        description="The ID of the parameter",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    value: Any = Field(
        title="Parameter Value",
        example="irrig"
    )

class CubeMetadata(BaseModel):
    """ Metadata describing a datacube """
    id: str
    name: str
    description: str
    created: Optional[str]
    job_id: str
    model_id: str
    data_paths: List[str]
    pre_gen_output_paths: Optional[List[str]]
    default_run: Optional[bool]
    parameters: List[Parameter]
    periods: Optional[List[Period]]
    tags: Optional[List[str]] = []
    geography: Optional[Geography]

    class Config:
        extra = "allow"
