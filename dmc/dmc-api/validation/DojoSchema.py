################################################################
# Dojo
################################################################

from enum import Enum
from typing import Any, Dict, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

from validation import ModelSchema

class ParameterFormatter(BaseModel):
    """
    A formatter for a model parameters that are date or time
    """

    id: str
    model_id: str = Field(
        title="Model ID",
        description="The ID (`ModelSchema.ModelMetadata.id`) of the related model",
        example="abcd-efg-1233"
    )
    format: str = Field(
        title="Format String",
        description="The format of the model parameter using strftime",
        example="%m/%d/%Y"
    )

class ModelOutputFile(BaseModel):
    id: str
    model_id: str = Field(
        title="Model ID",
        description="The ID (`ModelSchema.ModelMetadata.id`) of the related model",
        example="abcd-efg-1233"
    )
    name: str = Field(
        title="Output File Name",
        description="The name of the output file",
        example="Yield Forecast",
    )
    path: str = Field(
        title="Output File Path",
        description="The relative file path of the output file within the model's `output_directory`",
        example="yield_forecast.csv",
    )
    file_type: str = Field(
        title="Output File Type",
        description="The type of the output file",
        enum=["csv","geotiff","netcdf"],
        example="csv",
    )
    transform: Dict = Field(
        title="SpaceTag Transform Directives",
        description="A dictionary of SpaceTag generated transform directives that are used to convert the model output file into a CauseMos compliant schema",
        example={"x": "lng", "y": "lat"},
    )

    class Config:
        extra = "allow"


class ModelDirective(BaseModel):
    id: str
    model_id: str = Field(
        title="Model ID",
        description="The ID (`ModelSchema.ModelMetadata.id`) of the related model",
        example="abcd-efg-1233"
    )
    command: str = Field(
        title="Model Container command",
        description="The model container command, templated using Jinja. Templated fields must correspond with the name of the model parameters.",
        example="python3 dssat.py --management_practice = {{ management_practice }}"
    )
    output_directory: str = Field(
        title="Model Output Directory",
        description="The location of the model outputs within the model container. This will be mounted in order to retriee output files.",
        example="/results",
    )

    class Config:
        extra = "allow"

class ModelConfig(BaseModel):
    id: str
    model_id: str = Field(
        title="Model ID",
        description="The ID (`ModelSchema.ModelMetadata.id`) of the related model",
        example="abcd-efg-1233"
    )    
    s3_url: str = Field(
        title="S3 URL",
        description="The S3 URL where the config file is located",
        example="https://jataware-world-modelers.s3.amazonaws.com/dummy-model/config.json"
    )
    path: str = Field(
        title="File Path",
        description="The file path where the conf file must be mounted.",
        example="/model/settings/config.json"        
    )

    class Config:
        extra = "allow"   