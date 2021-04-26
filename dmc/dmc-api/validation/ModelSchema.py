################################################################
# Models
################################################################

from enum import Enum
from typing import Any, Dict, List, Tuple, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon

from toposort import CircularDependencyError, toposort_flatten
from validation import api_types as types

class ModelStatus(str, Enum):
    CURRENT = "current"  # image exists and can be run
    FAULTY = "faulty"  # image exists, run may fail
    NOT_RUNNABLE_CURRENT = "not-runnable-current"  # image doesn't exist, typically ghost models which only have pregen datacubes
    RUNNABLE_DEPRECATED = (
        "runnable-deprecated"  # image exists, but a more recent version of model exists
    )
    NOT_RUNNABLE_DEPRECATED = "not-runnable-deprecated"  # image doesn't exist, more recent version of model exists


class AllowableTypes(str, Enum):
    """
    A enumeration of model parameter types
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
        description="list of countries covered by the model or data (GADM)",
        example=["Ethiopia","South Sudan"]
    )
    admin1: List[str] = Field(
        description="list of admin1 areas covered by the model or data (GADM)",
        example=["Oromia","Sidama","Amhara"]
    )
    admin2: List[str] = Field(
        description="list of admin2 areas covered by the model or data (GADM)",
        example=["Agew Awi","Bale","Borona"]
    )
    admin3: List[str] = Field(
        description="list of admin3 areas covered by the model or data (GADM)",
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

class ModelMaintainer(BaseModel):
    """
    Model maintainer information
    """

    name: str = Field(
        title="Model Maintainer Name",
        description="The full name of the model maintainer",
    )
    email: str = Field(
        title="Model Maintainer Email",
        description="The email address of the model maintainer",
    )
    organization: Optional[str] = Field(
        title="Model Maintainer Organization",
        description="The name of the model maintainer organization",
    )
    website: Optional[str] = Field(
        title="Model Maintainer Website",
        description="The website of the model maintainer organization",
    )

    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "name": "Cheryl Porter",
                "email": "cporter@ufl.edu",
                "organization": "University of Florida",
                "website": "http://ufl.edu",
            }
        }


class ModelParameter(BaseModel):
    """
    A model parameter
    """

    id: str
    name: str = Field(
        title="Parameter Name",
        description="The name of the model parameter",
    )
    display_name: str = Field(
        title="Parameter Display Name",
        description="The display name of the model parameter",
    )    
    description: Optional[str] = Field(
        title="Parameter description",
        description="The description of the model parameter",
    )
    type: AllowableTypes = Field(
        title="Parameter Type",
        description="The type of model parameter",
    )
    unit: Optional[str] = Field(
        title="Parameter Unit",
        description="The unit of the parameter"
    )
    unit_description: Optional[str] = Field(
        title="Parameter Unit Description",
        description="A short description of the unit of the parameter"
    )
    concepts: Optional[List[Concept]]
    is_drilldown: Optional[bool] = Field(
        title="Is Drilldown?",
        description="Does this variable represent a drilldown"
    )
    additional_options: Optional[Dict]
    depends_on: Optional[Dict]
    data_type: str = Field(
        title="Data Value Type",
        description="Describes whether the data values will be categorical, ordered, or numerical",
        enum=["nominal","ordinal","numerical"],
    )
    default: Any = Field(
        title="Default Value",
        description="The default value of the parameter",
    )    
    tags: Optional[List[str]] = Field(
        title="Parameter Tags",
        description="Tags associated with the parameter",
    )
    choices: Optional[List[str]] = Field(
        title="Parameter Choices",
        description="Choices associated with the parameter",
    )
    min: Optional[str] = Field(
        title="Minimum Value",
        description="Minimum value of the parameter",
    )
    max: Optional[str] = Field(
        title="Maximum Value",
        description="Maximm value of the parameter",
    )
    boundary: Optional[List[List[float]]] = Field(
        title="Parameter Boundary",
        description="The boundary for the parameter",
    )    

    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "id": "1234-5678-91011",
                "name": "management_practice",
                "display_name": "Farming Management Practice",
                "description": "The management practice to model. rf_highN corresponds to a high nitrogen management  practice. irrig corresponds to a high nitrogen, irrigated management practice. rf_0N  corresponds to a subsistence management practice. rf_lowN corresponds to a low nitrogen  managemet practice.",
                "type": "str",
                "unit": "degC",
                "unit_description": "degrees Celcius",
                "concepts": [{"name": "wm/concept/causal_factor/food_security/food_utilization", "score": 0.976}],
                "is_drilldown": True,
                "data_type": "nominal",
                "choices": ["irrig", "rf_highN", "rf_lowN", "rf_0N"],
                "default": "irrig",
                "tags": ["agriculture", "farm management"],
            }
        }


class ModelOutput(BaseModel):
    id: str
    name: str = Field(
        title="Model Output Name",
        description="The name of the model output",
    )
    display_name: str = Field(
        title="Model Output Display Name",
        description="The display name of the model output",
    )    
    description: Optional[str] = Field(
        title="Model Output Description",
        description="A description of the model output",
    )
    type: AllowableTypes = Field(
        title="Model Output Type",
        description="The type of the model output",
    )
    units: Optional[str] = Field(
        title="Model Output Units",
        description="The units for the model output",
    )
    units_description: Optional[str] = Field(
        title="Output Units Description",
        description="Description of the units for the model output",
    )
    concepts: Optional[List[Concept]]
    additional_options: Optional[dict]    
    tags: Optional[List[str]] = Field(
        title="Model Output Tags",
        description="Tags associated with a model output",
    )
    data_resolution: Optional[Resolution] = Field(
        title="Data Resolution",
        description="Spatial and temporal resolution of the data",
    )

    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "name": "HWAH",
                "description": "Harvested weight at harvest (kg/ha).",
                "type": "float",
                "tags": ["agriculture"],
            }
        }

class ModelMetadata(BaseModel):
    id: str = Field(
        example="abcd-efg-1123"
    )
    name: str = Field(
        title="Model Name",
        description="The name of the model",
        example="DSSAT",
    )
    description: str = Field(
        title="Model Description",
        description="A description of the model",
        example="The Decision Support System for Agrotechnology Transfer (DSSAT) comprises dynamic crop growth simulation model for over 40 crops. The model simulates growth development; and yield as a function of the soil-plant-atmosphere dynamics.",
    )
    created: Optional[str] = Field(
        title="Model Registration Time",
        description="when the model was registered",
        example="2021-01-01T10:23:11Z",
    )
    version: Optional[str] = Field(
        title="Model Version",
        description="The version of the model",
        example="DSSAT",
    )
    status: Optional[ModelStatus] = Field(
        ModelStatus.CURRENT,
        title="Model Status",
        description="The status of the model",
    )
    category: List[str] = Field(
        example=["Economic", "Agricultural"]
    )
    maintainer: ModelMaintainer = Field(
        title="Model Maintainer",
        description="The maintainer of the model",
    )
    image: str = Field(
        title="Model Image",
        description="The name and tag of the model image",
        example="DSSAT_Pythia:latest",
    )
    type: str = Field(
        title="Model Type",
        description="Does this represent a bottom-up model or an indicator",
        enum=["model", "indicator"],
        example="model"
    )
    model_dependencies: Optional[List[str]] = Field(
        title="Model Dependencies",
        description="Array of dependencies represented as model or data IDs"
    )
    observed_data: Optional[List[str]] = Field(
        title="Observed Data",
        description="A list of Cube IDs that represent observed data for this model"
    )
    stochastic: Optional[bool] = Field(
        title="Is stochastic?",
        description="Is the model stochastic",
        default=False
    )
    cube_count: Optional[int] = Field(
        title="Cube Count",
        description="How many data cubes each job of the model produces",
        default=1
    )    
    parameters: List[ModelParameter] = Field(
        title="Model Parameters",
        description="Parameters assocaited with the model",
    )
    outputs: List[ModelOutput] = Field(
        title="Model Outputs",
        description="Outputs associated with the model",
    )
    tags: Optional[List[str]] = Field(
        title="Model Output Tags",
        description="Tags associated with a model output",
        example=["agriculture", "teff"],
    )    
    geography: Optional[Geography]

    class Config:
        extra = "allow"