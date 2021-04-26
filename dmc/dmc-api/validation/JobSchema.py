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

class JobKind(str, Enum):
    RUN = "run"
    IMPORT = "import"


# TODO: Refactor to make more generic.
class JobMetadata(BaseModel):
    kind: Optional[JobKind] = JobKind.RUN
    model: int
    parameters: Dict[str, Any]
    attributes: Optional[Dict[str, Any]] = dict()
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"