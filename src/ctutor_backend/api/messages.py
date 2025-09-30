from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ctutor_backend.api.crud import get_id_db, list_db, update_db, delete_db, create_db
from ctutor_backend.api.exceptions import BadRequestException
from ctutor_backend.database import get_db
from ctutor_backend.interface.messages import MessageInterface, MessageCreate, MessageGet, MessageList, MessageQuery, MessageUpdate
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.message import Message
from ctutor_backend.model.message import MessageRead


messages_router = APIRouter()


@messages_router.post("", response_model=MessageGet, status_code=status.HTTP_201_CREATED)
async def create_message(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    # Enforce author_id from current user
    if not payload.title or not payload.content:
        raise BadRequestException(detail="Title and content are required")

    model_dump = payload.model_dump(exclude_unset=True)
    model_dump['author_id'] = permissions.user_id

    # At least one target is recommended (user_id, course_member_id, submission_group_id, course_group_id)
    if not any(model_dump.get(k) for k in ['user_id', 'course_member_id', 'submission_group_id', 'course_group_id', 'course_content_id', 'course_id']):
        # Allow user-only message by setting user_id to current user if nothing else provided
        model_dump['user_id'] = permissions.user_id

    # Default level
    if 'level' not in model_dump or model_dump['level'] is None:
        model_dump['level'] = 0

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
    message = await get_id_db(permissions, db, id, MessageInterface)

    reader_user_id = permissions.user_id
    is_read = False
    if reader_user_id:
        exists = (
            db.query(MessageRead.id)
            .filter(
                MessageRead.message_id == id,
                MessageRead.reader_user_id == reader_user_id,
            )
            .first()
        )
        is_read = exists is not None

    return message.model_copy(update={"is_read": is_read})


@messages_router.get("", response_model=list[MessageList])
async def list_messages(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: MessageQuery = Depends(),
    db: Session = Depends(get_db),
):
    items, total = await list_db(permissions, db, params, MessageInterface)
    reader_user_id = permissions.user_id

    if reader_user_id and items:
        message_ids = [item.id for item in items]
        read_rows = (
            db.query(MessageRead.message_id)
            .filter(
                MessageRead.reader_user_id == reader_user_id,
                MessageRead.message_id.in_(message_ids),
            )
            .all()
        )
        read_ids = {str(row[0]) for row in read_rows}
    else:
        read_ids = set()

    items = [item.model_copy(update={"is_read": item.id in read_ids}) for item in items]

    response.headers["X-Total-Count"] = str(total)
    return items


@messages_router.patch("/{id}", response_model=MessageGet)
async def update_message(
    id: UUID | str,
    payload: MessageUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return update_db(permissions, db, id, payload, MessageInterface.model, MessageInterface.get)


@messages_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    delete_db(permissions, db, id, MessageInterface.model)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@messages_router.post("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_read(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)

    # Upsert read record for current user
    exists = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if not exists:
        db.add(MessageRead(message_id=id, reader_user_id=permissions.user_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@messages_router.delete("/{id}/reads", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_unread(
    id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    # Ensure user has visibility on the message
    await get_id_db(permissions, db, id, MessageInterface)

    read = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if read:
        db.delete(read)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
