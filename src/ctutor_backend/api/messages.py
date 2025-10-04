from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ctutor_backend.business_logic.crud import (
    create_entity as create_db,
    delete_entity as delete_db,
    get_entity_by_id as get_id_db,
    list_entities as list_db,
    update_entity as update_db
)
from ctutor_backend.database import get_db
from ctutor_backend.interface.messages import MessageInterface, MessageCreate, MessageGet, MessageList, MessageQuery, MessageUpdate
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

# Import business logic
from ctutor_backend.business_logic.messages import (
    create_message_with_author,
    get_message_with_read_status,
    list_messages_with_read_status,
    mark_message_as_read,
    mark_message_as_unread,
)


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
    return await create_db(permissions, db, entity, MessageInterface.model, MessageInterface.get)


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
):
    """List messages with read status."""
    items, total = await list_db(permissions, db, params, MessageInterface)
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
    """Update a message."""
    return update_db(permissions, db, id, payload, MessageInterface.model, MessageInterface.get)


@messages_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete a message."""
    delete_db(permissions, db, id, MessageInterface.model)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@messages_router.post("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_read(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Mark a message as read."""
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)
    mark_message_as_read(id, permissions, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@messages_router.delete("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_unread(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Mark a message as unread."""
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)
    mark_message_as_unread(id, permissions, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
