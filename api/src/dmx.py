
import logging
from pydantic import BaseModel, Field

from fastapi import APIRouter
from fastapi.logger import logger

from domainmodelexaminer import dmx



router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/dmx/examine")
def examine_model(url: str, return_comments: bool = True):
    
    logger.info(f'dmx examining {url} return_comments={return_comments}')
    return dmx.examine(url, return_comments = return_comments)

    #dmx_id = uuid.uuid4()
    #es.index(index="dmx", body=dmx_json, id=dmx_id)
    #return Response(
    #    status_code=status.HTTP_201_CREATED,
    #    headers={"location": f"/api/dmx/{dmx_id}"},
    #    content=f"Created dmx with id = {dmx_id}",)

#@router.get("/dmx")
#def search_dmx(query: str = None, size: int = 10, scroll_id: str = Query(None)):
#    return search_and_scroll(index="dmx", size=size, query=query, scroll_id=scroll_id)