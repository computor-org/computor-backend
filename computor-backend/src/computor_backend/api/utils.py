import os
from typing import Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import tuple_, and_
from sqlalchemy.orm import Session
from computor_backend.api.exceptions import BadRequestException
from computor_backend.model.course import Course, CourseContent

# TODO: REFACTORING to other types (github, minio, filesystem, etc.)

def url_to_provider_path(gitlab_url: str):   
    http_type = ""
    if gitlab_url.startswith("http://"):
        repo_url = gitlab_url.replace("http://","")
        http_type = "http://"
    elif gitlab_url.startswith("https://"):
        repo_url = gitlab_url.replace("https://","")
        http_type = "https://"

    path_splitted = repo_url.split("/")

    # TODO: REFACTORING
    if path_splitted[-1] == "assignments":
        path_splitted.pop()

    provider = f"{http_type}{path_splitted[0]}"
    full_path = "/".join(path_splitted[1:])

    return provider, full_path

def get_course_id_from_url(gitlab_url: str, db: Session):

    provider, full_path = url_to_provider_path(gitlab_url)

    return db.query(Course.properties).filter(Course.properties["gitlab"].op("->>")("url") == provider,Course.properties["gitlab"].op("->>")("full_path") == full_path).scalar()

def get_course_content_id_from_url_and_directory(release_dir: str, gitlab_url: str, db: Session):

    provider, full_path = url_to_provider_path(gitlab_url)

    return db.query(CourseContent.id) \
        .join(Course,Course.id == CourseContent.course_id) \
            .filter(Course.properties["gitlab"].op("->>")("url") == provider, Course.properties["gitlab"].op("->>")("full_path") == full_path, CourseContent.properties["gitlab"].op("->>")("directory") == release_dir).scalar()

def getattrtuple(o: object, names: tuple) -> tuple:
    attrs = []
    for name in names:
        attrs.append(getattr(o, name))
    return tuple(attrs)

def hasattrtuple(o: object, names: tuple) -> bool:
    for name in names:
        if not hasattr(o, name):
            return False
    return True

def sync_dependent_items(dependents: list[tuple[str, UUID | str | int | float]], dependent_items: list[BaseModel], dependent_item_type: Any, foreign_key: str | tuple, db: Session):

    if isinstance(foreign_key, str):
        foreign_key = (foreign_key,)
    
    if not hasattrtuple(dependent_item_type, foreign_key):
        raise BadRequestException()
    
    error_list_dependents = []
    for dependent in dependents:
        if not hasattr(dependent_item_type, dependent[0]):
            error_list_dependents.append(f"{dependent[0]} not in {dependent_item_type}")
    
    if len(error_list_dependents) > 0:
        raise BadRequestException(detail=error_list_dependents)
    
    check_expressions = []
    for dependent in dependents:
        check_expressions.append(getattr(dependent_item_type,dependent[0]) == dependent[1])

    new_course_item_keys = [getattrtuple(item, foreign_key) for item in dependent_items]
    existing_item_db = db.query(dependent_item_type).filter(and_(*check_expressions), tuple_(*getattrtuple(dependent_item_type, foreign_key)).in_(new_course_item_keys)).all()
    existing_item_db_keys = {getattrtuple(item, foreign_key) for item in existing_item_db}

    for item in existing_item_db:
        new_items_list = [a for a in dependent_items if getattrtuple(a, foreign_key) == getattrtuple(item, foreign_key)]
        if len(new_items_list) == 1:
            new_item = new_items_list[0]
            for key in new_item.model_fields_set:
                setable = True
                if key == "id":
                    setable = False
                for fk in foreign_key:
                    if key == fk:
                        setable = False
                        break
                for dependent in dependents:
                    if key == dependent[0]:
                        setable = False
                        break
                if setable == True:
                    setattr(item, key, getattr(new_item,key))

    # for it in existing_item_db:
    #     print(getattrtuple(it, foreign_key))

    ## CREATE NEW ITEM TYPES

    new_items_to_insert = [
        dependent_item_type(**item.model_dump())
        for item in dependent_items
        if getattrtuple(item, foreign_key) not in existing_item_db_keys
    ]

    for it in new_items_to_insert:
        print(getattrtuple(it, foreign_key))

    db.bulk_save_objects(new_items_to_insert)

    ## CREATE NEW ITEM TYPES

    items_to_delete = db.query(dependent_item_type).filter(and_(*check_expressions),~tuple_(*getattrtuple(dependent_item_type, foreign_key)).in_(new_course_item_keys)).all()

    for it in items_to_delete:
        print(getattrtuple(it, foreign_key))

    for item in items_to_delete:
        db.delete(item)
        

def position_directory_to_db_path(directory: str) -> str:
    dir_split = directory.split("_")

    if len(dir_split) > 1 and dir_split[0].isdigit():
        dir_split = dir_split[1:]

    return "_".join(dir_split).replace("-", "_").replace(" ", "_")

def position_directory_to_position(directory: str) -> float:

    dir_split = directory.split("_")

    if len(dir_split) == 1:
        return 0

    if dir_split[0].isdigit():
        return float(dir_split[0])
    else:
        return 0
    
def directory_path_to_db_path_and_parent_path(directory: str) -> tuple[str,str]:

    parts = directory.strip().split("/")
    new_parts = []

    for part in parts:
        new_parts.append(position_directory_to_db_path(part))

    if len(new_parts) <= 1:
        path = "".join(new_parts)
        parent_path = None
    else:
        path = ".".join(new_parts).replace(" ", "_")
        parent_path = ".".join(new_parts[:-1]).replace(" ", "_")

    return path, parent_path

def directory_path_to_position(directory: str) -> float:
    return position_directory_to_position(directory.split("/")[-1])

def collect_sub_path_positions_if_meta_exists(root_dir):
    data = []

    for dirpath, dirnames, filenames in os.walk(root_dir):

        # TODO: validate meta file
        if 'meta.yaml' in filenames:

            directory = os.path.relpath(dirpath,root_dir)

            if directory == ".":
                continue

            path, parent_path = directory_path_to_db_path_and_parent_path(directory)
            position = directory_path_to_position(directory)
            
            data.append((directory,path,position))

    return data
