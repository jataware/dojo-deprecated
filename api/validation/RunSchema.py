################################################################
# Jobs
################################################################

from enum import Enum
from typing import Any, Dict, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

class RunParameter(BaseModel):
    name: str = Field(
        title="Parameter Name",
        description="The name of the parameter",
        example="Management Practice"
    )
    value: Any = Field(
        title="Parameter Value",
        description="Set value of parameter during run",
        example="irrig"
    )

class RunMetadata(BaseModel):
    id: str
    model_name: str = Field(
        title="Model Name",
        description="The name of the model",
        example="DSSAT"
    )    
    model_id: str = Field(
        title="Model ID",
        description="The ID of the model to run",
        example="abcd-efg-1233"
    )
    created_at: str = Field(
        title="Run creation time",
        description="The time the run was kicked off",
        example="1970-01-01T00:00:00Z"
    )
    data_paths: List[str] = Field(
        title="Data URL Paths",
        description="URL paths to output datacubes",
        example=["runs/<run-id>/<cube-id-1>","runs/<run-id>/<cube-id-2>"]
    )
    pre_gen_output_paths: List[str] = Field(
        title="Pre-generated output URL Paths",
        description="URL paths to pre-generated output",
        example=["runs/<run-id>/<cube-id-1>/pre-gen"]
    )
    is_default_run: bool = Field(
        title="Default Run?",
        description="Is this the default run of the model",
        default=False
    )
    parameters: List[RunParameter] = Field(
        title="Run Parameters",
        description="A dictionary of parameters for the model run. Each key should be the `name` of a model parameter and each `value` the parameter level or setting",
    )
    attributes: Optional[Dict[str, Any]] = dict()
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"