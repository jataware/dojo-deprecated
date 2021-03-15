import itertools
import logging
import os
import pathlib
import sys
import time
from datetime import datetime

import uvicorn
from fastapi import FastAPI

from api import cubes, experiments, jobs, models

logger = logging.getLogger(__name__)

api = FastAPI(docs_url="/")
api.include_router(models.router, tags=['Models'])
api.include_router(cubes.router, tags=['Cubes'])
api.include_router(jobs.router, tags=['Jobs'])
api.include_router(experiments.router, tags=['Experiments'])

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    if os.environ.get("UVICORN_RELOAD") is not None:
        uvicorn.run(f"{__name__}:api", host="0.0.0.0", port=8000, reload=True)
    else:
        uvicorn.run(api, host="0.0.0.0", port=8000)
