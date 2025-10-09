import os
import subprocess
from typing import List
from pydantic import BaseModel

class GitCommit(BaseModel):
    hash: str
    date: str
    message: str
    author: str

def get_git_commits(directory) -> List[dict]:

    command = [
        "git",
        "log",
        #f"-n {n}",
        "--pretty=format:%h|%an|%ad|%s",
        "--date=iso",
    ]

    result = subprocess.run(command, cwd=os.path.abspath(directory), stdout=subprocess.PIPE, text=True, check=True)

    commits = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 3)
        if len(parts) == 4:
            hash_, author, date_str, message = parts
            commits.append(
                GitCommit(
                    hash=hash_.strip(),
                    date=date_str.strip(),
                    message=message.strip(),
                    author=author.strip()
                ).model_dump()
            )

    return commits