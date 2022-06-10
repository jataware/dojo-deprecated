import time
import json
import tempfile

from elasticsearch import Elasticsearch
from fastapi import APIRouter, HTTPException, Response, File, UploadFile, Form, status
from pydantic import BaseModel

from src.settings import settings
from validation import SpacetagSchema

import pandas as pd

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)


# For created_at times in epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


@router.get("/annotations/{annotation_uuid}", response_model=SpacetagSchema.SpaceModel)
def get_annotations(annotation_uuid: str) -> SpacetagSchema.SpaceModel:
    try:
        annotation = es.get(index="annotations", id=annotation_uuid)["_source"]
        return annotation
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return None


@router.post("/annotations/{annotation_uuid}")
def create_annotation(payload: SpacetagSchema.SpaceModel, annotation_uuid: str):

    try:

        body = payload.json()

        es.index(index="annotations", body=body, id=annotation_uuid)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{annotation_uuid}"},
            content=f"Updated annotation with id = {annotation_uuid}",
        )
    except:

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not update annotation with id = {annotation_uuid}",
        )


@router.put("/annotations/{annotation_uuid}")
def create_annotation(payload: SpacetagSchema.SpaceModel, annotation_uuid: str):

    try:

        body = payload.json()

        es.index(index="annotations", body=body, id=annotation_uuid)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{annotation_uuid}"},
            content=f"Created annotation with id = {annotation_uuid}",
        )
    except:

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not create annotation with id = {annotation_uuid}",
        )


@router.patch("/annotations/{annotation_uuid}")
def create_annotation(payload: SpacetagSchema.SpaceModel, annotation_uuid: str):

    try:

        body = payload.json()

        es.update(index="annotations", body=body, id=annotation_uuid)

        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={"location": f"/api/annotations/{annotation_uuid}"},
            content=f"Updated annotation with id = {annotation_uuid}",
        )
    except:

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Could not update annotation with id = {annotation_uuid}",
        )


@router.post("/annotations/preview/{lines}")
async def create_preview(number_of_lines: int, data: UploadFile = File(...)):

    try:
        print(data.filename)
        payload_wrapper = tempfile.TemporaryFile()
        payload_wrapper.write(await data.read())
        payload_wrapper.seek(0)

        df = pd.read_csv(payload_wrapper, delimiter=",")

        preview = df.head(number_of_lines).to_json(orient="records")

        return preview

    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={"msg": f"Error: {e}"},
            content=f"Queue could not be deleted.",
        )
