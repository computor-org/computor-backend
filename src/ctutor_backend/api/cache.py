import json
import hashlib
from functools import wraps
from ctutor_backend.interface.base import EntityInterface
from ctutor_backend.redis_cache import get_redis_client

def cache_route(interface: EntityInterface, ttl: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            permissions = kwargs["permissions"]

            user_id = permissions.user_id

            if user_id == None:
                response = await func(*args, **kwargs)

            params = kwargs.get('params')
            id = kwargs.get('id')
            namespace = interface.model.__tablename__

            if id != None:
                cache_key = f"{user_id}:{id}"
            else:
                if params != None:
                    hashed_params = hashlib.sha256(params.model_dump_json(exclude_none=True).encode()).hexdigest()
                    cache_key = f"{namespace}:{user_id}:{hashed_params}"
                else:
                    cache_key = f"{namespace}:{user_id}"

            cache = await get_redis_client()

            cached_value = await cache.get(cache_key)

            if cached_value:
                if isinstance(cached_value,list):
                    return [interface.list.model_validate(json.loads(entity),from_attributes=True) for entity in cached_value]
                else:
                    return interface.get.model_validate(json.loads(cached_value),from_attributes=True)

            response = await func(*args, **kwargs)

            try:
                if isinstance(response,list):
                    await cache.set(cache_key, [entity.model_dump_json() for entity in response], ttl=ttl)
                else:
                    await cache.set(cache_key, response.model_dump_json(), ttl=ttl)
            except Exception as e:
                raise e

            return response
        return wrapper
    return decorator