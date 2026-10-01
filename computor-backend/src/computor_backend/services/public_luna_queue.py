"""Atomic, temporary admission for the outbound public Luna worker.

Only request identifiers are indexed. The bounded prompt payload lives in a
15-minute Redis value; the inference host does not persist it. Redis failures
must propagate so callers fail closed.
"""

import json
import time
from uuid import uuid4

PREFIX = "public_luna:v1"
JOB_TTL = 900
RESULT_TTL = 86400

_ADMIT = r"""
local p = ARGV[1]
local user = ARGV[2]
local id = ARGV[3]
local now = tonumber(ARGV[4])
local body = ARGV[5]
local pending = p .. ':pending'
local active = p .. ':active'
local lock = p .. ':user:' .. user
local hour = p .. ':hour:' .. user
local day = p .. ':day:' .. user
redis.call('ZREMRANGEBYSCORE', pending, '-inf', now - 900)
if redis.call('EXISTS', lock) == 1 then return 'pending' end
if redis.call('ZCARD', pending) >= 20 then return 'full' end
redis.call('ZREMRANGEBYSCORE', hour, '-inf', now - 3600)
redis.call('ZREMRANGEBYSCORE', day, '-inf', now - 86400)
if redis.call('ZCARD', hour) >= 10 or redis.call('ZCARD', day) >= 30 then return 'quota' end
redis.call('SET', lock, id, 'EX', 900)
redis.call('SET', p .. ':job:' .. id, body, 'EX', 900)
redis.call('ZADD', pending, now, id)
redis.call('ZADD', hour, now, id)
redis.call('ZADD', day, now, id)
redis.call('EXPIRE', pending, 900)
redis.call('EXPIRE', hour, 3600)
redis.call('EXPIRE', day, 86400)
return 'accepted'
"""

_CLAIM = r"""
local p = ARGV[1]
local now = tonumber(ARGV[2])
local active = p .. ':active'
local pending = p .. ':pending'
local expired = redis.call('ZRANGEBYSCORE', active, '-inf', now)
for _, id in ipairs(expired) do
  redis.call('ZREM', active, id)
  if redis.call('EXISTS', p .. ':job:' .. id) == 1 then
    redis.call('ZADD', pending, now, id)
  end
end
if redis.call('ZCARD', active) >= 4 then return nil end
for i = 1, 20 do
  local ids = redis.call('ZRANGE', pending, 0, 0)
  if #ids == 0 then return nil end
  local id = ids[1]
  redis.call('ZREM', pending, id)
  local body = redis.call('GET', p .. ':job:' .. id)
  if body then
    local lease = tostring(redis.call('INCR', p .. ':lease'))
    redis.call('HSET', p .. ':claim:' .. id, 'lease', lease)
    redis.call('EXPIRE', p .. ':claim:' .. id, 900)
    redis.call('ZADD', active, now + 600, id)
    redis.call('EXPIRE', active, 900)
    return {id, lease, body}
  end
end
return nil
"""

_FINISH = r"""
local p = ARGV[1]
local id = ARGV[2]
local lease = ARGV[3]
local result = ARGV[4]
local now = tonumber(ARGV[5])
local job = redis.call('GET', p .. ':job:' .. id)
if not job then return 'expired' end
if redis.call('HGET', p .. ':claim:' .. id, 'lease') ~= lease then return 'stale' end
local expires = redis.call('ZSCORE', p .. ':active', id)
if not expires or tonumber(expires) <= now then return 'stale' end
local request = cjson.decode(job)
local response = cjson.decode(result)
response.user_id = request.user_id
redis.call('SET', p .. ':result:' .. id, cjson.encode(response), 'EX', 86400)
redis.call('DEL', p .. ':job:' .. id, p .. ':claim:' .. id)
redis.call('ZREM', p .. ':active', id)
redis.call('DEL', p .. ':user:' .. request.user_id)
return 'finished'
"""


async def admit(redis, user_id: str, payload: dict) -> tuple[str, str]:
    job_id = str(uuid4())
    body = json.dumps({"user_id": user_id, **payload}, separators=(",", ":"))
    outcome = await redis.eval(
        _ADMIT, 0, PREFIX, user_id, job_id, int(time.time()), body
    )
    return outcome, job_id


async def claim(redis) -> tuple[str, str, dict] | None:
    result = await redis.eval(_CLAIM, 0, PREFIX, int(time.time()))
    if not result:
        return None
    job_id, lease, body = result
    return job_id, lease, json.loads(body)


async def finish(redis, job_id: str, lease: str, result: dict) -> str:
    return await redis.eval(
        _FINISH,
        0,
        PREFIX,
        job_id,
        lease,
        json.dumps(result, separators=(",", ":")),
        int(time.time()),
    )


async def status(redis, user_id: str, job_id: str) -> dict | None:
    result = await redis.get(f"{PREFIX}:result:{job_id}")
    if result:
        data = json.loads(result)
        return data if data.get("user_id") == user_id else None
    body = await redis.get(f"{PREFIX}:job:{job_id}")
    if not body or json.loads(body).get("user_id") != user_id:
        return None
    state = (
        "running"
        if await redis.zscore(f"{PREFIX}:active", job_id) is not None
        else "queued"
    )
    return {"state": state}
