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
from pydantic import BaseModel, validator
from shapely.geometry import LineString, Point, Polygon
from toposort import CircularDependencyError, toposort_flatten

from validation import api_types as types

################################################################
# Utilities
################################################################

param_type_allowed_set = set(types.type_mapping.keys())
output_type_allowed_set = param_type_allowed_set - {"datacube"}


def param_type_validity(typ):
    return type_validity(typ, param_type_allowed_set)


def output_type_validity(typ):
    return type_validity(typ, output_type_allowed_set)


def type_validity(typ, allowed_set):
    typ = typ.replace("-", "").replace("/", "").replace(" ", "")
    typ = typ.lower()

    if typ == "latlong":
        typ = "longlat"
    if typ == "string":
        typ = "str"
    if typ == "integer":
        typ = "int"
    if typ == "cube" or typ == "data":
        typ = "datacube"

    if typ not in allowed_set:
        raise TypeError(f"must be in {allowed_set}, instead got '{typ}'")
    return typ


def model_param_requires_choices(typ: Optional[str]) -> bool:
    """
    All parameters in a model are required to enumerate choices, save for the
    following exceptions.
    """
    return typ not in ["boolean", "binary", "datacube"]


def model_param_requires_default(typ: Optional[str]) -> bool:
    """
    All parameters in a model are required to specify a default value, save for
    the following exceptions.
    """
    return typ not in ["binary", "datacube"]


def privileged_tag(tags: Optional[List[str]]) -> bool:
    return (tags is not None) and ("supermaas::privileged" in tags)


def point_in_polygon(point, boundary):
    """
    Check if a point is inside or on the boundary of a polygon defined by boundary

    point: List with 2 elements, e.g. [0,0]
    boundary: List of lists of 2 elements. Obeys boundary rules found here: https://gitlab-ext.galois.com/world-modelers/galois-internal/supermaas/-/blob/master/docs/metadata.md#boundary

    Note: Do NOT pass shapely objects as arguments, just pass ordinary Python lists
    """
    point = Point(point)
    return point.within(Polygon(boundary)) or point.within(LineString(boundary))


def check_param_value(
    value: Any,
    name: str,
    typ: str,
    choices: List[Any] = [],
    min: Any = None,
    max: Any = None,
    boundary: List[List[float]] = [],
):
    """
    Check if a given value can be valid for a particular parameter

    value: The value being checked
    name: The name of the parameter
    typ: The type of the parameter
    choices, min, max, boundary: Additional details about the parameter
    """
    if (
        typ in param_type_allowed_set
    ):  # required, since typ can be None if the type_validity check fails
        invalid_value = types.type_mapping[typ].validate(name, value)
        if invalid_value is not None:
            raise ValueError(invalid_value)
    """
    An alternative to above would be:
    try:
        invalid_value = types.type_mapping[typ].validate(name, value)
        if invalid_value is not None:
            raise ValueError(invalid_value)
    except KeyError:
        raise TypeError(f"Given type = {typ} is not in the the allowable list = {param_type_allowed_set}")
    But that would be checking for type validity twice
    """

    if choices not in [[], None]:
        """
        When choices is not provided, its default value is [].
        Then why do we check for None as a possible value for choices?
        This is because the validator `check_choices` runs prior to this validator.
        If validation fails there, the returned value of choices becomes None (this is just the way Pydantic works).
        For such cases, we don't want the check here to be performed.
        So we check choices for None and exclude this check if choices is indeed None.
        """
        if value not in choices:
            raise ValueError(
                f"Given value = {value} for {typ} type parameter '{name}' is not in its list of choices = {choices}"
            )

    elif typ in ["int", "float", "date", "time", "datetime"]:
        if min is not None and max is not None:
            if typ in ["int", "float"]:
                _min, _max, _value = min, max, value
            else:
                _min, _max, _value = (
                    dateutil.parser.parse(min),
                    dateutil.parser.parse(max),
                    dateutil.parser.parse(value),
                )
            if not _min <= _value <= _max:
                raise ValueError(
                    f"Given value = {value} for {typ} type parameter '{name}' is not between its min = {min} and max = {max}"
                )

    elif typ == "longlat":
        if boundary not in [[], None] and not point_in_polygon(value, boundary):
            """
            When boundary is not provided, its default value is [].
            Then why do we check for None as a possible value for boundary?
            See the explanation for choices above.
            """
            raise ValueError(
                f"Given value = {value} for longlat type parameter '{name}' is not inside or on the polygon formed by its boundary = {boundary}"
            )


################################################################
# Models
################################################################

# fmt: off
class ModelStatus(str, Enum):
    CURRENT = "current"  # image exists and can be run
    FAULTY = "faulty"  # image exists, run may fail
    NOT_RUNNABLE_CURRENT = "not-runnable-current"  # image doesn't exist, typically ghost models which only have pregen datacubes
    RUNNABLE_DEPRECATED = "runnable-deprecated" # image exists, but a more recent version of model exists
    NOT_RUNNABLE_DEPRECATED = "not-runnable-deprecated" # image doesn't exist, more recent version of model exists
# fmt: on


class ModelMaintainer(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    organization: Optional[str] = ""
    website: Optional[str] = ""

    class Config:
        extra = "allow"


class ModelParameter(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str
    depends_on: Optional[Dict[str, str]] = {}
    tags: Optional[List[str]] = []
    choices: Optional[List[Any]] = []
    min: Optional[Any] = None
    max: Optional[Any] = None
    boundary: Optional[List[List[float]]] = []
    default: Optional[Any] = None

    class Config:
        extra = "allow"

    _type_validity = validator("type", pre=True, allow_reuse=True)(param_type_validity)

    @validator("choices", always=True)
    def check_choices(cls, choices, values):
        typ, name = values.get("type"), values.get("name")
        if choices != []:
            if not model_param_requires_choices(typ):
                print(
                    f"WARNING: choices will be deleted for {typ} type parameter '{name}'"
                )
                choices = []
            elif typ in param_type_allowed_set:
                errors = []
                for i, choice in enumerate(choices):
                    error = types.type_mapping[typ].validate(f"choices[{i}]", choice)
                    errors.extend([error] if error is not None else [])
                if len(errors) > 0:
                    raise ValueError(
                        f"choices for {typ} type parameter '{name}' has the following errors:\n"
                        + "\n".join(errors)
                        + "\n"
                    )
        return choices

    @validator("min", "max", always=True)
    def check_minmax(cls, limit, values):
        typ, choices, name = (
            values.get("type"),
            values.get("choices"),
            values.get("name"),
        )
        if typ in ["int", "float", "datetime", "date", "time"]:
            if choices == []:
                if limit is None:
                    raise ValueError(
                        f"must provide either (min and max), or choices, for {typ} type parameter '{name}'"
                    )
                else:
                    error = types.type_mapping[typ].validate("min/max", limit)
                    if error is not None:
                        raise ValueError(error)
            elif limit is not None:
                print(
                    f"WARNING: choices exist for parameter '{name}', so its min and max will be deleted"
                )
                limit = None
        return limit

    @validator("boundary", always=True)
    def check_boundary(cls, boundary, values):
        choices, name = values.get("choices"), values.get("name")
        if values.get("type") == "longlat":
            if choices == []:
                if boundary == []:
                    raise ValueError(
                        f"must provide either non-empty list of boundary longlat coordinates, or choices, for longlat type parameter '{name}'"
                    )
                elif len(boundary) < 4 or boundary[-1] != boundary[0]:
                    raise ValueError(
                        f"must provide boundary with at least 4 coordinates and equal first and last coordinates for longlat type parameter '{name}'"
                    )
                else:
                    errors = []
                    for i, longlat in enumerate(boundary):
                        error = types.type_mapping["longlat"].validate(
                            f"boundary[{i}]", longlat
                        )
                        errors.extend([error] if error is not None else [])
                    if len(errors) > 0:
                        raise ValueError(
                            f"boundary for longlat type parameter '{name}' has the following errors:\n"
                            + "\n".join(errors)
                            + "\n"
                        )
            elif boundary != []:
                print(
                    f"WARNING: choices exist for parameter '{name}', so its boundary will be deleted"
                )
                boundary = []
        return boundary

    @validator("default", always=True)
    def check_default(cls, default, values):
        typ, name = values.get("type"), values.get("name")

        if default is None:
            if model_param_requires_default(typ) and not privileged_tag(
                values.get("tags")
            ):
                raise ValueError(
                    f"must provide 'default' for {typ} type parameter '{name}'"
                )

        else:
            check_param_value(
                value=default,
                name=name,
                typ=typ,
                choices=values.get("choices"),
                min=values.get("min"),
                max=values.get("max"),
                boundary=values.get("boundary"),
            )

        return default

    # Note that we do not need separate checks for min <= max since `check_param_value()` accomplishes the same thing in the course of checking min <= default <= max


class ModelOutput(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str
    units: Optional[str] = ""
    units_description: Optional[str] = ""
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"

    _type_validity = validator("type", pre=True, allow_reuse=True)(output_type_validity)


class ModelMetadata(BaseModel):
    name: str
    version: Optional[str] = ""
    description: Optional[str] = ""
    image: Optional[str] = ""  # only runnable models have images
    status: Optional[ModelStatus] = ModelStatus.CURRENT
    maintainer: Optional[ModelMaintainer] = {}
    parameters: List[ModelParameter]
    outputs: List[List[ModelOutput]]
    tags: Optional[List[str]] = []

    class Config:
        extra = "allow"

    @validator("status", always=True)
    def set_status(cls, status, values):
        """
        If image is not provided, do the following to model status:
        - CURRENT, FAULTY and NOT_RUNNABLE_CURRENT will map to NOT_RUNNABLE_CURRENT
        - RUNNABLE_DEPRECATED and NOT_RUNNABLE_DEPRECATED will map to NOT_RUNNABLE_DEPRECATED
        """
        if values.get("image") == "":
            if status in [
                ModelStatus.RUNNABLE_DEPRECATED,
                ModelStatus.NOT_RUNNABLE_DEPRECATED,
            ]:
                status = ModelStatus.NOT_RUNNABLE_DEPRECATED
            else:
                status = ModelStatus.NOT_RUNNABLE_CURRENT
        return status

    @validator("parameters")
    def parameter_dependency_validity(cls, parameters):
        param_names = [param.name for param in parameters]
        for param in parameters:
            for key in param.depends_on.keys():
                if key not in param_names:
                    raise ValueError(
                        f"{param.name}['depends_on'] keys must be in parameter name set = {set(param_names)-{param.name}}, instead got '{key}'"
                    )
                if key == param.name:
                    raise ValueError(f"{param.name} cannot depend on itself")
        return parameters

    @validator("parameters")
    def parameter_dependency_ordering(cls, parameters):
        """ Re-orders parameters according to dependencies, with independents first """
        topo_in = {}
        param_names = [param.name for param in parameters]
        for index, param in enumerate(parameters):
            dependencies = [
                param_names.index(param_name) for param_name in param.depends_on.keys()
            ]
            topo_in[index] = set(dependencies)

        try:
            topo_out = toposort_flatten(topo_in)
            parameters = [
                parameters[index] for index in topo_out
            ]  # rearrange parameters
        except CircularDependencyError:  # do nothing
            print(
                "WARNING: Parameters have circular dependencies, leaving order unchanged!"
            )

        return parameters


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
