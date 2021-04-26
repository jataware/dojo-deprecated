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

class CubeMetadataFromModeler(BaseModel):
    """ The fields a modeler needs to provide for cube metadata """

    description: Optional[str] = ""
    parameters: Dict[str, Any]
    independent_vars: List[str]
    dependent_vars: List[str]
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"


class CubeMetadata(CubeMetadataFromModeler):
    """ The fields that are inserted by SuperMaaS in cube metadata """

    job_id: int
    model_id: int
    paths: List[str]
    entries: Optional[List[Any]] = []

    class Config:
        extra = "allow"


class CubePoint(BaseModel):
    # The exclusive purpose of this model is to propagate an example into the Swagger UI.
    # This example describes what a CubePoint may be - namely, a Dict[str, Any]
    class Config:
        schema_extra = {
            "example": {
                "ind_var_1": "<ind_val_1>",
                "ind_var_2": "<ind_val_2>",
                "dep_var_1": "<dep_val_1>",
                "dep_var_2": "<dep_val_2>",
            }
        }

        extra = "allow"