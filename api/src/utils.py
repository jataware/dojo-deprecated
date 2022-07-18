import io

import os
import hashlib

import boto3

from validation import ModelSchema
import time
from elasticsearch import Elasticsearch

from src.settings import settings
es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)

def try_parse_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except ValueError:
        return default

def delete_matching_records_from_model(model_id, record_key, record_test):
    """
    This function provides an easy way to remove information from within a specific key of a model.

    - model_id: the id of the model that we should be removing information from
    - record_key: the key of the model that we should look in to remove data (ie "parameters", "outputs")
    - record_test: a function that will run on each of the records within the record_key to see whether
        they should be deleted. record_test() should return True if this record is to be deleted
    """

    from src.models import get_model, modify_model  # import at runtime to avoid circular import error
    record_count = 0

    model = get_model(model_id)
    records = model.get(record_key, [])
    records_to_delete = []
    for record in records:
        if record_test(record):
            records_to_delete.append(record)

    for record in records_to_delete:
        record_count += 1
        records.remove(record)

    update = { record_key: records }
    modify_model(model_id, ModelSchema.ModelMetadataPatchSchema(**update))

    return record_count

def run_model_with_defaults(model_id):
    """
    This function takes in a model and submits a default run to test that model's functionality
    """

    from src.models import get_model 
    from src.runs import create_run, current_milli_time
    from validation.RunSchema import ModelRunSchema

    model = get_model(model_id)

    params = []
    for param in model.get("parameters",[]):
        param_obj = {}
        param_obj['name'] = param['name']
        param_obj['value'] = param['default']
        params.append(param_obj)

    model_name_clean = ''.join(filter(str.isalnum, model['name']))
    run_id = f"{model_name_clean}-{current_milli_time()}"

    run = ModelRunSchema(id=run_id,
                         model_id=model_id,
                         model_name=model["name"],
                         parameters=params,
                         data_paths=[],
                         tags=[],
                         is_default_run=True,
                         attributes={},
                         created_at = current_milli_time())

    create_run(run)

    # Store model ID to `tests` index with `status` set to `running`
    body = {"status": "running", "model_name": model["name"], "created_at": run.created_at, "run_id": run.id}
    es.index(index="tests", body=body, id=model_id)

    return run_id    


# TODO: DELETE; THIS SHOULD NOT BE SET HERE!
os.environ["S3_BUCKET"] = "jataware-world-modelers"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
    # aws_session_token=os.environ["SESSION_TOKEN"]
)

def gen_s3_file(model_id, path, contents):
    if path.startswith("/"):
        path = path[1:]  # trim leading slash
    s3_key = f"dojo/shorthand_templates/{model_id}/{path}.txt"

    s3_client.upload_fileobj(
        io.BytesIO(contents.encode('utf-8')),
        Bucket=os.environ["S3_BUCKET"],
        Key=s3_key,
        ExtraArgs={'ACL':'public-read'},
    )

    return "https://{bucket}.s3.amazonaws.com/{key}".format(
        bucket=os.environ["S3_BUCKET"],
        key=s3_key
    )
