################################################################
# This file defines schemas for metadata and checks their validity
# This includes models, cubes, jobs, experiments
# For models and cubes, it follows the schemas defined in https://gitlab-ext.galois.com/world-modelers/galois-internal/supermaas/-/blob/master/docs/metadata.md

# Conventions followed for ease of UI implementation:
## Optional fields have their defaults set to the type inside Optional
## For example, Optional[List[str]] is basically a list which is optional, so default is []
## Similarly, Optional[Dict] = {}, Optional[str] = ""
## Optional[Any] types have default None

# Validators are always run (always=True) for Optional fields since we may want to check their existence / absence
# Validators are not run (default always=False) for compulsory fields since we do not want the validator to run on None
## None is the the system-wide default value for not-provided compulsory fields
################################################################

from enum import Enum
from typing import Any, Dict, List, Optional

import dateutil.parser
from pydantic import BaseModel, Field, validator
from shapely.geometry import LineString, Point, Polygon
from toposort import CircularDependencyError, toposort_flatten

from validation import api_types as types

################################################################
# Models
################################################################


class ModelStatus(str, Enum):
    CURRENT = "current"  # image exists and can be run
    FAULTY = "faulty"  # image exists, run may fail
    NOT_RUNNABLE_CURRENT = "not-runnable-current"  # image doesn't exist, typically ghost models which only have pregen datacubes
    RUNNABLE_DEPRECATED = (
        "runnable-deprecated"  # image exists, but a more recent version of model exists
    )
    NOT_RUNNABLE_DEPRECATED = "not-runnable-deprecated"  # image doesn't exist, more recent version of model exists


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


class ModelParameter(BaseModel):
    """
    A model parameter
    """

    name: str = Field(
        title="Parameter Name",
        description="The name of the model parameter",
    )
    description: Optional[str] = Field(
        title="Parameter description",
        description="The description of the model parameter",
    )
    type: AllowableTypes = Field(
        title="Parameter Type",
        description="The type of model parameter",
    )
    depends_on: Optional[Dict[str, str]] = Field(
        title="Parameter Dependencies",
        description="A dictionary of parameter dependencies",
    )
    tags: Optional[List[str]] = Field(
        title="Parameter Tags",
        description="Tags associated with the parameter",
    )
    choices: Optional[List[Any]] = Field(
        title="Parameter Choices",
        description="Choices associated with the parameter",
    )
    min: Optional[Any] = Field(
        title="Minimum Value",
        description="Minimum value of the parameter",
    )
    max: Optional[Any] = Field(
        title="Maximum Value",
        description="Maximm value of the parameter",
    )
    boundary: Optional[List[List[float]]] = Field(
        title="Parameter Boundary",
        description="The boundary for the parameter",
    )
    default: Optional[Any] = Field(
        title="Default Value",
        description="The default value of the parameter",
    )

    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "name": "management_practice",
                "description": "The management practice to model. rf_highN corresponds to a high nitrogen management  practice. irrig corresponds to a high nitrogen, irrigated management practice. rf_0N  corresponds to a subsistence management practice. rf_lowN corresponds to a low nitrogen  managemet practice.",
                "type": "str",
                "choices": ["irrig", "rf_highN", "rf_lowN", "rf_0N"],
                "default": "irrig",
                "tags": ["agriculture", "farm management"],
            }
        }


class ModelOutput(BaseModel):
    name: str = Field(
        title="Model Output Name",
        description="The name of the model output",
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
    tags: Optional[List[str]] = Field(
        title="Model Output Tags",
        description="Tags associated with a model output",
    )

    class Config:
        extra = "allow"
        schema_extra = {
            "example": [
                {
                    "name": "HWAH",
                    "description": "Harvested weight at harvest (kg/ha).",
                    "type": "float",
                    "tags": ["agriculture"],
                },
                {
                    "name": "SDAT",
                    "description": "Sowing Date",
                    "type": "datetime",
                    "tags": ["agriculture"],
                },
            ]
        }


class ModelOutputFile(BaseModel):
    name: str = Field(
        title="Output File Name",
        description="The name of the output file",
        example="Yield Forecast",
    )
    path: str = Field(
        title="Output File Path",
        description="The full file path of the output file within the model container image",
        example="/home/ubuntu/dssat/results/yield_forecast.csv",
    )
    features: List[ModelOutput] = Field(
        title="Output Features",
        description="An array of features contained within the output file",
    )

    class Config:
        extra = "allow"


class ModelDirectives(BaseModel):
    command: str = Field(
        title="Model Container command",
        description="The model container command, templated using Jinja. Templated fields must correspond with the name of the model parameters.",
    )
    output_directory: str = Field(
        title="Model Output Directory",
        description="The location of the model outputs within the model container. This will be mounted in order to retriee output files.",
    )

    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "command": "python3 dssat.py --management_practice = {{ management_practice }}",
                "output_directory": "/output",
            }
        }


class ModelMetadata(BaseModel):
    name: str = Field(
        title="Model Name",
        description="The name of the model",
        example="DSSAT",
    )
    version: Optional[str] = Field(
        title="Model Version",
        description="The version of the model",
        example="DSSAT",
    )
    description: Optional[str] = Field(
        title="Model Description",
        description="A description of the model",
        example="The Decision Support System for Agrotechnology Transfer (DSSAT) comprises dynamic crop growth simulation model for over 40 crops. The model simulates growth development; and yield as a function of the soil-plant-atmosphere dynamics.",
    )
    image: Optional[str] = Field(
        title="Model Image",
        description="The name and tag of the model image",
        example="DSSAT_Pythia:latest",
    )
    status: Optional[ModelStatus] = Field(
        ModelStatus.CURRENT,
        title="Model Status",
        description="The status of the model",
    )
    maintainer: Optional[ModelMaintainer] = Field(
        {},
        title="Model Maintainer",
        description="The maintainer of the model",
    )
    parameters: List[ModelParameter] = Field(
        title="Model Parameters",
        description="Parameters assocaited with the model",
    )
    outputs: List[ModelOutputFile] = Field(
        title="Model Outputs",
        description="Outputs associated with the model",
    )
    directives: ModelDirectives = Field(
        title="Model Directives",
        description="Directives associated with model parameterization and execution",
    )
    tags: Optional[List[str]] = Field(
        title="Model Output Tags",
        description="Tags associated with a model output",
        example=["agriculture", "teff"],
    )

    class Config:
        extra = "allow"


################################################################
# Cubes
################################################################


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


################################################################
# Jobs
################################################################


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


################################################################
# Experiments
################################################################


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
