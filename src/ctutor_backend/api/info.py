# import os
# import zipfile
# import tempfile
# from fastapi import APIRouter
# from pydantic import BaseModel
# from ctutor_backend.interface.tokens import decrypt_api_key
# from gitlab import Gitlab
# from ctutor_backend.api.exceptions import NotFoundException
# from ctutor_backend.redis_cache import get_redis_client
# from ctutor_backend.database import get_db
# from ctutor_backend.interface.organizations import OrganizationProperties
# from ctutor_backend.model.organization import Organization

# info_router = APIRouter()

# @info_router.get("", response_model=dict)
# async def get_server_info():

#     cache = await get_redis_client()

#     vsc_info = await cache.get("extensions:vsc")

#     if vsc_info == None:
#         vsc_info = await get_vsc_extension_info()

#         if vsc_info != None:
#             await cache.set("extensions:vsc", vsc_info)

#     return {
#         "extensions": [vsc_info]
#     }

# def get_version_from_manifest(file_path: str) -> str:

#     import xml.etree.ElementTree as ET

#     try:
#         tree = ET.parse(file_path)
#         root = tree.getroot()

#         namespace = {'ns': 'http://schemas.microsoft.com/developer/vsx-schema/2011'}
#         identity = root.find(".//ns:Identity", namespace)

#         if identity is not None and "Version" in identity.attrib:
#             return identity.attrib["Version"]
#         else:
#             return "<not found>"
#     except Exception as e:
#         return "<not found>"

# class VSCExtensionConfig(BaseModel):
#     project_id: int
#     gitlab_url: str
#     file_path: str
#     download_link: str

# async def get_vsc_extension_info():

#     try:
#         vsc_config = VSCExtensionConfig(
#             project_id=os.environ.get("VSC_GITLAB_PROJECT_ID"),
#             gitlab_url=os.environ.get("VSC_GITLAB_URL"),
#             file_path=os.environ.get("VSC_FILE_PATH"),
#             download_link=os.environ.get("VSC_VSIX_DOWNLOAD_LINK")
#         )

#     except:
#         raise NotFoundException()

#     with next(get_db()) as db:
#         query = db.query(Organization.properties).filter(Organization.properties["gitlab"].op("->>")("url") == vsc_config.gitlab_url).first()

#     if query == None:
#         raise NotFoundException()

#     query = query[0]

#     organization_props = OrganizationProperties(**query)

#     token = decrypt_api_key(organization_props.gitlab.token)

#     gitlab = Gitlab(url=vsc_config.gitlab_url,private_token=token)

#     project = gitlab.projects.get(vsc_config.project_id)

#     with tempfile.TemporaryDirectory() as tmp:

#         vsix_tmp = os.path.join(tmp,os.path.basename(vsc_config.file_path))

#         with open(vsix_tmp, "wb") as f:
#             file_content = project.files.get(file_path=vsc_config.file_path, ref="main").decode()
#             f.write(file_content)

#         manifest_tmp = os.path.join(tmp,"extracted_vsix")

#         with zipfile.ZipFile(vsix_tmp, "r") as zip_ref:
#             zip_ref.extractall(manifest_tmp)

#         manifest_path = os.path.join(manifest_tmp,"extension.vsixmanifest")

#     vsc_info = {
#             "type": "vsc",
#             "version": get_version_from_manifest(manifest_path),
#             "source": vsc_config.download_link
#         }

#     return vsc_info