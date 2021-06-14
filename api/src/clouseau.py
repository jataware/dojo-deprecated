import asyncio
import logging
from logging import Logger
from operator import attrgetter
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.settings import settings
from src.utils import try_parse_int

logger: Logger = logging.getLogger(__name__)
router = APIRouter()

EXPIRE_TTL = 86400 * 2  # seconds


class AsyncRedisPool:
    def __init__(self) -> None:
        self._pool: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()

    async def __call__(self) -> aioredis.Redis:
        if self._pool is not None:
            return self._pool

        async with self._lock:
            if self._pool is not None:
                return self._pool
            logger.debug("Creating Redis Pool")
            host = settings.REDIS_HOST
            port = settings.REDIS_PORT
            pool = await aioredis.create_pool((host, port), encoding="utf-8")
            self._pool = aioredis.Redis(pool)
        return self._pool


redis_pool: aioredis.Redis = AsyncRedisPool()


class ProvisionItem(BaseModel):
    idx: Optional[int]
    cmd: List[str]


class HistoryItem(BaseModel):
    idx: Optional[int]
    command: str
    cwd: str


class EditItem(BaseModel):
    idx: Optional[int]
    file: str
    text: str


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    launched: str
    docker_host: str
    run_command: Optional[str]
    run_cwd: Optional[str]
    provisions: List[List[str]]
    history: List[HistoryItem]
    edits: List[EditItem]


@router.get("/ping")
async def ping_redis(redis: aioredis.Redis = Depends(redis_pool)) -> str:
    logger.debug("ping")
    return str(await redis.ping())


async def gather_non_nil(xs: List[Awaitable[Any]]) -> List[Any]:
    """
    Run coroutines concurrently only return non-nil results
    """
    res: List[Any] = []
    for co in asyncio.as_completed(xs):
        r = await co
        if r:
            res.append(r)
    return res


async def gather_list(redis: aioredis.Redis, prefix: str, fetcher: Callable[[str, int], Awaitable[Any]]) -> List[Any]:
    resp = await redis.get(f"{prefix}:idx")
    if resp is None:
        return []
    count = try_parse_int(resp)
    return await gather_non_nil([fetcher(prefix, i) for i in range(count)])


@router.get("/container/{cid}/history")
async def container_history(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> List[HistoryItem]:
    key = f"closeau:container:{cid}"
    history_prefix = f"{key}:history"

    async def fetcher(prefix: str, i: int) -> Optional[HistoryItem]:
        hist = await redis.hmget(f"{prefix}:{i}", "command", "cwd")
        if hist[0]:
            command, cwd = hist
            return HistoryItem(idx=i, command=command, cwd=cwd)
        return None

    res = await gather_list(redis, history_prefix, fetcher)
    return sorted(res, key=attrgetter("idx"))


@router.delete("/container/{cid}/{prefix}/{idx}")
async def delete_list_item(cid: str, prefix: str, idx: str, redis: aioredis.Redis = Depends(redis_pool)) -> str:
    key = f"closeau:container:{cid}"
    item_key = f"{key}:{prefix}:{idx}"
    await redis.delete(item_key)
    return "ok"


@router.get("/container/{cid}/edits")
async def container_edits(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> List[EditItem]:
    key = f"closeau:container:{cid}"
    edits_prefix = f"{key}:edits"

    async def fetcher(prefix: str, i: int) -> Optional[EditItem]:
        edit = await redis.hmget(f"{prefix}:{i}", "file", "text")
        if edit:
            f, t = edit
            return EditItem(idx=i, file=f, text=t)
        return None

    res = await gather_list(redis, edits_prefix, fetcher)
    return sorted(res, key=attrgetter("idx"))


@router.get("/container/{cid}/provisions")
async def container_provisions(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> List[List[str]]:
    key = f"closeau:container:{cid}"
    provisions_prefix = f"{key}:provisions"

    async def fetcher(prefix: str, i: int) -> Optional[ProvisionItem]:
        provision = await redis.lrange(f"{provisions_prefix}:{i}", 0, -1)
        if provision:
            return ProvisionItem(idx=i, cmd=provision)
        return None

    res = await gather_list(redis, provisions_prefix, fetcher)
    return [p.cmd for p in sorted(res, key=attrgetter("idx"))]


@router.get("/container/{cid}")
async def container_info(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> ContainerInfo:
    """
    Rebuild an object from redis
    """
    key = f"closeau:container:{cid}"
    fields = [
        "id",
        "name",
        "image",
        "launched",
        "docker_host",
        "run_command",
        "run_cwd",
    ]
    # meta
    cid, name, image, launched, docker_host, run_command, run_cwd = await redis.hmget(key, *fields)
    edits = await container_edits(cid, redis)
    provisions = await container_provisions(cid, redis)
    history = await container_history(cid, redis)
    return ContainerInfo(
        id=cid,
        name=name,
        image=image,
        launched=launched,
        docker_host=docker_host,
        run_command=run_command,
        run_cwd=run_cwd,
        edits=edits,
        provisions=provisions,
        history=history,
    )


@router.get("/container/{cid}/runcommand")
async def container_runcommand(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> Dict[str, str]:
    key = f"closeau:container:{cid}"
    fields = ["run_command", "run_cwd"]

    run_command, run_cwd = await redis.hmget(key, *fields)
    if not run_command:
        return {}
    return {"command": run_command, "cwd": run_cwd}


@router.delete("/container/{cid}")
async def expire_container_info(cid: str, redis: aioredis.Redis = Depends(redis_pool)) -> int:
    """
    Expire all keys related to an ID
    """
    key = f"closeau:container:{cid}"
    cur = 0
    count = 0
    while res := await redis.scan(cur, f"{key}*", 100):
        cursor, keys = res
        await asyncio.gather(*[redis.expire(k, EXPIRE_TTL) for k in keys])
        cur = try_parse_int(cursor)
        count += len(keys)
        if cur == 0:
            break

    return count
