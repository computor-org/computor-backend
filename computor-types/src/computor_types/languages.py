from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class LanguageCreate(BaseModel):
    code: str = Field(min_length=2, max_length=2, description="ISO 639-1 language code (2 lowercase letters)")
    name: str = Field(min_length=1, max_length=255, description="Language name in English")
    native_name: Optional[str] = Field(None, max_length=255, description="Language name in native script")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "de",
                "name": "German",
                "native_name": "Deutsch"
            }
        }
    )

class LanguageGet(BaseModel):
    code: str = Field(description="ISO 639-1 language code")
    name: str = Field(description="Language name in English")
    native_name: Optional[str] = Field(None, description="Language name in native script")

    model_config = ConfigDict(from_attributes=True)

class LanguageList(BaseModel):
    code: str = Field(description="ISO 639-1 language code")
    name: str = Field(description="Language name in English")
    native_name: Optional[str] = Field(None, description="Language name in native script")

    model_config = ConfigDict(from_attributes=True)

class LanguageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Language name in English")
    native_name: Optional[str] = Field(None, max_length=255, description="Language name in native script")

class LanguageQuery(ListQuery):
    code: Optional[str] = Field(None, description="Filter by language code")
    name: Optional[str] = Field(None, description="Filter by language name")

def language_search(db: 'Session', query, params: Optional[LanguageQuery]):
    if params.code is not None:
        query = query.filter(code == params.code)
    if params.name is not None:
        query = query.filter(name.ilike(f"%{params.name}%"))

    return query

class LanguageInterface(EntityInterface):
    create = LanguageCreate
    get = LanguageGet
    list = LanguageList
    update = LanguageUpdate
    query = LanguageQuery
    search = language_search
    endpoint = "languages"
    model = None  # Set by backend
    cache_ttl = 3600  # 1 hour - language data rarely changes