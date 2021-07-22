
import logging
from logging import Logger
import json

from typing import List, Optional

import aioredis
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from src.redisapi import redis_pool


logger: Logger = logging.getLogger(__name__)
router = APIRouter()

BASE_IMAGES_KEY = "phantom:base_images"


class BaseImageItem(BaseModel):
    sort_order: Optional[int]
    display_name: str
    image: str

    def hash(self):
        return f"{self.image}_{self.display_name}"


@router.get("/ping")
async def ping_redis(redis: aioredis.Redis = Depends(redis_pool)) -> str:
    logger.debug("ping")
    return Response(content=str(await redis.ping()), media_type="plain/text")


@router.get("/base_images")
async def get_base_images(redis: aioredis.Redis = Depends(redis_pool)) -> List[BaseImageItem]:
    res = await redis.hgetall(BASE_IMAGES_KEY)
    return sorted((json.loads(x) for x in res.values()), key=lambda x: x.get("sort_order", 100) or 100)


@router.post("/base_images")
async def add_base_image(item: BaseImageItem, redis: aioredis.Redis = Depends(redis_pool)) -> List[BaseImageItem]:
    await redis.hmset(BASE_IMAGES_KEY, item.hash(), json.dumps(item.dict()))
    return await get_base_images(redis)


@router.delete("/base_images")
async def delete_base_image(item: BaseImageItem, redis: aioredis.Redis = Depends(redis_pool)) -> List[BaseImageItem]:
    await redis.hdel(BASE_IMAGES_KEY, item.hash())
    return await get_base_images(redis)

