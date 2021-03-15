from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from pydantic import BaseModel, Field

from validation import schemas

router = APIRouter()


"""
We have two views of models:

* schemas.ModelMetadata. This is what is used when registering models (with POST
  requests) and retrieving models (with GET requests). This corresponds to the
  schema specified in
  https://gitlab-ext.galois.com/world-modelers/galois-internal/supermaas/-/blob/master/docs/metadata.md#model-metadata-schema.

  Another way of saying this, to borrow some turns of phrase from the FastAPI
  documentation (https://fastapi.tiangolo.com/tutorial/extra-models/), is that
  this is the input/output model.
* db.Model. This is what is stored in the SQL database directly. Its schema is
  almost the same as the metadata schema, but instead of having `parameters`
  and `outputs` fields, it instead has a `type` field with the following
  schema:

    Field  Subfields   Type
    type               dict
           parameters  type-dict
           outputs     List of type-dicts

  Where a "type-dict" maps names to { "type": <type>, "annotations": <dict> }
  pairs. This contains exactly the same information as the current schema, but
  with different "type-centric" organization.

  In FastAPI-documentation terms, this is the database model.
"""

"""
Metadata-to-database conversion
"""


def model_parameters_metadata_to_database(
    parameters: List[schemas.ModelParameter],
) -> Dict:
    parameters_db: Dict = {}
    for parameter in parameters:
        parameter_name = parameter.name
        parameter_type = parameter.type

        parameter_annotations = parameter.dict()
        del parameter_annotations["name"]
        del parameter_annotations["type"]

        parameters_db[parameter_name] = {
            "type": parameter_type,
            "annotations": parameter_annotations,
        }
    return parameters_db


def model_outputs_metadata_to_database(
    cubes: List[List[schemas.ModelOutput]],
) -> List[Dict]:
    def gen_cubes() -> Generator[Dict, None, None]:
        for cube in cubes:
            cube_db: Dict = {}
            for column in cube:
                column_name = column.name
                column_type = column.type

                column_annotations = column.dict()
                del column_annotations["name"]
                del column_annotations["type"]

                cube_db[column_name] = {
                    "type": column_type,
                    "annotations": column_annotations,
                }
            yield cube_db

    return list(gen_cubes())


def model_metadata_to_database(mm: schemas.ModelMetadata) -> Model:
    model_parameters = model_parameters_metadata_to_database(mm.parameters)
    model_outputs = model_outputs_metadata_to_database(mm.outputs)
    model_type = {"parameters": model_parameters, "outputs": model_outputs}

    mm_dict = mm.dict()
    del mm_dict["parameters"]
    del mm_dict["outputs"]

    return Model(**mm_dict, created=datetime.now(), type=model_type)


"""
Database-to-metadata conversion
"""


def model_parameters_database_to_metadata(
    parameters_db: Dict,
) -> List[schemas.ModelParameter]:
    def gen_parameters() -> Generator[schemas.ModelParameter, None, None]:
        for parameter_name, parameter_dict in parameters_db.items():
            parameter_type = parameter_dict["type"]
            parameter_annotations = parameter_dict["annotations"]

            yield schemas.ModelParameter(
                **parameter_annotations, name=parameter_name, type=parameter_type
            )

    return list(gen_parameters())


def model_outputs_database_to_metadata(
    cubes_db: List[Dict],
) -> List[List[schemas.ModelOutput]]:
    def gen_columns(cube_db: Dict) -> Generator[schemas.ModelOutput, None, None]:
        for column_name, column_dict in cube_db.items():
            column_type = column_dict["type"]
            column_annotations = column_dict["annotations"]

            yield schemas.ModelOutput(
                **column_annotations, name=column_name, type=column_type
            )

    def gen_cubes() -> Generator[List[schemas.ModelOutput], None, None]:
        for cube_db in cubes_db:
            yield list(gen_columns(cube_db))

    return list(gen_cubes())


def model_database_to_metadata(model_db: Model) -> schemas.ModelMetadata:
    model_parameters = model_parameters_database_to_metadata(
        model_db.type["parameters"]
    )
    model_outputs = model_outputs_database_to_metadata(model_db.type["outputs"])

    model_db_dict = {
        c.key: getattr(model_db, c.key) for c in inspect(model_db).mapper.column_attrs
    }
    del model_db_dict["type"]

    return schemas.ModelMetadata(
        **model_db_dict, parameters=model_parameters, outputs=model_outputs
    )


@router.post("/models")
def create_model(
    payload: schemas.ModelMetadata
):
    model = model_metadata_to_database(payload)
    session.add(model)
    session.commit()
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/v1/models/{model.id}"},
        content=f"Created model with id = {model.id}",
    )


@router.get("/models")
def get_models(
    inputs: List[str] = Query(None),
    outputs: List[str] = Query(None),
    tags: List[str] = Query(None),
    status: List[str] = Query(None),
    created_since: datetime = Query(None),
) -> List[str]:
    filters = []
    return 


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    model = session.query(Model).get(model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model_database_to_metadata(model)
