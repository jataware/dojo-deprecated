from __future__ import annotations

import csv
import io
import time
import zlib
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlparse

import json
import pandas as pd

from elasticsearch import Elasticsearch
import pandas as pd
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status,
    UploadFile,
    File,
    Request,
)
from fastapi.logger import logger
from fastapi.responses import StreamingResponse

from validation import IndicatorSchema, DojoSchema, MetadataSchema
from src.settings import settings

from src.dojo import search_and_scroll
from src.ontologies import get_ontologies
from src.causemos import notify_causemos
from src.causemos import deprecate_dataset
from src.utils import put_rawfile, get_rawfile, list_files
from validation.IndicatorSchema import (
    IndicatorMetadataSchema,
    QualifierOutput,
    Output,
    Period,
    Geography,
)

import os

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.post("/indicators")
def create_indicator(payload: IndicatorSchema.IndicatorMetadataSchema):
    indicator_id = str(uuid.uuid4())
    payload.id = indicator_id
    payload.created_at = current_milli_time()
    body = payload.json()
    payload.published = False

    es.index(index="indicators", body=body, id=indicator_id)
    empty_annotations_payload = MetadataSchema.MetaModel(metadata={}).json()
    es.index(index="annotations", body=empty_annotations_payload, id=indicator_id)
    # TODO: Move this to publish
    # data = get_ontologies(json.loads(body), type="indicator")
    # logger.info(f"Sent indicator to UAZ")

    # Notify Causemos that an indicator was created
    # notify_causemos(data, type="indicator")

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={
            "location": f"/api/indicators/{indicator_id}",
            "content-type": "application/json",
        },
        content=body,
    )


@router.put("/indicators")
def update_indicator(payload: IndicatorSchema.IndicatorMetadataSchema):
    indicator_id = payload.id
    payload.created_at = current_milli_time()
    body = payload.json()
    es.index(index="indicators", body=body, id=indicator_id)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Updated indicator with id = {indicator_id}",
    )


@router.patch("/indicators")
def patch_indicator(
    payload: IndicatorSchema.IndicatorMetadataSchema, indicator_id: str
):
    payload.created_at = current_milli_time()
    body = json.loads(payload.json(exclude_unset=True))
    es.update(index="indicators", body={"doc": body}, id=indicator_id)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Updated indicator with id = {indicator_id}",
    )


@router.get(
    "/indicators/latest", response_model=List[IndicatorSchema.IndicatorsSearchSchema]
)
def get_latest_indicators(size=10000):
    q = {
        "_source": [
            "description",
            "name",
            "id",
            "created_at",
            "deprecated",
            "maintainer.name",
            "maintainer.email",
        ],
        "query": {
            "bool": {
                "must": [{"match_all": {}}],
                "filter": [{"term": {"published": True}}],
            }
        },
    }
    results = es.search(index="indicators", body=q, size=size)["hits"]["hits"]
    IndicatorsSchemaArray = []
    for res in results:
        IndicatorsSchemaArray.append(res.get("_source"))
    return IndicatorsSchemaArray


@router.get("/indicators", response_model=DojoSchema.IndicatorSearchResult)
def search_indicators(
    query: str = Query(None),
    size: int = 10,
    scroll_id: str = Query(None),
    include_ontologies: bool = True,
    include_geo: bool = True,
) -> DojoSchema.IndicatorSearchResult:
    indicator_data = search_and_scroll(
        index="indicators", size=size, query=query, scroll_id=scroll_id
    )
    # if request wants ontologies and geo data return all
    if include_ontologies and include_geo:
        return indicator_data
    else:
        for indicator in indicator_data["results"]:
            if not include_ontologies:
                for q_output in indicator["qualifier_outputs"]:
                    try:
                        q_output["ontologies"] = {
                            "concepts": None,
                            "processes": None,
                            "properties": None,
                        }
                    except Exception as e:
                        print(e)
                for outputs in indicator["outputs"]:
                    try:
                        outputs["ontologies"] = {
                            "concepts": None,
                            "processes": None,
                            "properties": None,
                        }
                    except Exception as e:
                        print(e)
            if not include_geo:
                indicator["geography"]["country"] = []
                indicator["geography"]["admin1"] = []
                indicator["geography"]["admin2"] = []
                indicator["geography"]["admin3"] = []

        return indicator_data


@router.get(
    "/indicators/{indicator_id}", response_model=IndicatorSchema.IndicatorMetadataSchema
)
def get_indicators(indicator_id: str) -> IndicatorSchema.IndicatorMetadataSchema:
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return indicator


@router.put("/indicators/{indicator_id}/publish")
def publish_indicator(indicator_id: str):
    try:
        # Update indicator model with ontologies from UAZ
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
        indicator["published"] = True
        data = get_ontologies(indicator, type="indicator")
        logger.info(f"Sent indicator to UAZ")
        es.index(index="indicators", body=data, id=indicator_id)

        # Notify Causemos that an indicator was created
        notify_causemos(data, type="indicator")
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}/publish"},
        content=f"Published indicator with id {indicator_id}",
    )


@router.get("/indicators/{indicator_id}/download/csv")
def get_csv(indicator_id: str, request: Request):
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async def iter_csv():
        # Build single dataframe
        df = pd.concat(pd.read_parquet(file) for file in indicator["data_paths"])

        # Ensure pandas floats are used because vanilla python ones are problematic
        df = df.fillna("").astype(
            {
                col: "str"
                for col in df.select_dtypes(include=["float32", "float64"]).columns
            },
            # Note: This links it to the previous `df` so not a full copy
            copy=False,
        )

        # Prepare for writing CSV to a temporary buffer
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Write out the header row
        writer.writerow(df.columns)

        yield buffer.getvalue()
        buffer.seek(
            0
        )  # To clear the buffer we need to seek back to the start and truncate
        buffer.truncate()

        # Iterate over dataframe tuples, writing each one out as a CSV line one at a time
        for record in df.itertuples(index=False, name=None):
            writer.writerow(str(i) for i in record)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()

    async def compress(content):
        compressor = zlib.compressobj()
        async for buff in content:
            yield compressor.compress(buff.encode())
        yield compressor.flush()

    if "deflate" in request.headers.get("accept-encoding", ""):
        return StreamingResponse(
            compress(iter_csv()),
            media_type="text/csv",
            headers={"Content-Encoding": "deflate"},
        )
    else:
        return StreamingResponse(
            iter_csv(),
            media_type="text/csv",
        )


@router.put("/indicators/{indicator_id}/deprecate")
def deprecate_indicator(indicator_id: str):
    try:
        indicator = es.get(index="indicators", id=indicator_id)["_source"]
        indicator["deprecated"] = True
        es.index(index="indicators", id=indicator_id, body=indicator)

        # Tell Causemos to deprecate the dataset on their end
        deprecate_dataset(indicator_id)
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"location": f"/api/indicators/{indicator_id}"},
        content=f"Deprecated indicator with id {indicator_id}",
    )


# TODO this function isn't much less gross than the original, needs cleanup.
@router.post("/indicators/mixmasta_update/{uuid}")
def update_indicator_with_mixmasta_results(uuid, filename_list=None, append=False):
    # Get the mixmasta results
    if filename_list is None:
        filename_list = [f"{uuid}.parquet.gzip"]
    parquet_filename = filename_list[0]
    parquet_path = os.path.join(
        settings.DATASET_STORAGE_BASE_URL, uuid, parquet_filename
    )
    mixmasta_results = get_rawfile(parquet_path)
    parquet_df = pd.read_parquet(mixmasta_results)
    meta_annotations = get_annotations(uuid)
    original_indicator = get_indicators(uuid)

    # Init schema
    indicator = IndicatorMetadataSchema(
        name=original_indicator["name"],
        description=original_indicator["description"],
        maintainer=original_indicator["maintainer"],
    )

    # We update data_paths, outputs, qualifier_outputs, geography, and period from the mixmasta results and then patch the indicator.

    # Data_paths
    dir_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, uuid)
    all_files = list_files(dir_path)
    indicator.data_paths = original_indicator["data_paths"]
    for file in all_files:
        if file in filename_list:
            indicator.data_paths.append(file)

    # Outputs
    indicator.qualifier_outputs = []
    indicator.outputs = []
    feature_names = []
    for feature in meta_annotations["annotations"]["feature"]:
        feature_names.append(feature["name"])  # Used for the primary qualifier outputs.
        output = Output(
            name=feature["name"],
            display_name=feature["display_name"],
            description=feature["description"],
            type=feature["feature_type"],
            unit=feature["units"],
            unit_description=feature["units_description"],
            ontologies={},
            is_primary=True,
            data_resolution={
                "data_resolution": {
                    "temporal_resolution": "annual",
                    "spatial_resolution": None,
                }
            },  # TODO will be something like meta_annotations["metadata"]["data_resolution"] instead of hardcoded values.
            alias=feature["aliases"],
        )
        # Append
        indicator.outputs.append(output)
        # Qualifier output for qualifying features
        if len(feature["qualifies"]) > 0:
            qualifier_output = QualifierOutput(
                name=feature["name"],
                display_name=feature["display_name"],
                description=feature["description"],
                # Gross conversion between the two output types.
                type=(
                    "str"
                    if feature["feature_type"] == "string"
                    else "binary"
                    if feature["feature_type"] == "boolean"
                    else feature["feature_type"]
                ),
                unit=feature["units"],
                unit_description=feature["units_description"],
                ontologies={},
                related_features=feature["qualifies"],
            )
            # Append to qualifier outputs
            indicator.qualifier_outputs.append(qualifier_output)

    # Qualifier_outputs
    for date in meta_annotations["annotations"]["date"]:
        if date["primary_date"]:
            qualifier_output = QualifierOutput(
                name=date["name"],
                display_name=date["display_name"],
                description=date["description"],
                type="datetime",
                unit=date.get("units", None),
                unit_description=date.get("units_description", None),
                ontologies={},
                related_features=feature_names,
                # Extra field (Schema allows extras)
                qualifier_role="breakdown",
            )
            # Append
            indicator.qualifier_outputs.append(qualifier_output)

    # TODO potentially update description dynamically if present in annotations
    for geo_str in ["country", "admin1", "admin2", "admin3", "lat", "lng"]:
        qualifier_output = QualifierOutput(
            name=geo_str,
            display_name=geo_str,
            description="location",
            type=geo_str,
            unit=None,
            unit_description=None,
            ontologies={},
            related_features=feature_names,
            # Extra field (Schema allows extras)
            qualifier_role="breakdown",
        )
        # Append
        indicator.qualifier_outputs.append(qualifier_output)

    # Geography
    geography_dict = {}
    for x in ["admin1", "admin2", "admin3", "country"]:
        geography_dict[x] = [
            x for x in parquet_df[parquet_df[x].notna()][x].unique() if x != "nan"
        ]
    # Deals with the append case, if we are not appending we can just add None and it doesn't change anything.
    if append:
        original_geography = original_indicator["geography"]
    else:
        original_geography = dict(
            Geography(country=[], admin1=[], admin2=[], admin3=[])
        )
    if len(geography_dict["country"]) < 10:
        geography = Geography(
            country=geography_dict["country"] + original_geography["country"],
            admin1=geography_dict["admin1"] + original_geography["admin1"],
            admin2=geography_dict["admin2"] + original_geography["admin2"],
            admin3=geography_dict["admin3"] + original_geography["admin3"],
        )
        indicator.geography = geography
    else:
        geography = Geography(
            country=geography_dict["country"],
        )
        indicator.geography = geography

    # Period
    if not parquet_df.timestamp.isnull().all():
        # If we are appending, take the last gte and lte and add them to the pandas series to find the new max and min.
        if original_indicator["period"] is not None:
            original_period = original_indicator["period"]
            indicator.period = Period(
                gte=int(
                    max(parquet_df.timestamp.append(pd.Series(original_period["gte"])))
                ),
                lte=int(
                    min(parquet_df.timestamp.append(pd.Series(original_period["lte"])))
                ),
            )
        else:
            indicator.period = Period(
                gte=int(max(parquet_df.timestamp)), lte=int(min(parquet_df.timestamp))
            )

    logger.info(f"INDICATOR {indicator}")

    # Patch the indicator with the results
    return patch_indicator(payload=indicator, indicator_id=uuid)


@router.get(
    "/indicators/{indicator_id}/annotations", response_model=MetadataSchema.MetaModel
)
def get_annotations(indicator_id: str) -> MetadataSchema.MetaModel:
    """Get annotations for a dataset.

    Args:
        indicator_id (str): The UUID of the dataset to retrieve annotations for from elasticsearch.

    Raises:
        HTTPException: This is raised if no annotation is found for the dataset in elasticsearch.

    Returns:
        MetadataSchema.MetaModel: Returns the annotations pydantic schema for the dataset that contains a metadata dictionary and an annotations object validated via a nested pydantic schema.
    """
    try:
        annotation = es.get(index="annotations", id=indicator_id)["_source"]
        return annotation
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return None


@router.post("/indicators/{indicator_id}/annotations")
def post_annotation(payload: MetadataSchema.MetaModel, indicator_id: str):
    """Post annotations for a dataset.

    Args:
        payload (MetadataSchema.MetaModel): Payload needs to be a fully formed json object representing the pydantic schema MettaDataSchema.MetaModel.
        indicator_id (str): The UUID of the dataset to retrieve annotations for from elasticsearch.

    Returns:
        Response: Returns a response with the status code of 201 and the location of the annotation.
    """
    try:

        body = json.loads(payload.json())

        es.index(index="annotations", body=body, id=indicator_id)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{indicator_id}"},
            content=f"Updated annotation with id = {indicator_id}",
        )
    except:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not update annotation with id = {indicator_id}",
        )


@router.put("/indicators/{indicator_id}/annotations")
def put_annotation(payload: MetadataSchema.MetaModel, indicator_id: str):
    """Put annotation for a dataset to Elasticsearch.

    Args:
        payload (MetadataSchema.MetaModel): Payload needs to be a fully formed json object representing the pydantic schema MettaDataSchema.MetaModel.
        indicator_id (str): The UUID of the dataset for which the annotations apply.

    Returns:
        Response: Response object with status code, informational messages, and content.
    """
    try:

        body = json.loads(payload.json())

        es.index(index="annotations", body=body, id=indicator_id)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{indicator_id}"},
            content=f"Created annotation with id = {indicator_id}",
        )
    except:

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not create annotation with id = {indicator_id}",
        )


@router.patch("/indicators/{indicator_id}/annotations")
def patch_annotation(payload: MetadataSchema.MetaModel, indicator_id: str):
    """Patch annotation for a dataset to Elasticsearch.

    Args:
        payload (MetadataSchema.MetaModel): Payload needs to be a partially formed json object valid for the pydantic schema MettaDataSchema.MetaModel.
        indicator_id (str): The UUID of the dataset for which the annotations apply.

    Returns:
        Response: Response object with status code, informational messages, and content.
    """
    try:

        body = json.loads(payload.json(exclude_unset=True))

        es.update(index="annotations", body={"doc": body}, id=indicator_id)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{indicator_id}"},
            content=f"Updated annotation with id = {indicator_id}",
        )
    except:

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not update annotation with id = {indicator_id}",
        )


@router.post("/indicators/{indicator_id}/upload")
def upload_file(
    indicator_id: str,
    file: UploadFile = File(...),
    filename: Optional[str] = None,
    append: Optional[bool] = False,
):
    original_filename = file.filename
    _, ext = os.path.splitext(original_filename)
    dir_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, indicator_id)
    if filename is None:
        if append:
            filenum = len(
                [
                    f
                    for f in list_files(dir_path)
                    if f.startswith("raw_data") and f.endswith(ext)
                ]
            )
            filename = f"raw_data_{filenum}{ext}"
        else:
            filename = f"raw_data{ext}"

    # Upload file
    dest_path = os.path.join(settings.DATASET_STORAGE_BASE_URL, indicator_id, filename)
    put_rawfile(path=dest_path, fileobj=file.file)

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={
            "location": f"/api/indicators/{indicator_id}",
            "content-type": "application/json",
        },
        content=json.dumps({"id": indicator_id, "filename": filename}),
    )


@router.get("/indicators/{indicator_id}/verbose")
def get_all_indicator_info(indicator_id: str):
    indicator = get_indicators(indicator_id)
    annotations = get_annotations(indicator_id)

    verbose_return_object = {"indicators": indicator, "annotations": annotations}

    return verbose_return_object


@router.post(
    "/indicators/validate_date",
    response_model=IndicatorSchema.DateValidationResponseSchema,
)
def validate_date(payload: IndicatorSchema.DateValidationRequestSchema):
    valid = True
    try:
        for value in payload.values:
            datetime.strptime(value, payload.format)
    except ValueError:
        valid = False

    return {
        "format": payload.format,
        "valid": valid,
    }


@router.post("/indicators/{indicator_id}/preview/{preview_type}")
async def create_preview(
    indicator_id: str, preview_type: IndicatorSchema.PreviewType, filename: str = None
):
    """Get preview for a dataset.

    Args:
        indicator_id (str): The UUID of the dataset to return a preview of.

    Returns:
        JSON: Returns a json object containing the preview for the dataset.
    """
    try:
        # TODO - Get all potential string files concatenated together using list file utility
        if preview_type == IndicatorSchema.PreviewType.processed:
            rawfile_path = os.path.join(
                settings.DATASET_STORAGE_BASE_URL,
                indicator_id,
                f"{indicator_id}.parquet.gzip",
            )
            file = get_rawfile(rawfile_path)
            df = pd.read_parquet(file)
            try:
                strparquet_path = os.path.join(
                    settings.DATASET_STORAGE_BASE_URL,
                    indicator_id,
                    f"{indicator_id}_str.parquet.gzip",
                )
                file = get_rawfile(strparquet_path)
                df_str = pd.read_parquet(file)
                df = pd.concat([df, df_str])
            except FileNotFoundError:
                pass

        else:
            rawfile_path = os.path.join(
                settings.DATASET_STORAGE_BASE_URL, indicator_id, "raw_data.csv"
            )
            file = get_rawfile(rawfile_path)
            df = pd.read_csv(file, delimiter=",")

        # preview = df.head(100).to_json(orient="records")
        obj = json.loads(df.head(100).to_json(orient="index"))
        indexed_rows = [{"__id": key, **value} for key, value in obj.items()]

        return indexed_rows
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"Queue could not be deleted.",
        )
