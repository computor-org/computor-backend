import os
import re
import shutil
import subprocess
from pydantic import BaseModel, field_validator
from pydantic import BaseModel
from typing import Optional

class Repository(BaseModel):
    url: str
    user: Optional[str] = ""
    token: Optional[str] = ""
    branch: Optional[str] = "main"
    path: Optional[str] = ""
    commit: Optional[str] = ""

    @field_validator('url')
    def validate_git_url(cls, v):
        git_url_pattern = "(?:git|ssh|https?|git@[-\w.]+):(\/\/)?(.*?)(\.git)(\/?|\#[-\d\w._]+?)$"

        if not re.match(git_url_pattern, v):
            raise ValueError('URL must be a valid Git repository URL')
        return v

    @field_validator('token')
    def validate_git_token(cls, v):
        if v == None or v == "":
          return v

        allowed_pattern = r'^\S+$'

        if not re.match(allowed_pattern, v):
            raise ValueError('TOKEN must be a valid Git repository token')

        return v

    @field_validator('branch')
    def is_valid_branch_or_commit(cls, v):
        commit_pattern = r'^[0-9a-fA-F]{40}$'

        forbidden_branch_chars_pattern = r'[\s*:?"><|\\]'
        if re.search(forbidden_branch_chars_pattern, v) and re.match(commit_pattern, v):
            raise ValueError('BRANCH must be a valid Git repository branch')
        return v

    @field_validator('user')
    def is_valid_user(cls, v):
        if v == None or v == "":
          return v

        path_pattern = r'^\S+$'

        if not bool(re.match(path_pattern, v)):
            raise ValueError('USER must be a valid Git user')
        return v

    @field_validator('path')
    def is_valid_path(cls, v):
        if v == "" or v == "/":
          return v

        path_pattern = r'^(\/)?([^\/\0]+(\/)?)+$'

        if not bool(re.match(path_pattern, v)):
            raise ValueError('PATH must be a valid unix path')
        return v

    def build_repository(self):

      if self.token == None or self.token == "":
          return self.url
      else:
          try:
            repo_url = self.url
            repo_url = repo_url.replace("https://","")
            repo_url = repo_url.replace("git@", "")
            repo_url = repo_url.replace(":","/")
            if self.user != None and self.user != "":
              return f"https://{self.user}:{self.token}@{repo_url}"
            elif self.user == None or self.user == "":
              return f"https://x-token-auth:{self.token}@{repo_url}"

          except:
            raise Exception({'repository': {'url: ', repo_url, ', token: ', self.token}})

    def clone(self,local_path):
        repo_url = self.build_repository()
        
        if self.commit != None and self.commit != "":
            subprocess.check_output(f"git clone --quiet {repo_url} {local_path}", shell=True)
            subprocess.check_output(f"git checkout --quiet {self.commit}", cwd=os.path.abspath(local_path), shell=True)
        else:
            subprocess.check_output(f"git clone --quiet {repo_url} {local_path}", shell=True)

    def clone_or_fetch(self,local_path):
      repo_url = self.build_repository()
      if os.path.isdir(local_path) and not os.path.isdir(f"{local_path}/.git"):
            shutil.rmtree(local_path)
      if not os.path.isdir(local_path):
            os.mkdir(local_path)
            return subprocess.check_output(f"git clone --depth=1 --single-branch --branch={self.branch} --quiet {repo_url} {local_path}", shell=True)
      else:
            return subprocess.check_output(f"git -C {local_path} fetch origin {self.branch} -q; git -C {local_path} reset --hard FETCH_HEAD -q; git -C {local_path} clean -df -q", shell=True)
