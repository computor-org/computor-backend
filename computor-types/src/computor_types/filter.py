from pydantic import BaseModel, Field
from typing import Any, List, Union
class FilterBase(BaseModel):
    pass

class EqualsFilter(FilterBase):
    eq: Any

class GreaterFilter(FilterBase):
    gt: Any

class LowerFilter(FilterBase):
    lt: Any

class NotEqualsFilter(FilterBase):
    ne: Any

class InFilter(FilterBase):
    in_: List[Any] = Field(..., alias='in')

class NotInFilter(FilterBase):
    not_in: List[Any] = Field(..., alias='not_in')

class LikeFilter(FilterBase):
    like: str

class ILikeFilter(FilterBase):
    ilike: str

class BetweenFilter(FilterBase):
    between: List[Any]

class IsNullFilter(FilterBase):
    is_null: bool

class NotNullFilter(FilterBase):
    not_null: bool

class StartswithFilter(FilterBase):
    startswith: str

class EndswithFilter(FilterBase):
    endswith: str

class ContainsFilter(FilterBase):
    contains: str

class AndFilter(FilterBase):
    and_: list[Union['FilterSchema', 'AndFilter', 'OrFilter']]# = Field(..., alias='and')

class OrFilter(FilterBase):
    or_: list[Union['FilterSchema', 'AndFilter', 'OrFilter']]# = Field(..., alias='or')

FilterSchema = Union[
    EqualsFilter, GreaterFilter, LowerFilter, NotEqualsFilter, InFilter, NotInFilter, 
    LikeFilter, ILikeFilter, BetweenFilter, IsNullFilter, NotNullFilter, 
    StartswithFilter, EndswithFilter, ContainsFilter, AndFilter, OrFilter
]

AndFilter.model_rebuild()
OrFilter.model_rebuild()

def get_jsonb_field(model, path):
    keys:list = path.split(".")
    column = getattr(model, keys[0])
    i = 1
    for key in keys[1:]:
        if i != len(keys)-1:
            column = (column.op('->')(key)).cast(JSONB)
        else:
            column = column.op('->>')(key).cast(String)
        i += 1

    return column

def apply_filters(query, model, filters: dict):
    if "or" in filters:
        or_conditions = [apply_filters(query, model, sub_filter) for sub_filter in filters["or"]]
        return or_(*or_conditions)

    if "and" in filters:
        and_conditions = [apply_filters(query, model, sub_filter) for sub_filter in filters["and"]]
        return and_(*and_conditions)

    filter_conditions = []
    for field, condition in filters.items():

        if isinstance(condition, dict):

            field_splitted = field.split(".")
            json_field = True if len(field_splitted) > 1 else False

            if json_field:
                column = get_jsonb_field(model, field)

            else:
                column = getattr(model, field)

                if isinstance(column.property, RelationshipProperty):

                    related_model = column.property.mapper.class_

                    filter_conditions.append(apply_filters(query,related_model,condition))

                    continue

            for operator, value in condition.items():

                if operator == "startswith":
                    filter_conditions.append(column.startswith(value))
                elif operator == "endswith":
                    filter_conditions.append(column.endswith(value))
                elif operator == "contains":
                    filter_conditions.append(column.contains(value))
                elif operator == "eq":
                    filter_conditions.append(column == value)
                elif operator == "neq":
                    filter_conditions.append(column != value)
                elif operator == "gt":
                    filter_conditions.append(column > value)
                elif operator == "geq":
                    filter_conditions.append(column >= value)
                elif operator == "lt":
                    filter_conditions.append(column < value)
                elif operator == "leq":
                    filter_conditions.append(column <= value)
                elif operator == 'in':
                    filter_conditions.append(column.in_(value))
                elif operator == 'not_in':
                    filter_conditions.append(~column.in_(value))
                elif operator == 'like':
                    filter_conditions.append(column.like(value))
                elif operator == 'ilike':
                    filter_conditions.append(column.ilike(value))
                elif operator == 'between':
                    filter_conditions.append(column.between(value[0], value[1]))
                elif operator == 'is_null':
                    filter_conditions.append(column.is_(None))
                elif operator == 'not_null':
                    filter_conditions.append(column.isnot(None))

        else:
            field_splitted = field.split(".")
            json_field = True if len(field_splitted) > 1 else False
                
            if json_field:
                column = get_jsonb_field(model, field)
                filter_conditions.append(column == condition)
            else:
                column = getattr(model, field)
                filter_conditions.append(column == condition)

    return and_(*filter_conditions) if filter_conditions else None