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


@router.post("/models")
def create_model(
    payload: schemas.ModelMetadata
):
    model_id = 1
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/v1/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )


@router.get("/models")
def get_models(
    inputs: List[str] = Query(None),
    outputs: List[str] = Query(None),
    tags: List[str] = Query(None),
    status: List[str] = Query(None),
    created_since: datetime = Query(None),
) -> List[str]:
    return 


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    model = model
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model_database_to_metadata(model)