import base64
from collections import defaultdict
from typing import Optional
from pydantic import BaseModel, model_validator
from computor_types.api.exceptions import NotFoundException

def allowed_course_role_ids(course_role_id: str | None = None):

    hierarchy = {
        "_owner": ["_owner"],
        "_maintainer": ["_maintainer", "_owner"],
        "_lecturer": ["_lecturer", "_maintainer", "_owner"],
        "_tutor": ["_tutor", "_lecturer", "_maintainer", "_owner"],
        "_student": ["_student", "_tutor", "_lecturer", "_maintainer", "_owner"],
    }

    return hierarchy.get(course_role_id, [])

class Claims(BaseModel):
    general: dict = {}
    dependent: dict = {}

def build_claim_actions(claim_values: list[tuple[str,str]]):
    
    claims: dict[str, list[str]] = defaultdict(list)
    dependent_claims: dict = {}

    for type_, resource in claim_values:

        parts = resource.split(":")

        if len(parts) == 2:

            resource, action = parts
            claims[resource].append(action)

        elif len(parts) == 3:

            resource, action, resource_id = parts

            if dependent_claims.get(resource) == None:
                dependent_claims[resource] = {}

            if dependent_claims[resource].get(resource_id) == None:
                dependent_claims[resource][resource_id] = []

            dependent_claims[resource][resource_id].append(action)

    return Claims(
        general=dict(claims),
        dependent=dependent_claims
    )

class Principal(BaseModel):

    is_admin: bool = False
    user_id: Optional[str] = None

    roles: list[str] = []
    claims: Claims = Claims()

    @model_validator(mode='after')
    def set_is_admin_from_roles(self):
        if any(role.endswith("_admin") for role in self.roles):
            self.is_admin = True
        return self

    def encode(self):
        return base64.b64encode(bytes(self.model_dump_json(),encoding="utf-8"))

    def get_user_id(self):
        return self.user_id

    def get_user_id_or_throw(self):
        if self.user_id == None:
            raise NotFoundException()

        return self.user_id

    def permitted(self, resource: str, action: str | list[str], resource_id: str | None = None, course_role: str | None = None):
        
        if self.is_admin:
            return True

        if resource_id != None and course_role != None:
            if resource_id != None and resource in self.claims.dependent and resource_id in self.claims.dependent[resource] and any(elem in allowed_course_role_ids(course_role) for elem in self.claims.dependent[resource][resource_id]):
                return True
            
        _actions = []
        if isinstance(action, str):
            _actions = [action]
        
        else:
            _actions = action

        for _action in _actions:

            if resource in self.claims.general and _action in self.claims.general[resource]:
                return True

            if resource_id != None and resource in self.claims.dependent and resource_id in self.claims.dependent[resource] and _action in self.claims.dependent[resource][resource_id]:
                return True

        return False