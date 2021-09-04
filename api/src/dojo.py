
import uuid

from typing import List

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

from fastapi import APIRouter, Response, status
from validation import DojoSchema
from src.settings import settings

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)


def search_by_model(model_id):
    q = {"query": {"term": {"model_id.keyword": {"value": model_id, "boost": 1.0}}}}
    return q


def search_and_scroll(index, query=None, size=10, scroll_id=None):
    if query:
        q = {
            "query": {
                "query_string": {
                    "query": query,
                }
            },
        }
    else:
        q = {"query": {"match_all": {}}}
    if not scroll_id:
        # we need to kick off the query
        results = es.search(index=index, body=q, scroll="2m", size=size)
    else:
        # otherwise, we can use the scroll
        results = es.scroll(scroll_id=scroll_id, scroll="2m")

    # get count
    count = es.count(index=index, body=q)

    # if results are less than the page size (10) don't return a scroll_id
    if len(results["hits"]["hits"]) < size:
        scroll_id = None
    else:
        scroll_id = results.get("_scroll_id", None)
    return {
        "hits": count["count"],
        "scroll_id": scroll_id,
        "results": [i["_source"] for i in results["hits"]["hits"]],
    }


@router.post("/dojo/directive")
def create_directive(payload: DojoSchema.ModelDirective):
    """
    Create a `directive` for a model. This is the command which is used to execute
    the model container. The `directive` is templated out using Jinja, where each templated `{{ item }}`
    maps directly to the name of a specific `parameter.
    """

    try:
        es.update(index="directives", body={"doc": payload.dict()}, id=payload.model_id)
        return Response(
            status_code=status.HTTP_200_OK,
            headers={"location": f"/dojo/directive/{payload.model_id}"},
            content=f"Created directive for model with id = {payload.model_id}",
        )
    except NotFoundError:
        es.index(index="directives", body=payload.json(), id=payload.model_id)
        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/dojo/directive/{payload.model_id}"},
            content=f"Created directive for model with id = {payload.model_id}",
        )


@router.get("/dojo/directive/{model_id}")
def get_directive(model_id: str) -> DojoSchema.ModelDirective:
    results = es.search(index="directives", body=search_by_model(model_id))
    try:
        directive = results["hits"]["hits"][-1]["_source"]
        return directive
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Directive for model {model_id} not found.",
        )


@router.post("/dojo/config")
def create_configs(payload: List[DojoSchema.ModelConfig]):
    """
    Create one or more model `configs`. A `config` is a settings file which is used by the model to
    set a specific parameter level. Each `config` is stored to S3, templated out using Jinja, where each templated `{{ item }}`
    maps directly to the name of a specific `parameter.
    """
    for p in payload:
        es.index(index="configs", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/config/{p.id}"},
        content=f"Created config(s) for model with id = {p.model_id}",
    )


@router.get("/dojo/config/{model_id}")
def get_configs(model_id: str) -> List[DojoSchema.ModelConfig]:
    results = es.search(index="configs", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Config(s) for model {model_id} not found.",
        )


@router.post("/dojo/outputfile")
def create_outputfiles(payload: List[DojoSchema.ModelOutputFile]):
    """
    Create an `outputfile` for a model. Each `outputfile` represents a single file that is created upon each model
    execution. Here we store key metadata about the `outputfile` which enables us to find it within the container and
    normalize it into a CauseMos compliant format.
    """
    for p in payload:
        es.index(index="outputfiles", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/outputfile/{p.id}"},
        content=f"Created outputfile(s) for model with id = {p.model_id}",
    )


@router.get("/dojo/outputfile/{model_id}")
def get_outputfiles(model_id: str) -> List[DojoSchema.ModelOutputFile]:
    results = es.search(index="outputfiles", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Outputfile(s) for model {model_id} not found.",
        )


### Accessories Endpoints

@router.get("/dojo/accessories/{model_id}")
def get_accessory_files(model_id: str) -> List[DojoSchema.ModelAccessory]:
    """
    Get the `accessory files` for a model.

    Each `accessory file` represents a single file that is created to be 
    associated with the model. Here we store key metadata about the 
    `accessory file` which  enables us to find it within the container and 
    provide it to Uncharted.
    """
    results = es.search(index="accessories", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Accessory file(s) for model {model_id} not found.",
        )


@router.post("/dojo/accessories")
def create_accessory_file(payload: DojoSchema.ModelAccessory):
    """
    Create or update an `accessory file` for a model. 
    
    Each `accessory file` represents a single file that is created to be 
    associated with the model. Here we store key metadata about the 
    `accessory file` which  enables us to find it within the container and 
    provide it to Uncharted.
    """
    try:
        payload.id = uuid.uuid4() # update payload with uuid
        es.update(index="accessories", body={"doc": payload.dict()}, id=payload.id)
        return Response(
            status_code=status.HTTP_200_OK,
            headers={"location": f"/dojo/accessory/{payload.model_id}"},
            content=f"Created accessory for model with id = {payload.model_id}",
        )
    except NotFoundError:
        es.index(index="accessories", body=payload.json(), id=payload.id)
        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/dojo/accessory/{payload.model_id}"},
            content=f"Created accessory for model with id = {payload.model_id}",
        )


@router.put("/dojo/accessories")
def create_accessory_files(payload: List[DojoSchema.ModelAccessory]):
    """
    The PUT would overwrite the entire array with a new array.

    For each, create an `accessory file` for a model. 
    
    Each `accessory file` represents a single file that is created to be 
    associated with the model. Here we store key metadata about the 
    `accessory file` which  enables us to find it within the container and 
    provide it to Uncharted.
    """
    if len(payload) == 0:
        return Response(status_code=status.HTTP_400_BAD_REQUEST,content=f"No payload")
    
    # Delete previous entries.
    results = es.search(index="accessories", body=search_by_model(payload[0].model_id))
    try:
        for i in results["hits"]["hits"]:
            es.delete(index="accessories", id=i["_source"]["id"])
    except Exception as e:
        logger.error(e)

    # Add the new entries.
    for p in payload:
        p.id = uuid.uuid4() # update payload with uuid
        es.index(index="accessories", body=p.json(), id=p.id)

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/accessory/{p.id}"},
        content=f"Created accessories(s) for model with id = {p.model_id}",
    )
    