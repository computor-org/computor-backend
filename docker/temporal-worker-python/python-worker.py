
import os
import sys
import subprocess
from computor_types.repositories import Repository

if __name__ == '__main__':

    PYTHON_TEST_ENGINE_URL = os.getenv("PYTHON_TEST_ENGINE_URL")
    PYTHON_TEST_ENGINE_TOKEN = os.getenv("PYTHON_TEST_ENGINE_TOKEN")
    PYTHON_TEST_ENGINE_VERSION = os.getenv("PYTHON_TEST_ENGINE_VERSION") or "main"

    if PYTHON_TEST_ENGINE_TOKEN is None:
       print("No test repository token available. Please assign environment variable PYTHON_TEST_ENGINE_TOKEN to python worker!")
       sys.exit(2)
       
    worker_path = os.path.abspath("/tmp/engine")
      
    try:
      print(Repository(url=PYTHON_TEST_ENGINE_URL,token=PYTHON_TEST_ENGINE_TOKEN,branch=PYTHON_TEST_ENGINE_VERSION).clone_or_fetch(worker_path))
    except Exception as e:
      print(f"FAILED: git clone {PYTHON_TEST_ENGINE_URL} failed [{str(e)}]")
      quit(2)
    
    cmd = "python -m venv venv && venv/bin/pip install ."
    subprocess.run(cmd, cwd=worker_path, shell=True)
    
    # Pass command line arguments to the temporal worker
    # This allows docker-compose to specify --queues=testing-python
    args = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    cmd = f"python -m computor_backend.tasks.temporal_worker {args}"
    print(f"Starting temporal worker with command: {cmd}")
    subprocess.run(cmd, cwd=os.path.abspath(os.path.expanduser("~")), shell=True)