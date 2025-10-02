import json
import random
import base64
from abc import ABC
from typing import Any
from uuid import UUID
from httpx import Client, Headers, Response
from pydantic import BaseModel
from ctutor_backend.api.exceptions import response_to_http_exception
from ctutor_backend.interface.base import EntityInterface, ListQuery

def raise_if_response_is_error(response: Response):
    if response.is_error:
        response_exception = response_to_http_exception(response.status_code,response.json())
        raise response_exception if response_exception != None else response.raise_for_status()

class BaseClient(ABC):
    pass

class CrudClient(BaseClient):

    def __init__(self, url_base: str, entity_interface: EntityInterface, auth: tuple[str,str] = None, headers: Headers = {}, glp_auth_header: dict = None):
        self.url_base = url_base
        self.url = entity_interface.endpoint
        self.auth = auth
        self.client = Client(base_url=self.url_base, auth=auth,timeout=10)
        self.entity_interface = entity_interface

        self.client.headers = headers

        if glp_auth_header != None:
            crypt = base64.b64encode(bytes(json.dumps(glp_auth_header),encoding="utf-8"))
            self.client.headers.update({"GLP-CREDS": str(crypt,"utf-8") })

    def get(self, id: UUID | str) -> BaseModel:
        try:
            response = self.client.get(f"{self.url}/{id}")

            raise_if_response_is_error(response)

        except Exception as e:
            raise e
            
        try:
            return self.entity_interface.get(**response.json())
        except Exception as e:
            raise Exception(response)
        
    def list(self, params: ListQuery | dict | None = None) -> list[BaseModel]:
    
        try:
            if params != None:
                if isinstance(params,ListQuery):
                    params = params.model_dump(exclude_unset=True)

        except Exception as e:
            raise e
        
        try:
            response = self.client.get(self.url, params=params)

            raise_if_response_is_error(response)
        
        except Exception as e:
            raise e

        try:
            json_response = response.json()
        
            entities: list = []

            for entity_response in json_response:
                entity = self.entity_interface.list(**entity_response)
                entities.append(entity)
            
            return entities
        except Exception as e:
            raise Exception(response)
        
    def get_first_or_default(self, params: BaseModel | None = None, default: Any = None):
        entities = self.list(params)
        
        if len(entities) >= 1:
            return entities[0]
        else:
            return default
        
    def get_random_or_default(self, params: BaseModel | None = None, default: Any = None):
        entities = self.list(params)
        
        if len(entities) == 1:
            return entities[0]
        elif len(entities) > 0:
            entity = entities[random.randint(0,len(entities)-1)]

            return entity if entity != None else default
        else:
            return default
        
    def create(self, entity: BaseModel):
        
        create_entity = entity.model_dump()
        
        try:
            response = self.client.post(f"{self.url}",json=create_entity)

            raise_if_response_is_error(response)
                
        except Exception as e:
            raise e
            
        try:
            return self.entity_interface.get(**response.json())
        except Exception as e:
            raise Exception(response.json())
        
    def update(self, id: UUID | str, entity: BaseModel):
        
        update_entity = entity.model_dump(exclude_unset=True)

        try:
            response = self.client.patch(f"{self.url}/{id}",json=update_entity)

            raise_if_response_is_error(response)
            
        except Exception as e:
            raise e
            
        try:
            return self.entity_interface.get(**response.json())
        except Exception as e:
            raise Exception(response)
    
    def delete(self, id: UUID | str):
    
        try:
            response = self.client.delete(f"{self.url}/{id}")

            raise_if_response_is_error(response)
        
        except Exception as e:
            raise e
            
        return response
    
class CustomClient(BaseClient):

    def __init__(self, url_base: str, auth: tuple[str,str] = None, headers: Headers = {}, glp_auth_header: dict = None):
        self.url_base = url_base
        self.auth = auth
        self.client = Client(base_url=self.url_base, auth=auth, timeout=10)

        self.client.headers = headers

        if glp_auth_header != None:
            crypt = base64.b64encode(bytes(json.dumps(glp_auth_header),encoding="utf-8"))
            self.client.headers.update({"GLP-CREDS": str(crypt,"utf-8") })

    def create(self, endpoint, payload = None, params: dict = None, files = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.post,
            wrapper=self._return_one,
            payload=payload,
            files=files)
        
    def get(self, endpoint, params: dict = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.get,
            wrapper=self._return_one)

    def get_file(self, endpoint, params: dict = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.get,
            wrapper=self._return_file)
        
    def list(self, endpoint, params: dict = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.get,
            wrapper=self._return_list)

    def update(self, endpoint, payload, params: dict = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.patch,
            wrapper=self._return_one,
            payload=payload)
        
    def delete(self, endpoint, params: dict = None):
        return self._call(
            endpoint=endpoint,
            params=params,
            func_method=self.client.delete,
            wrapper=self._return_one)

    def _return_one(self, response: Response):

        raise_if_response_is_error(response)
        
        if response.status_code == 204:
            return "OK"
        try:
            return response.json()

        except Exception as e:
            raise Exception(response)

    def _return_file(self, response: Response):

        raise_if_response_is_error(response)
        
        if response.status_code == 204:
            return "OK"
        try:
            return response.stream

        except Exception as e:
            raise Exception(response)

    def _return_list(self, response: Response):

        raise_if_response_is_error(response)

        try:
            json_response = response.json()

            entities: list = []

            for entity_response in json_response:
                
                entities.append(entity_response)

            return entities
        
        except Exception as e:
            raise Exception(response)

    def _call(self, endpoint, func_method, wrapper, payload: dict = None, params: dict = None, files = None):
        try:
            if files != None:
                if params != None:
                    response = func_method(f"{endpoint}",params=params,files=files)
                else:
                    response = func_method(f"{endpoint}",files=files)
                return

            if payload == None:
                response = func_method(f"{endpoint}",params=params)
            else:
                response = func_method(f"{endpoint}",json=payload,params=params)
        except Exception as e:
            raise e
            
        return wrapper(response)