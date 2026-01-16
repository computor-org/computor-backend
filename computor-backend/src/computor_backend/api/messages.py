from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status, Query
from sqlalchemy.orm import Session

from computor_backend.business_logic.crud import (
    create_entity as create_db,
    delete_entity as delete_db,
    get_entity_by_id as get_id_db,
    list_entities as list_db,
    update_entity as update_db
)
from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_types.messages import MessageCreate, MessageGet, MessageList, MessageQuery, MessageUpdate
from computor_backend.interfaces.message import MessageInterface
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

# Import business logic
from computor_backend.business_logic.messages import (
    create_message_with_author,
    get_message_with_read_status,
    list_messages_with_read_status,
    list_messages_with_filters,
    mark_message_as_read,
    mark_message_as_unread,
)
from computor_backend.business_logic.message_operations import (
    soft_delete_message,
    update_message_with_audit,
    create_message_audit,
    get_message_audit_history,
)
from computor_backend.websocket.broadcast import ws_broadcast

messages_router = APIRouter()

@messages_router.post("", response_model=MessageGet, status_code=status.HTTP_201_CREATED)
async def create_message(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    """Create a new message with enforced author and defaults."""
    model_dump = create_message_with_author(payload, permissions, db)

    # Use create_db so permission handler validates
    class _Create(MessageCreate):
        author_id: str
    entity = _Create(**model_dump)
    message = await create_db(permissions, db, entity, MessageInterface.model, MessageInterface.get)

    # Create audit log entry
    from computor_backend.model.message import Message
    db_message = db.query(Message).filter(Message.id == message.id).first()
    if db_message:
        create_message_audit(db_message, permissions, db)

    # Broadcast to WebSocket subscribers (use DTO which has target fields)
    await ws_broadcast.message_created(message, message.model_dump(mode="json"))

    return message

@messages_router.get("/{id}", response_model=MessageGet)
async def get_message(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get a message with read status."""
    message = await get_id_db(permissions, db, id, MessageInterface)
    return get_message_with_read_status(id, message, permissions, db)

@messages_router.get("", response_model=list[MessageList])
async def list_messages(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: MessageQuery = Depends(),
    db: Session = Depends(get_db),
    # Explicit Query parameter for tags list - FastAPI doesn't parse List[str] from Pydantic Field
    tags: Optional[List[str]] = Query(
        None,
        description="Filter by tags in title (e.g., tags=ai::request&tags=priority::high)"
    ),
):
    """List messages with read status.

    Supports filtering by:
    - unread: True = unread only, False = read only, None = all
    - created_after/created_before: Datetime boundaries
    - tags: List of tags in format "scope::value" to filter by (in title)
    - tags_match_all: True = must match ALL tags, False = match ANY tag
    - tag_scope: Wildcard scope filter (e.g., "ai" matches any #ai::* tag)
    """
    # Merge the explicit tags parameter into params (FastAPI doesn't parse List from Pydantic Field)
    if tags is not None:
        params.tags = tags

    # Use custom list function that supports user-specific filtering
    items, total = await list_messages_with_filters(permissions, db, params)
    items = list_messages_with_read_status(items, permissions, db)
    response.headers["X-Total-Count"] = str(total)
    return items

@messages_router.patch("/{id}", response_model=MessageGet)
async def update_message(
    id: UUID | str,
    payload: MessageUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update a message with audit logging."""
    # First verify user has access via permissions
    await get_id_db(permissions, db, id, MessageInterface)

    # Update with audit
    message = update_message_with_audit(
        message_id=id,
        principal=permissions,
        db=db,
        new_title=payload.title,
        new_content=payload.content
    )

    # Convert to MessageGet
    message_get = get_message_with_read_status(id, MessageInterface.get.model_validate(message), permissions, db)

    # Broadcast to WebSocket subscribers (use DTO which has target fields)
    await ws_broadcast.message_updated(message_get, message_get.model_dump(mode="json"), str(id))

    return message_get

@messages_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Soft delete a message (preserves thread structure)."""
    # Verify user has access and get message for broadcast
    message = await get_id_db(permissions, db, id, MessageInterface)

    # Soft delete with audit
    soft_delete_message(
        message_id=id,
        principal=permissions,
        db=db,
        reason="user_request"
    )

    # Broadcast to WebSocket subscribers (use DTO which has target fields)
    await ws_broadcast.message_deleted(message, str(id))

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@messages_router.post("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_read(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Mark a message as read."""
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)
    mark_message_as_read(id, permissions, db, cache)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@messages_router.delete("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_unread(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    """Mark a message as unread."""
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)
    mark_message_as_unread(id, permissions, db, cache)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@messages_router.get("/{id}/audit")
async def get_message_audit(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get audit history for a message (author or admin only)."""
    # Verify user has access
    await get_id_db(permissions, db, id, MessageInterface)

    # Get audit history
    audit_logs = get_message_audit_history(
        message_id=id,
        principal=permissions,
        db=db
    )

    # Convert to dict for response
    return [
        {
            "id": str(log.id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "message_id": str(log.message_id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action.value,
            "old_title": log.old_title,
            "old_content": log.old_content,
            "new_title": log.new_title,
            "new_content": log.new_content,
        }
        for log in audit_logs
    ]
