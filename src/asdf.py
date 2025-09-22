import os
import sys
import asyncio
import logging
from pathlib import Path

from ctutor_backend.client.crud_client import CustomClient

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file from project root
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)

if __name__ == "__main__":
    client = CustomClient("http://localhost:8000", auth=("course_manager","password"))
    data = client.get("/students/course-contents?title=Mathematische Konstanten")
    import json
    print(json.dumps(data,indent=1))