import logging
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from computor_backend.business_logic.crud import (
    archive_entity as archive_db,
    unarchive_entity as unarchive_db,
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
from computor_backend.redis_cache import get_cache
from fastapi import FastAPI, BackgroundTasks
from fastapi import Response

logger = logging.getLogger(__name__)

class CrudRouter:

    id_type = "id"
    
    path: str
    dto: EntityInterface

    def __init__(self, dto, endpoint: Optional[str] = None):
        self.dto = dto
        if endpoint is None:
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
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            entity_created = await create_db(permissions, db, entity, self.dto.model, self.dto.get, self.dto.post_create)

            self._invalidate_caches_for(entity_created)

            for task in self.on_created:
                background_tasks.add_task(task, entity_created, permissions)

            return entity_created
        return route
    
    def get(self):
        async def route(
                permissions: Annotated[Principal, Depends(get_current_principal)],
                id: UUID | str,
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            return await get_id_db(permissions, db, id, self.dto)
        return route

    def list(self):
        async def route(
                permissions: Annotated[Principal, Depends(get_current_principal)],
                response: Response,
                params: Annotated[self.dto.query, Depends()],
                db: Session = Depends(get_db)
        ) -> list[self.dto.list]:
            list_result, total = await list_db(permissions, db, params, self.dto)
            response.headers["X-Total-Count"] = str(total)
            return list_result
        return route
    
    def update(self):
        async def route(
                background_tasks: BackgroundTasks,
                permissions: Annotated[Principal, Depends(get_current_principal)],
                id: UUID | str,
                entity: self.dto.update,
                db: Session = Depends(get_db)
        ) -> self.dto.get:
            entity_updated = await update_db(permissions, db, id, entity, self.dto.model, self.dto.get, self.dto.post_update, self.dto.custom_permissions)

            self._invalidate_caches_for(entity_updated)

            for task in self.on_updated:
                background_tasks.add_task(task, entity_updated, permissions)

            return entity_updated
        return route

    def delete(self):
        async def route(
                background_tasks: BackgroundTasks,
                permissions: Annotated[Principal, Depends(get_current_principal)],
                id: UUID | str,
                db: Session = Depends(get_db)
        ):
            # Fetch the row before deletion so post_delete callbacks and cache
            # invalidation can see its fields. Cheaper than racing the delete.
            entity_deleted = await get_id_db(permissions, db, id, self.dto)

            self._invalidate_caches_for(entity_deleted)

            for task in self.on_deleted:
                if entity_deleted:
                    background_tasks.add_task(task, entity_deleted, permissions)

            return await delete_db(permissions, db, id, self.dto.model)

        return route

    def archive(self):
        if hasattr(self.dto.model, "archived_at"):
            async def route(
                    background_tasks: BackgroundTasks,
                    permissions: Annotated[Principal, Depends(get_current_principal)],
                    id: UUID | str,
                    db: Session = Depends(get_db)
            ):
                entity_archived = await get_id_db(permissions, db, id, self.dto)

                for task in self.on_archived:
                    background_tasks.add_task(task, entity_archived, permissions)

                result = await archive_db(permissions, db, id, self.dto.model)
                self._invalidate_caches_for(entity_archived)
                return result
            return route
        else:
            return None

    def unarchive(self):
        if hasattr(self.dto.model, "archived_at"):
            async def route(
                    permissions: Annotated[Principal, Depends(get_current_principal)],
                    id: UUID | str,
                    db: Session = Depends(get_db)
            ):
                entity = await get_id_db(permissions, db, id, self.dto)
                result = await unarchive_db(permissions, db, id, self.dto.model)
                self._invalidate_caches_for(entity)
                return result
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

        if archive_fun is not None:
            self.router.add_api_route(f"/{{{CrudRouter.id_type}}}/archive", archive_fun, methods=["PATCH"],
                status_code=status.HTTP_204_NO_CONTENT, name=f"{archive_fun.__name__} {scope_name.capitalize()}", dependencies=[Depends(get_current_principal)])

        unarchive_fun = self.unarchive()

        if unarchive_fun is not None:
            self.router.add_api_route(f"/{{{CrudRouter.id_type}}}/unarchive", unarchive_fun, methods=["PATCH"],
                status_code=status.HTTP_204_NO_CONTENT, name=f"Unarchive {scope_name.capitalize()}", dependencies=[Depends(get_current_principal)])
        
        # self.router.add_api_route("-filtered", self.filter(), methods=["GET"],
        #         status_code=status.HTTP_200_OK, name=f"{self.filter.__name__} {scope_name.capitalize()}",dependencies=[Depends(get_current_principal)])

        app.include_router(
            self.router,
            prefix=f"/{self.path}",
            tags=[scope_name]
        )
        
        return self
    
    def _invalidate_caches_for(self, entity) -> None:
        """Invalidate user-view cache tags emitted by the entity's interface.

        Each entity interface declares which tags it carries via
        ``cache_invalidation_tags`` (see ``BackendEntityInterface``); the
        default implementation handles the standard scope FKs and
        per-entity overrides extend with role-aware view tags.
        Failures are logged, never raised — a stale cache is preferable
        to a 500 on the write path.
        """
        if entity is None:
            return
        try:
            cache = get_cache()
            for tag in self.dto.cache_invalidation_tags(entity):
                cache.invalidate_user_views(
                    user_id=tag.user_id,
                    entity_type=tag.entity_type,
                    entity_id=tag.entity_id,
                )
        except Exception:
            logger.exception(
                "User view cache invalidation failed for %s",
                self.dto.model.__tablename__,
            )

class LookUpRouter:

    id_type = "id"
    
    path: str
    dto: EntityInterface

    def __init__(self, dto, endpoint: Optional[str] = None):
        self.dto = dto
        if endpoint is None:
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
