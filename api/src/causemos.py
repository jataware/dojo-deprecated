import json
import requests
import os
from copy import deepcopy
from fastapi.logger import logger

from validation import ModelSchema
from src.dojo import get_parameters
from src.ontologies import get_ontologies


def convert_to_causemos_format(model):
    """
    Transforms model from internal representation to the representation
    accepted by Cauesmos.
    """
    def to_parameter(annot):
        """
        Transform Dojo annotation into a Causemos parameter.
        """
        return {
            "name": annot["name"],
            "display_name": annot["name"],
            "description": annot["description"],
            "type": annot["type"],
            "unit": annot["unit"],
            "unit_description": annot["unit_description"],
            "ontologies": None,
            "is_drilldown": None,
            "additional_options": None,
            "data_type": annot["data_type"],
            "default": annot["default_value"],
            "choices": annot["options"] if annot["predefined"] else None,
            # NOTE: Do we want to store these as strings internally?
            "min": float(annot["min"]) if annot["min"] != "" else None,
            "max": float(annot["max"]) if annot["max"] != "" else None
        }

    causemos_model = deepcopy(model)
    causemos_model["parameters"] = [
        to_parameter(parameters["annotation"])
        for parameters in get_parameters(model['id'])
    ]
    causemos_model = get_ontologies(causemos_model, type='model')
    payload = ModelSchema.CausemosModelMetadataSchema(
        **causemos_model
    )
    return json.loads(payload.json())


def deprecate_dataset(dataset_id):
    """
    A function to deprecate a dataset within Causemos

    PUT https://causemos.uncharted.software/api/maas/datacubes/exampleID/deprecate

    """
    url = f'{os.getenv("CAUSEMOS_IND_URL")}/datacubes/{dataset_id}/deprecate'
    causemos_user = os.getenv("CAUSEMOS_USER")
    causemos_pwd = os.getenv("CAUSEMOS_PWD")

    try:
        # Notify Uncharted
        if os.getenv("CAUSEMOS_DEBUG") == "true":
            logger.info("CauseMos debug mode: no need to notify Uncharted")
            return
        else:
            logger.info(f"Notifying Causemos to deprecate dataset")
            response = requests.put(
                url,
                auth=(causemos_user, causemos_pwd),
            )
            logger.info(f"Response from Uncharted: {response.text}")
            return

    except Exception as e:
        logger.error(f"Encountered problems communicating with Causemos: {e}")
        logger.exception(e)


def notify_causemos(data, type="indicator"):
    """
    A function to notify Causemos that a new indicator or model has been
    created.

    If type is "indicator":
        POST https://causemos.uncharted.software/api/maas/indicators/post-process
        // Request body: indicator metadata

    If type is "model":
        POST https://causemos.uncharted.software/api/maas/datacubes
        // Request body: model metadata
    """
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    if type == "indicator":
        endpoint = "indicators/post-process"
    elif type == "model":
        endpoint = "datacubes"
        data = convert_to_causemos_format(data)

    # Notify Causemos that a model was created
    logger.info("Notifying CauseMos of model registration")

    url = f'{os.getenv("CAUSEMOS_IND_URL")}/{endpoint}'
    causemos_user = os.getenv("CAUSEMOS_USER")
    causemos_pwd = os.getenv("CAUSEMOS_PWD")

    try:
        # Notify Uncharted
        if os.getenv("CAUSEMOS_DEBUG") == "true":
            logger.info("CauseMos debug mode: no need to notify Uncharted")
            return
        else:
            logger.info(f"Notifying CauseMos of {type} creation...")
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=data,
                auth=(causemos_user, causemos_pwd),
            )
            logger.info(f"Response from Uncharted: {response.text}")
            return

    except Exception as e:
        logger.error(f"Encountered problems communicating with Causemos: {e}")
        logger.exception(e)


def submit_run(model):
    """
    This function takes in a model and submits a default run for that model to CauseMos

    POST https://causemos.uncharted.software/api/maas/model-runs
    // The request body must at a minimum include
    {
    model_id,
    model_name,
    parameters,
    is_default_run = true
    }
    """

    logger.info("Submitting default run to CauseMos")

    headers = {"accept": "application/json", "Content-Type": "application/json"}
    endpoint = "model-runs"
    url = f'{os.getenv("CAUSEMOS_IND_URL")}/{endpoint}'
    causemos_user = os.getenv("CAUSEMOS_USER")
    causemos_pwd = os.getenv("CAUSEMOS_PWD")

    payload = {"model_id": model["id"],
               "model_name": model["name"],
               "is_default_run": True,
               "parameters": []}

    try:
        # Notify Uncharted
        if os.getenv("CAUSEMOS_DEBUG") == "true":
            logger.info("CauseMos debug mode: no need to submit default model run to Uncharted")
            return
        else:
            logger.info(f"Submitting default model run to CauseMos with payload: {payload}")
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                auth=(causemos_user, causemos_pwd),
            )
            logger.info(f"Response from Uncharted: {response.text}")
            return

    except Exception as e:
        logger.error(f"Encountered problems communicating with Causemos: {e}")
        logger.exception(e)
