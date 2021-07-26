import requests
import json
import os
from fastapi.logger import logger


def notify_causemos(data, type="indicator"):
    """
    A function to notify Causemos that a new indicator or model has been created.

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
        endpoint - "datacubes"

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