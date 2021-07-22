import requests
import json
import os
from fastapi.logger import logger


def get_ontology(data, type="indicator"):
    """
    A function to submit either indicators or models to the UAZ
    ontology mapping service

    Params:
        - data: the indicator or model object
        - type: one of either [indicator, model]
    """
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    url = os.getenv("UAZ_URL")
    uaz_threshold = os.getenv("UAZ_THRESHOLD")
    uaz_hits = os.getenv("UAZ_HITS")
    params = f"?maxHits={uaz_hits}&threshold={uaz_threshold}&compositional=true"

    # Send to either /groundIndicator or /groundModel
    if type == "indicator":
        type_ = "groundIndicator"
    elif type == "model":
        type_ = "groundModel"

    # Build final URL to route to UAZ
    url_ = f"{url}/{type_}{params}"

    try:
        logger.debug(f"Sending data to {url}")
        response = requests.put(url_, json=data, headers=headers)
        logger.debug(f"response: {response}")
        logger.debug(f"response reason: {response.raw.reason}")

        # Ensure good response and not an empty response
        if response.status_code == 200:
            resp_str = response.content.decode("utf8")
            ontologies = json.loads(resp_str)

            # Capture UAZ ontology data
            ontology_dict = {}
            for ontology in ontologies["outputs"]:
                key = ontology["name"]
                ontology_dict[key] = ontology["ontologies"]

            return ontology_dict

        else:
            logger.debug(f"else response: {response}")
            return response

    except Exception as e:
        logger.error(f"Encountered problems communicating with UAZ service: {e}")
        logger.exception(e)
