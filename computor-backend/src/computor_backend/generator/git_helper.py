import os
import subprocess
from ..gitlab_utils import construct_gitlab_http_url

def git_repo_exist(directory):
  try:
    return_code = subprocess.run(f"git status",cwd=os.path.abspath(directory),shell=True)

    if return_code.returncode == 0:
        return True
    return False
  except:
      return False
  
def construct_git_auth_url(gitlab_base_url: str, full_path: str, token: str) -> str:
    """
    Construct a Git clone URL with authentication token from GitLab base URL and project path.

    Args:
        gitlab_base_url: Base GitLab URL (e.g., "http://localhost:8084")
        full_path: Project path (e.g., "testing/group/project")
        token: GitLab access token

    Returns:
        Auth URL for cloning (e.g., "http://x-token-auth:token@localhost:8084/testing/group/project.git")
    """
    if not gitlab_base_url or not full_path or not token:
        raise ValueError("gitlab_base_url, full_path, and token are required")

    # Construct the proper clone URL
    clone_url = construct_gitlab_http_url(gitlab_base_url, full_path)
    if not clone_url:
        raise ValueError(f"Failed to construct clone URL from {gitlab_base_url} and {full_path}")

    # Parse the URL to insert authentication
    if clone_url.startswith("http://"):
        return clone_url.replace("http://", f"http://x-token-auth:{token}@")
    elif clone_url.startswith("https://"):
        return clone_url.replace("https://", f"https://x-token-auth:{token}@")
    else:
        raise ValueError(f"Unsupported URL scheme in {clone_url}")


def git_http_url_to_ssh_url(http_url_to_repo: str, token: str):
    """
    DEPRECATED: This function works with potentially broken http_url_to_repo from GitLab API.
    Use construct_git_auth_url instead with proper gitlab_base_url and full_path.
    """
    import warnings
    warnings.warn(
        "git_http_url_to_ssh_url is deprecated due to broken GitLab API URLs. "
        "Use construct_git_auth_url instead.",
        DeprecationWarning,
        stacklevel=2
    )

    http_type = ""
    if http_url_to_repo.startswith("http://"):
        repo_url = http_url_to_repo.replace("http://","")
        http_type = "http://"
    elif http_url_to_repo.startswith("https://"):
        repo_url = http_url_to_repo.replace("https://","")
        http_type = "https://"

    return f"{http_type}x-token-auth:{token}@{repo_url}"

def git_clone_from_properties(directory: str, gitlab_base_url: str, full_path: str, token: str):
    """
    Clone a Git repository using proper URL construction.

    Args:
        directory: Target directory for cloning
        gitlab_base_url: Base GitLab URL (e.g., "http://localhost:8084")
        full_path: Project path (e.g., "testing/group/project")
        token: GitLab access token
    """
    auth_url = construct_git_auth_url(gitlab_base_url, full_path, token)
    return subprocess.check_call(f"git clone {auth_url} {directory}", cwd=os.path.abspath(directory), shell=True)


def git_clone(directory: str, http_url_to_repo: str, token: str):
    """
    DEPRECATED: This function works with potentially broken http_url_to_repo from GitLab API.
    Use git_clone_from_properties instead with proper gitlab_base_url and full_path.
    """
    import warnings
    warnings.warn(
        "git_clone is deprecated due to broken GitLab API URLs. "
        "Use git_clone_from_properties instead.",
        DeprecationWarning,
        stacklevel=2
    )
    ssh_url = git_http_url_to_ssh_url(http_url_to_repo, token)
    return subprocess.check_call(f"git clone {ssh_url} {directory}", cwd=os.path.abspath(directory), shell=True)

def git_checkout(directory: str, commit: str):
    return subprocess.check_call(f"git checkout {commit}", cwd=os.path.abspath(directory), shell=True)

def git_pull(directory: str):
    return subprocess.check_call(f"git pull", cwd=os.path.abspath(directory), shell=True)

def git_fetch_all(directory: str):
    return subprocess.check_call(f"git fetch --all", cwd=os.path.abspath(directory), shell=True)

def clone_or_pull_and_checkout(directory, repo_url, token, commit):
    
  try:
      if not os.path.exists(directory):
        print(f"Cloning {repo_url} into {directory}...")

        if not os.path.exists(directory):
          os.makedirs(directory,exist_ok=True)

        git_clone(directory, repo_url, token)

      elif os.path.exists(directory) and not os.path.exists(os.path.join(directory,".git")):

        os.removedirs(directory)

        print(f"Cloning {repo_url} into {directory}...")

        if not os.path.exists(directory):
          os.makedirs(directory,exist_ok=True)

        git_clone(directory, repo_url, token)
      else:
        git_checkout(directory,"main")
        git_fetch_all(directory)
         
      return git_checkout(directory,commit)

  except subprocess.CalledProcessError as e:
      print(f"An error occurred while cloning: {e}")
      return

def git_repo_create_from_properties(directory: str, gitlab_base_url: str, full_path: str, token: str):
    """
    Create and initialize a Git repository using proper URL construction.

    Args:
        directory: Local directory to initialize
        gitlab_base_url: Base GitLab URL (e.g., "http://localhost:8084")
        full_path: Project path (e.g., "testing/group/project")
        token: GitLab access token
    """
    repo_url = construct_git_auth_url(gitlab_base_url, full_path, token)

    subprocess.check_call(f"git init --initial-branch=main", cwd=os.path.abspath(directory), shell=True)
    subprocess.check_call(f"git remote add origin {repo_url}", cwd=os.path.abspath(directory), shell=True)
    subprocess.run(f"git pull --set-upstream origin main", cwd=os.path.abspath(directory), shell=True)

    subprocess.check_call(f"git add .", cwd=os.path.abspath(directory), shell=True)

    exec = subprocess.run(f'git commit -m "system release: from template"', cwd=os.path.abspath(directory), shell=True)
    if exec.returncode != 0:
        return

    subprocess.run(f"git push --set-upstream origin main", cwd=os.path.abspath(directory), shell=True)


def git_repo_create(directory: str, http_url_to_repo: str, token: str):
    """
    DEPRECATED: This function works with potentially broken http_url_to_repo from GitLab API.
    Use git_repo_create_from_properties instead with proper gitlab_base_url and full_path.
    """
    import warnings
    warnings.warn(
        "git_repo_create is deprecated due to broken GitLab API URLs. "
        "Use git_repo_create_from_properties instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # https://docs.gitlab.com/ee/api/projects.html
    # http_url_to_repo mit token vermischen

    # apiProject.http_url_to_repo

    repo_url = git_http_url_to_ssh_url(http_url_to_repo, token)

    subprocess.check_call(f"git init --initial-branch=main", cwd=os.path.abspath(directory), shell=True)
    subprocess.check_call(f"git remote add origin {repo_url}", cwd=os.path.abspath(directory), shell=True)
    subprocess.run(f"git pull --set-upstream origin main", cwd=os.path.abspath(directory), shell=True)

    subprocess.check_call(f"git add .", cwd=os.path.abspath(directory), shell=True)

    exec = subprocess.run(f'git commit -m "system release: from template"', cwd=os.path.abspath(directory), shell=True)
    if exec.returncode != 0:
        return

    subprocess.run(f"git push --set-upstream origin main", cwd=os.path.abspath(directory), shell=True)

def git_repo_pull(directory):
  subprocess.run(f"git pull", cwd=os.path.abspath(directory), shell=True)

def git_repo_commit(directory: str, commit_message: str, branch: str = "main"):
  subprocess.run(f"git add .", cwd=os.path.abspath(directory),shell=True)
  exec = subprocess.run(f'git commit -m "{commit_message}"', cwd=os.path.abspath(directory), shell=True)
  if exec.returncode != 0:
      return
  subprocess.check_output(f"git push --set-upstream origin {branch}", cwd=os.path.abspath(directory), shell=True)

def git_version_identifier(directory: str) -> str:
  return subprocess.check_output(f"git rev-parse --verify HEAD", cwd=os.path.abspath(directory), shell=True).decode().strip()

def git_push_set_upstream(directory, branch):
  exec = subprocess.run(f"git push --set-upstream origin {branch}", cwd=os.path.abspath(directory), shell=True, stdout=subprocess.PIPE)

  return True if exec.returncode == 0 else False

def check_branch_is_available(directory, branch):
  exec = subprocess.run(f"git ls-remote --exit-code origin {branch}", cwd=os.path.abspath(directory), shell=True, stdout=subprocess.PIPE)

  return True if exec.returncode == 0 else False

def checkout_branch(directory, branch):

  if not check_branch_is_available(directory,branch):
    exec = subprocess.run(f"git checkout -b {branch}", cwd=os.path.abspath(directory), shell=True, stdout=subprocess.PIPE)

    if exec.returncode == 0:
      return True
    else:
      exec = subprocess.run(f"git checkout {branch}", cwd=os.path.abspath(directory), shell=True, stdout=subprocess.PIPE)

      return True if exec.returncode == 0 else False

  else:
    exec = subprocess.run(f"git checkout {branch}", cwd=os.path.abspath(directory), shell=True, stdout=subprocess.PIPE)

    return True if exec.returncode == 0 else False