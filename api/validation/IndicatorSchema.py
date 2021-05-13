################################################################
# Indicators
################################################################

from enum import Enum
from typing import Any, Dict, List, Tuple, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

class AllowableTypes(str, Enum):
    """
    A enumeration of indicator parameter types
    """

    INT = "int"
    FLOAT = "float"
    STR = "str"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    LONGLAT = "longlat"
    BINARY = "binary"
    BOOLEAN = "boolean"

class Geography(BaseModel):
    """ A geography """
    country: List[str] = Field(
        description="list of countries covered by the indicator or data (GADM)",
        example=["Ethiopia","South Sudan"]
    )
    admin1: List[str] = Field(
        description="list of admin1 areas covered by the indicator or data (GADM)",
        example=["Oromia","Sidama","Amhara"]
    )
    admin2: List[str] = Field(
        description="list of admin2 areas covered by the indicator or data (GADM)",
        example=["Agew Awi","Bale","Borona"]
    )
    admin3: List[str] = Field(
        description="list of admin3 areas covered by the indicator or data (GADM)",
        example=["Aminyaa","Coole","Qarsaa"]
    )
    class Config:
        extra = "allow"    

class Concept(BaseModel):
    """ A concept provided by the UAZ Concept Aligner Service """
    name: str = Field(
        title="Concept Name"
    )
    score: float = Field(
        title="Concept Score"
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "wm/concept/causal_factor/food_security/food_utilization",
                "score": 0.9533
            }
        }

class Resolution(BaseModel):
    """ A geospatial and temporal resolution """
    temporal_resolution: str = Field(
        title="Temporal Resolution",
        description="Temporal resolution of the output",
        enum=["annual","monthly","dekad","weekly","daily","other"],
        example="monthly"
    )        
    spatial_resolution: Tuple[float,float] = Field(
        title="Spatial Resolution",
        description="Spatial resolution of the output",
        example=[20,20]
    )

class IndicatorMaintainer(BaseModel):
    """
    Indicator maintainer information
    """

    name: str = Field(
        title="Indicator Maintainer Name",
        description="The full name of the indicator maintainer",
        example="Brad Goodman"
    )
    email: str = Field(
        title="Indicator Maintainer Email",
        description="The email address of the indicator maintainer",
        email="bgoodman@mitre.org"
    )
    organization: Optional[str] = Field(
        title="Indicator Maintainer Organization",
        description="The name of the indicator maintainer organization",
        example="FAO"
    )
    website: Optional[str] = Field(
        title="Indicator Maintainer Website",
        description="The website of the indicator maintainer organization",
        example="https://data.worldbank.org/indicator/SN.ITK.DEFC.ZS"
    )

    class Config:
        extra = "allow"


class IndicatorOutput(BaseModel):
    id: str
    name: str = Field(
        title="Indicator Output Name",
        description="The name of the indicator output",
        example="malnutrition_rate"
    )
    display_name: str = Field(
        title="Indicator Output Display Name",
        description="The display name of the indicator output",
        example="malnutrition rate"
    )    
    description: Optional[str] = Field(
        title="Indicator Output Description",
        description="A description of the indicator output",
        example="Population below minimum level of dietary energy consumption (also referred to as prevalence of undernourishment) shows the percentage of the population whose food intake is insufficient to meet dietary energy requirements continuously. Data showing as 5 may signify a prevalence of undernourishment below 5%."
    )
    type: AllowableTypes = Field(
        title="Indicator Output Type",
        description="The type of the indicator output",
        example="float"
    )
    units: Optional[str] = Field(
        title="Indicator Output Units",
        description="The units for the indicator output",
        example="percent"
    )
    units_description: Optional[str] = Field(
        title="Output Units Description",
        description="Description of the units for the indicator output",
        example="percent"
    )
    concepts: Optional[List[Concept]]
    additional_options: Optional[dict]    
    tags: Optional[List[str]] = Field(
        title="Indicator Output Tags",
        description="Tags associated with a indicator output",
        example=["healthcare"]
    )
    data_resolution: Optional[Resolution] = Field(
        title="Data Resolution",
        description="Spatial and temporal resolution of the data",
    )

    class Config:
        extra = "allow"


class IndicatorMetadata(BaseModel):
    id: str = Field(
        example="abcd-efg-1123"
    )
    name: str = Field(
        title="Indicator Name",
        description="The name of the indicator",
        example="Prevalence of undernourishment (% of population)",
    )
    description: str = Field(
        title="Indicator Description",
        description="A description of the indicator",
        example="Population below minimum level of dietary energy consumption (also referred to as prevalence of undernourishment) shows the percentage of the population whose food intake is insufficient to meet dietary energy requirements continuously. Data showing as 5 may signify a prevalence of undernourishment below 5%.",
    )
    created: Optional[str] = Field(
        title="Indicator Registration Time",
        description="when the indicator was registered",
        example="2021-01-01 10:23:11",
    )
    version: Optional[str] = Field(
        title="Indicator Version",
        description="The version of the indicator",
        example="SN.ITK.DEFC.ZS",
    )
    category: List[str] = Field(
        example=["Economic", "Agricultural"]
    )
    maintainer: IndicatorMaintainer = Field(
        title="Indicator Maintainer",
        description="The maintainer of the indicator",
    )
    outputs: List[IndicatorOutput] = Field(
        title="Indicator Outputs",
        description="Outputs associated with the indicator",
    )
    tags: Optional[List[str]] = Field(
        title="Indicator Output Tags",
        description="Tags associated with a indicator output",
        example=["agriculture", "teff"],
    )    
    geography: Optional[Geography]

    class Config:
        extra = "allow"