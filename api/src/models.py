from __future__ import annotations

import logging
import uuid
import time
from copy import deepcopy
import json
from typing import Dict, List, Union

from elasticsearch import Elasticsearch

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import ModelSchema, DojoSchema

from src.settings import settings
from src.dojo import search_and_scroll, copy_configs, copy_outputfiles, copy_directive, copy_accessory_files
from src.causemos import notify_causemos, submit_run
from src.utils import run_model_with_defaults

router = APIRouter()

es = Elasticsearch(
    [settings.ELASTICSEARCH_URL],
    port=settings.ELASTICSEARCH_PORT
)
logger = logging.getLogger(__name__)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.get("/models/families")
def list_model_families() -> List(ModelSchema.ModelFamilySchema):

    es_families = es.search(index='model_families')
    families = [
        ModelSchema.ModelFamilySchema(**es_family["_source"])
        for es_family in es_families["hits"]["hits"]
    ]

    return families


@router.post("/models/families")
def create_model_family(family: ModelSchema.ModelFamilySchema):

    es.index(index="model_families", body=family.json(), id=family.family_name)

    return Response(
        status_code=status.HTTP_200_OK,
        content="Model family created"
    )


@router.post("/models")
def create_model(payload: ModelSchema.ModelMetadataSchema):
    model_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()

    # Create a new model family if it doesn't already exist
    if not es.exists(index="model_families", id=payload.family_name):
        logger.info(f"Model family doesn't exist. Creating new one.")
        es.index(
            index="model_families",
            body=ModelSchema.ModelFamilySchema(
                family_name=payload.family_name,
                display_name=payload.family_name,
            ).json(),
            id=payload.family_name
        )

    es.index(index="models", body=json.loads(body), id=model_id)

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
    results = [i["_source"] for i in results["hits"]["hits"]]
    return {
        "hits": count["count"],
        "scroll_id": scroll_id,
        "results": results,
    }


@router.put("/models/{model_id}")
def update_model(model_id: str, payload: ModelSchema.ModelMetadataSchema):
    payload.created_at = current_milli_time()
    model = payload.json()
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


@router.get("/models/{model_id}", response_model=ModelSchema.ModelMetadataSchema)
def get_model(model_id: str) -> ModelSchema.ModelMetadataSchema:
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
    model_obj = ModelSchema.ModelMetadataSchema.parse_obj(model)
    update_model(model_id=model_id, payload=model_obj)

    # On the notification step only, we want to include any previous versions so that they can be deprecated
    previous_versions = model_versions(model_id)['prev_versions']
    model["deprecatesIDs"] = previous_versions

    notify_causemos(model, type="model")
    submit_run(model)

    return Response(
        status_code=status.HTTP_201_CREATED,
        content=f"Registered model to CauseMos with id = {model_id}"
    )


@router.get("/models/version/{model_id}")
def version_model(model_id : str, exclude_files: bool = False):
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

    # Reset variables related to publishing since they don't apply to the new model
    new_model.is_published = False
    new_model.commit_message = None

    try:
        if exclude_files:
            # Update the created model setting the mappings to be empty/blank
            new_model.parameters = []
            new_model.outputs = []
            new_model.qualifier_outputs = []
        else:
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
        create_model(new_model)

        # Assign next_version id to original model after save
        modify_model(model_id=model_id, payload=ModelSchema.ModelMetadataPatchSchema(next_version=new_id))

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


@router.get("/models/{model_id}/versions", response_model=ModelSchema.VersionSchema)
def model_versions(model_id : str) -> ModelSchema.VersionSchema:
    """
    This endpoint returns the model ids for all versions of the model, both any previous version or any later versions.
    """

    model_definition = get_model(model_id)
    prev_versions = []
    later_versions = []
    prev_leaf = model_definition.get("prev_version", None)
    next_leaf = model_definition.get("next_version", None)

    while prev_leaf:
        prev_versions.append(prev_leaf)
        prev_model = get_model(prev_leaf)
        prev_leaf = prev_model.get("prev_version", None)

    while next_leaf:
        later_versions.append(next_leaf)
        next_model = get_model(next_leaf)
        next_leaf = next_model.get("next_version", None)

    prev_versions.reverse()

    return {
        "current_version": model_id,
        "prev_versions": prev_versions,
        "later_versions": later_versions,
    }


@router.post("/models/{model_id}/publish")
def publish_model(model_id: str, publish_data: ModelSchema.PublishSchema):
    """
    This endpoint finalizes the model, setting the state to published and saving a commit message.
    A model should only be able to be edited while is_published is set to false.
    Once a model is published, any changes should be done via a new version.
    """
    # Update the model, setting is_published to True and saving the commit message.
    model = get_model(model_id)
    if model.get("is_published", False):
        return Response(
            status_code=status.HTTP_403_FORBIDDEN,
            content="Model has already been published and cannot be republished.",
        )

    body = json.loads(publish_data.json(exclude_unset=False))
    body["is_published"] = True
    es.update(index="models", body={"doc": body}, id=model_id)

    return Response(
        status_code=status.HTTP_200_OK,
        content="Model published",
    )

@router.get("/models/{model_id}/test")
def test_model(model_id: str):
    """
    This endpoint tests a model's functionality within Dojo.
    """
    run_id = run_model_with_defaults(model_id)
    return Response(
        status_code=status.HTTP_200_OK,
        content=run_id,
    ) 
