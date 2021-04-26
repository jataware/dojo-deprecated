################################################################
# Experiments
################################################################

from enum import Enum
from typing import Any, Dict, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

class ExperimentMetadata(BaseModel):
    model: int
    scenarios: List[Dict[str, Any]]
    tags: Optional[List[str]] = []
    job_tags: Optional[List[List[str]]] = []

    class Config:
        extra = "allow"

    @validator("scenarios")
    def prevent_empty_scenarios(cls, scenarios):
        if scenarios == []:
            scenarios = [
                {}
            ]  # Ensures that experiment will be run even if model takes no parameters
        return scenarios

    @validator("job_tags", always=True)
    def match_job_tags_scenarios(cls, job_tags, values):
        num_scenarios = len(values.get("scenarios"))
        num_job_tags = len(job_tags)
        if num_job_tags < num_scenarios:
            job_tags.extend(
                (num_scenarios - num_job_tags) * [[]]
            )  # add empty tags for jobs which don't have tags specified by user
        elif num_scenarios < num_job_tags:
            job_tags = job_tags[:num_scenarios]
        return job_tags
