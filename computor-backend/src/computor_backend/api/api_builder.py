from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from computor_backend.business_logic.crud import (
    archive_entity as archive_db,
    create_entity as create_db,
    filter_entities as filter_db,
    get_entity_by_id as get_id_db,
    list_entities as list_db,
    update_entity as update_db,
    delete_entity as delete_db
)
from typing import Annotated, Optional
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db
from computor_backend.permissions.principal import Principal
from computor_types.base import EntityInterface
from computor_backend.redis_cache import get_redis_client, get_cache
from computor_backend.cache import Cache
from aiocache import BaseCache
from fastapi import FastAPI, BackgroundTasks
from fastapi import Response

class CrudRouter:

    id_type = "id"
    
    path: str
    dto: EntityInterface

    def __init__(self, dto, endpoint: Optional[str] = None):
        self.dto = dto
        if endpoint == None:
            self.path = self.dto.endpoint
        else:
            self.path = endpoint
        
        self.router = APIRouter()

        self.on_created = []
        self.on_updated = []
        self.on_deleted = []
        self.on_archived = []

    def create(self):
        async def route(
                background_tasks: BackgroundTasks,
                permissions: Annotated[Principal, Depends(get_current_principal)],
                entity: self.dto.create,
                cache: Annotated[BaseCache, Depends(get_redis_client)],
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            entity_created = await create_db(permissions, db, entity, self.dto.model, self.dto.get, self.dto.post_create)

            # Clear related cache entries (old async Redis cache)
            await self._clear_entity_cache(cache, self.dto.model.__tablename__)

            # Invalidate user views (new sync Cache system)
            self._invalidate_user_views_for_entity(entity_created, db)

            for task in self.on_created:
                background_tasks.add_task(task, entity_created, db, permissions)

            return entity_created
        return route
    
    def get(self):
        async def route(
                permissions: Annotated[Principal, Depends(get_current_principal)], 
                id: UUID | str, cache: Annotated[BaseCache, Depends(get_redis_client)], 
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            # Check cache first
            # cache_key = f"{self.dto.model.__tablename__}:get:{permissions.user_id}:{id}"
            # cached_result = await cache.get(cache_key)
            
            # if cached_result:
            #     return self.dto.get.model_validate_json(cached_result)
            
            result = await get_id_db(permissions, db, id, self.dto)
            
            # # Cache the result
            # await cache.set(cache_key, result.model_dump_json(), ttl=self.dto.cache_ttl)
            
            return result
        return route

    def list(self):
        async def route(
                permissions: Annotated[Principal, Depends(get_current_principal)], 
                cache: Annotated[BaseCache, Depends(get_redis_client)], 
                response: Response, 
                params: Annotated[self.dto.query , Depends()],
                db: Session = Depends(get_db)
        ) -> list[self.dto.list]:
            # Generate cache key based on params and user permissions
            # import hashlib
            # params_hash = hashlib.sha256(params.model_dump_json(exclude_none=True).encode()).hexdigest()
            # cache_key = f"{self.dto.model.__tablename__}:list:{permissions.user_id}:{params_hash}"
            
            # cached_result = await cache.get(cache_key)
            # if cached_result:
            #     cached_data = cached_result
            #     response.headers["X-Total-Count"] = str(cached_data.get("total", 0))
            #     return [self.dto.list.model_validate(item) for item in cached_data.get("items", [])]
            
            list_result, total = await list_db(permissions, db, params, self.dto)
            response.headers["X-Total-Count"] = str(total)
            
            # Cache the result
            # cache_data = {
            #     "items": [item.model_dump(mode='json') for item in list_result],
            #     "total": total
            # }
            # await cache.set(cache_key, cache_data, ttl=self.dto.cache_ttl)
            
            return list_result
        return route
    
    def update(self):
        async def route(
                background_tasks: BackgroundTasks,
                permissions: Annotated[Principal, Depends(get_current_principal)],
                id: UUID | str,
                entity: self.dto.update,
                cache: Annotated[BaseCache, Depends(get_redis_client)],
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            entity_updated = await update_db(permissions, db, id, entity, self.dto.model, self.dto.get, self.dto.post_update)

            # Clear related cache entries (old async Redis cache)
            await self._clear_entity_cache(cache, self.dto.model.__tablename__)

            # Invalidate user views (new sync Cache system)
            self._invalidate_user_views_for_entity(entity_updated, db)

            for task in self.on_updated:
                background_tasks.add_task(task, entity_updated, db, permissions)

            return entity_updated
        return route

    def delete(self):
        async def route(
                background_tasks: BackgroundTasks,
                permissions: Annotated[Principal, Depends(get_current_principal)],
                id: UUID | str,
                cache: Annotated[BaseCache, Depends(get_redis_client)],
                db: Session = Depends(get_db)
        ):

            entity_deleted = None
            if len(self.on_deleted) > 0:
                entity_deleted = await get_id_db(permissions, db, id, self.dto)

            # If we need to invalidate views, get entity first
            if entity_deleted is None:
                entity_deleted = await get_id_db(permissions, db, id, self.dto)

            # Clear related cache entries (old async Redis cache)
            await self._clear_entity_cache(cache, self.dto.model.__tablename__)

            # Invalidate user views (new sync Cache system)
            self._invalidate_user_views_for_entity(entity_deleted, db)

            # Run on_deleted tasks (not on_created)
            for task in self.on_deleted:
                if entity_deleted:
                    background_tasks.add_task(task, entity_deleted, db, permissions)

            return await delete_db(permissions, db, id, self.dto.model)

        return route
    
    def archive(self):  
        if hasattr(self.dto.model, "archived_at"):   
            async def route(
                    background_tasks: BackgroundTasks, 
                    permissions: Annotated[Principal, Depends(get_current_principal)], 
                    id: UUID | str, db: Session = Depends(get_db)
            ):

                if len(self.on_archived) > 0:

                    entity_archived = await get_id_db(permissions, db, id, self.dto)

                    for task in self.on_archived:
                        background_tasks.add_task(task, entity_archived, db, permissions)

                return archive_db(permissions, db, id, self.dto.model)
            return route
        else:
            return None

    def filter(self):
        async def route(
                permissions: Annotated[Principal, Depends(get_current_principal)], 
                filters: Optional[dict] = None, 
                params: self.dto.query = Depends(), 
                db: Session = Depends(get_db)
        ) -> list[self.dto.list]:
            return await filter_db(permissions, db, self.dto.model, params, self.dto.search, filters)
        return route

    def register_routes(self, app: FastAPI):
        
        scope_name = self.path.replace("/","").replace("_"," ")

        self.router.add_api_route("", self.create(), methods=["POST"], 
                    status_code=status.HTTP_201_CREATED, name=f"{self.create.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        self.router.add_api_route(f"/{{{CrudRouter.id_type}}}", self.get(), methods=["GET"], 
                    status_code=status.HTTP_200_OK, name=f"{self.get.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        self.router.add_api_route("", self.list(), methods=["GET"], 
                    status_code=status.HTTP_200_OK, name=f"{self.list.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        self.router.add_api_route(f"/{{{CrudRouter.id_type}}}", self.update(), methods=["PATCH"], 
                    status_code=status.HTTP_200_OK, name=f"{self.update.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        self.router.add_api_route(f"/{{{CrudRouter.id_type}}}", self.delete(), methods=["DELETE"], 
                    status_code=status.HTTP_204_NO_CONTENT, name=f"{self.delete.__name__} {scope_name.capitalize()}", dependencies=[Depends(get_current_principal)])
        
        archive_fun = self.archive()
        
        if archive_fun != None:
            self.router.add_api_route(f"/{{{CrudRouter.id_type}}}/archive", archive_fun, methods=["PATCH"], 
                status_code=status.HTTP_204_NO_CONTENT, name=f"{archive_fun.__name__} {scope_name.capitalize()}", dependencies=[Depends(get_current_principal)])
        
        # self.router.add_api_route("-filtered", self.filter(), methods=["GET"],
        #         status_code=status.HTTP_200_OK, name=f"{self.filter.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])

        app.include_router(
            self.router,
            prefix=f"/{self.path}",
            tags=[scope_name]
        )
        
        return self
    
    async def _clear_entity_cache(self, cache: BaseCache, table_name: str):
        """Clear all cache entries for a given entity type"""
        try:
            # The cache parameter is actually the async Redis client from get_redis_client()
            # Check if it's a direct Redis client
            if hasattr(cache, 'keys') and callable(cache.keys):
                pattern = f"{table_name}:*"
                cache_keys = await cache.keys(pattern)
                if cache_keys:
                    await cache.delete(*cache_keys)
            # Otherwise check if it has a wrapped client (for aiocache BaseCache)
            elif hasattr(cache, '_client') or hasattr(cache, 'client'):
                redis_client = getattr(cache, '_client', None) or getattr(cache, 'client', None)
                if redis_client and hasattr(redis_client, 'keys') and callable(redis_client.keys):
                    pattern = f"{table_name}:*"
                    cache_keys = await redis_client.keys(pattern)
                    if cache_keys:
                        await redis_client.delete(*cache_keys)
                else:
                    print(f"Warning: Using fallback cache clear method for {table_name}")
            else:
                print(f"Warning: Using fallback cache clear method for {table_name}")

        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache clear error for {table_name}: {e}")

    def _invalidate_user_views_for_entity(self, entity, db: Session):
        """
        Invalidate user views when entities are created/updated/deleted.

        This ensures that lecturer/tutor/student views are invalidated when
        related entities change (e.g., course content creation invalidates
        lecturer course content lists).
        """
        try:
            # Get the sync Cache instance
            cache = get_cache()

            # Determine entity type and extract relevant IDs
            table_name = self.dto.model.__tablename__

            # Handle CourseContent specifically
            if table_name == "course_content" and hasattr(entity, 'course_id'):
                # Invalidate all lecturer views for this course
                # This uses the 'lecturer_view:course_id' tag set in LecturerViewRepository
                cache.invalidate_user_views(
                    entity_type="lecturer_view",
                    entity_id=str(entity.course_id)
                )
                # Also invalidate by course_id tag for broader invalidation
                cache.invalidate_user_views(
                    entity_type="course_id",
                    entity_id=str(entity.course_id)
                )

            # Handle other entities with course_id
            elif hasattr(entity, 'course_id'):
                cache.invalidate_user_views(
                    entity_type="course_id",
                    entity_id=str(entity.course_id)
                )

            # Handle Course entities
            elif table_name == "course" and hasattr(entity, 'id'):
                cache.invalidate_user_views(
                    entity_type="course_id",
                    entity_id=str(entity.id)
                )
                cache.invalidate_user_views(
                    entity_type="lecturer_view",
                    entity_id=str(entity.id)
                )

        except Exception as e:
            # Log error but don't fail the operation
            print(f"User view cache invalidation error for {table_name}: {e}")

class LookUpRouter:

    id_type = "id"
    
    path: str
    dto: EntityInterface

    def __init__(self, dto, endpoint: Optional[str] = None):
        self.dto = dto
        if endpoint == None:
            self.path = self.dto.endpoint
        else:
            self.path = endpoint
        
        self.router = APIRouter()
        
    def get(self):
        async def route(permissions: Annotated[Principal, Depends(get_current_principal)], id: str, db: Session = Depends(get_db)) -> self.dto.get:
            return await get_id_db(permissions, db, id, self.dto)
        return route

    
    def list(self):
        async def route(permissions: Annotated[Principal, Depends(get_current_principal)], response: Response, params: self.dto.query = Depends(), db: Session = Depends(get_db)) -> list[self.dto.list]:
            list_result, total = await list_db(permissions, db, params, self.dto)
            response.headers["X-Total-Count"] = str(total)
            return list_result
        return route
    
    def register_routes(self, app: FastAPI):
        
        scope_name = self.path.replace("/","").replace("_"," ")

        self.router.add_api_route(f"/{{{LookUpRouter.id_type}}}", self.get(), methods=["GET"], 
                    status_code=status.HTTP_200_OK, name=f"{self.get.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        self.router.add_api_route("", self.list(), methods=["GET"], 
                    status_code=status.HTTP_200_OK, name=f"{self.list.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])
        
        app.include_router(
            self.router,
            prefix=f"/{self.path}",
            tags=[scope_name]
        )
