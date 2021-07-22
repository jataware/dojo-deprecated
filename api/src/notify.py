import requests
import json
import os
from fastapi.logger import logger


def notify_causemos(data):
    """
    A function to notify Causemos that a new indicator has been created
    POST https://causemos.uncharted.software/api/maas/indicators/post-process
    // Request body: indicator metadata
    """
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    url = os.getenv("CAUSEMOS_IND_URL")
    causemos_user = os.getenv("CAUSEMOS_USER")
    causemos_pwd = os.getenv("CAUSEMOS_PWD")

    try:
        # Notify Uncharted
        if os.getenv("CAUSEMOS_DEBUG") == "true":
            print("Debug mode: no need to notify Uncharted")
            return
        else:
            print("Notifying Uncharted...")
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=data,
                auth=(causemos_user, causemos_pwd),
            )
            print(f"Response from Uncharted: {response.text}")
            return

    except Exception as e:
        logger.error(f"Encountered problems communicating with Causemos: {e}")
        logger.exception(e)
