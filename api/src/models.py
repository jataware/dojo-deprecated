from __future__ import annotations

import logging
import uuid
import time
from copy import deepcopy
from datetime import datetime
import json
from typing import Any, Dict, Generator, List, Optional, Union

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, Body
from fastapi.logger import logger
from validation import ModelSchema, DojoSchema

from src.settings import settings
from src.dojo import search_and_scroll, copy_configs, copy_outputfiles, copy_directive, copy_accessory_files
from src.ontologies import get_ontologies
from src.causemos import notify_causemos, submit_run

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)
logger = logging.getLogger(__name__)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.post("/models")
def create_model(payload: ModelSchema.ModelMetadataSchema, fetch_ontologies=True):
    model_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    
    if fetch_ontologies:
        logger.info(f"Sent model to UAZ")
        model = get_ontologies(json.loads(body), type="model")        
    else:
        model = json.loads(body)
        logger.info(f"Cloning model; not re-sending to UAZ")
        
    es.index(index="models", body=model, id=model_id)

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Created model with id = {model_id}",
    )

@router.get("/models/latest", response_model=DojoSchema.ModelSearchResult)
def get_latest_models(size=100, scroll_id=None) -> DojoSchema.ModelSearchResult:
    q = {
        'query': {
            'bool':{
            'must_not': {
                'exists': {'field' : 'next_version'}
            }}
        }
    }
    if not scroll_id:
        # we need to kick off the query
        results = es.search(index='models', body=q, scroll="2m", size=size)
    else:
        # otherwise, we can use the scroll
        results = es.scroll(scroll_id=scroll_id, scroll="2m")

    # get count
    count = es.count(index='models', body=q)

    # if results are less than the page size (10) don't return a scroll_id
    if len(results["hits"]["hits"]) < int(size):
        scroll_id = None
    else:
        scroll_id = results.get("_scroll_id", None)
    return {
        "hits": count["count"],
        "scroll_id": scroll_id,
        "results": [i["_source"] for i in results["hits"]["hits"]],
    }

@router.put("/models/{model_id}")
def update_model(model_id: str, payload: ModelSchema.ModelMetadataSchema):
    payload.created_at = current_milli_time()
    body = payload.json()
    model = get_ontologies(json.loads(body))
    es.index(index="models", body=model, id=model_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Updated model with id = {model_id}",
    )


@router.patch("/models/{model_id}")
def modify_model(model_id: str, payload: ModelSchema.ModelMetadataPatchSchema):
    body = json.loads(payload.json(exclude_unset=True))
    logging.info(body)
    es.update(index="models", body={"doc": body}, id=model_id)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/models/{model_id}"},
        content=f"Modified model with id = {model_id}",
    )


@router.get("/models", response_model=DojoSchema.ModelSearchResult)
def search_models(
    query: str = None, size: int = 10, scroll_id: str = Query(None)
) -> DojoSchema.ModelSearchResult:
    return search_and_scroll(
        index="models", size=size, query=query, scroll_id=scroll_id
    )


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Model:
    try:
        model = es.get(index="models", id=model_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return model


def delete_model(model_id: str) -> None:
    try:
        es.delete(index="models", id=model_id)
    except:
        pass

@router.post("/models/register/{model_id}")
def register_model(model_id: str):
    """
    This endpoint finalizes the registration of a model by notifying
    Uncharted and submitting to them a default run for the model.
    """
    logger.info("Updating model with latest ontologies.")
    model = es.get(index="models", id=model_id)["_source"]
    model = get_ontologies(model)
    model_obj = ModelSchema.ModelMetadataSchema.parse_obj(model)
    update_model(model_id=model_id, payload=model_obj)


    # Notify Causemos that a model was created
    logger.info("Notifying CauseMos of model registration")
    notify_causemos(model, type="model")

    # Send CauseMos a default run
    logger.info("Submitting defualt run to CauseMos")
    submit_run(model)

    return Response(
        status_code=status.HTTP_201_CREATED,
        content=f"Registered model to CauseMos with id = {model_id}"
    )


@router.get("/models/version/{model_id}")
def version_model(model_id : str):
    """
    This endpoint creates a new version of a model. It is primarily used as part of the model
    editing workflow. When a modeler wishes to edit their model, a new version is created
    and the modelers edits are made against this new (cloned) model.
    """

    def get_updated_outputs(
            outputs: List[Union[ModelSchema.Output, ModelSchema.QualifierOutput]],
            uuid_mapping: Dict[str, str]
    ):
        """
        Helper function to remap Outputs to their new uuids

        Each output or qualifier output has a uuid corresponding to the outputfile idx
        this function changes the uuids in the models outputs and qualifiers to the new model version
        outputfiles uuid. This is the uuid used by spacetag.
        """
        updated_outputs = []
        for output in deepcopy(outputs):
            original_uuid = output.uuid
            new_uuid = uuid_mapping.get(original_uuid)
            if new_uuid:
                output.uuid = new_uuid
                updated_outputs.append(output)
        return updated_outputs

    original_model_definition = get_model(model_id)
    new_id = str(uuid.uuid4())

    # Update required fields from the original definition
    original_model_definition['id'] = new_id
    original_model_definition['prev_version'] = model_id
    if original_model_definition.get('next_version', False):
        del original_model_definition['next_version']

    # Create a new pydantic model for processing
    new_model = ModelSchema.ModelMetadataSchema(**original_model_definition)

    try:
        # Make copies of related items
        outputfile_uuid_mapping = copy_outputfiles(model_id, new_id)
        copy_configs(model_id, new_id)
        copy_directive(model_id, new_id)
        copy_accessory_files(model_id, new_id)

        # Update the created model with the changes related to copying
        if new_model.outputs:
            new_model.outputs = get_updated_outputs(new_model.outputs, outputfile_uuid_mapping)
        if new_model.qualifier_outputs:
            new_model.qualifier_outputs = get_updated_outputs(new_model.qualifier_outputs, outputfile_uuid_mapping)

        # Save model
        create_model(new_model, fetch_ontologies=False)

    except Exception as e:
        # Delete partially created model
        # TODO: Clean up copies configs, directives, accessories, and output file data which may exist even if the
        # TODO: model was never actually created due to error
        delete_model(new_id)
        raise

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/models/{model_id}", "Content-Type": "text/plain"},
        content=new_id
    )
