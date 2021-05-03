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


class JobMetadata(BaseModel):
    id: str
    model_id: str = Field(
        title="Model ID",
        description="The ID of the model to run",
        example="abcd-efg-1233"
    )
    parameters: Dict[Any, Any] = Field(
        title="Run Parameters",
        description="A dictionary of parameters for the model run. Each key should be the `name` of a model parameter and each `value` the parameter level or setting",
        example={"rainfall": 0.9, "temperature": 1.2}
    )
    attributes: Optional[Dict[str, Any]] = dict()
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"