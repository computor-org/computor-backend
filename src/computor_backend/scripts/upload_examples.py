#!/usr/bin/env python3
"""
Script to upload examples from the examples/ directory to the Example Library API.

This script iterates over directories in examples/ and uploads each one as an example
using the API endpoint.
"""

import os
import sys
import json
import yaml
import requests
import zipfile
from pathlib import Path
from typing import Dict, Optional, List
import argparse

# Add the parent directory to sys.path to import from computor_backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from computor_backend.database import get_db
    from computor_backend.model.example import ExampleRepository
    from sqlalchemy.orm import Session
except ImportError:
    # If running without full backend setup, just skip the database imports
    print("Note: Running without database imports (for zip creation only)")
    get_db = None
    ExampleRepository = None
    Session = None


class ExampleUploader:
    """Handles uploading examples to the API."""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if auth_token:
            # Check if it's basic auth (contains colon) or bearer token
            if ':' in auth_token:
                # Basic auth format: username:password
                username, password = auth_token.split(':', 1)
                self.session.auth = (username, password)
            else:
                # Bearer token format
                self.session.headers.update({'Authorization': f'Bearer {auth_token}'})
    
    def create_repository_if_not_exists(self, name: str, description: str = None) -> Dict:
        """Create an example repository if it doesn't exist."""
        # First, try to list repositories to see if it exists
        response = self.session.get(f"{self.base_url}/example-repositories")
        
        if response.status_code == 200:
            repositories = response.json()
            for repo in repositories:
                if repo['name'] == name:
                    print(f"Repository '{name}' already exists (ID: {repo['id']})")
                    return repo
        
        # Create new repository
        repo_data = {
            "name": name,
            "description": description or f"Repository for {name} examples",
            "source_type": "minio",
            "source_url": "examples-bucket/local"
        }
        
        response = self.session.post(f"{self.base_url}/example-repositories", json=repo_data)
        
        if response.status_code in [200, 201]:
            repo = response.json()
            print(f"Created repository '{name}' (ID: {repo['id']})")
            return repo
        else:
            print(f"Failed to create repository: {response.status_code} - {response.text}")
            return None
    
    def read_file_content(self, file_path: Path) -> str:
        """Read file content as string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # If it's not UTF-8, try binary and decode
            with open(file_path, 'rb') as f:
                content = f.read()
                # Try common encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # If all fail, use utf-8 with error replacement
                return content.decode('utf-8', errors='replace')
    
    def parse_meta_yaml(self, meta_path: Path) -> Dict:
        """Parse meta.yaml file."""
        try:
            content = self.read_file_content(meta_path)
            return yaml.safe_load(content)
        except Exception as e:
            print(f"Warning: Could not parse {meta_path}: {e}")
            return {}
    
    def generate_identifier(self, directory_name: str, meta_data: Dict) -> str:
        """Generate identifier from directory name and meta.yaml."""
        # Try to use slug from meta.yaml if available
        if 'slug' in meta_data:
            return meta_data['slug']
        
        # Otherwise, generate from directory name
        # Convert directory name to dot-separated format
        identifier = directory_name.replace('-', '.').replace('_', '.')
        return identifier
    
    def upload_example(self, repository_id: str, example_dir: Path) -> bool:
        """Upload a single example directory."""
        print(f"\nUploading example from: {example_dir}")
        
        # Check if directory exists and contains files
        if not example_dir.is_dir():
            print(f"Error: {example_dir} is not a directory")
            return False
        
        # Look for meta.yaml
        meta_path = example_dir / "meta.yaml"
        
        if not meta_path.exists():
            print(f"Warning: No meta.yaml found in {example_dir}")
            # Create a basic meta.yaml
            meta_content = f"""slug: {example_dir.name}
version: '1.0'
title: {example_dir.name.replace('-', ' ').replace('_', ' ').title()}
description: Example from {example_dir.name}
language: en
"""
        else:
            meta_content = self.read_file_content(meta_path)
        
        # Parse meta.yaml for metadata
        meta_data = yaml.safe_load(meta_content) if meta_content else {}
        
        
        # Collect all files (including meta.yaml and test.yaml)
        files = {}
        for file_path in example_dir.iterdir():
            if file_path.is_file():
                files[file_path.name] = self.read_file_content(file_path)
        
        # Generate identifier
        identifier = self.generate_identifier(example_dir.name, meta_data)
        
        # Prepare upload request
        upload_data = {
            "repository_id": repository_id,
            "directory": example_dir.name,
            "version_tag": meta_data.get('version', '1.0'),
            "files": files
        }
        
        # Upload to API
        response = self.session.post(f"{self.base_url}/examples/upload", json=upload_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Successfully uploaded {example_dir.name}")
            print(f"   Version ID: {result['id']}")
            print(f"   Identifier: {identifier}")
            print(f"   Files: {list(files.keys())}")
            return True
        else:
            print(f"❌ Failed to upload {example_dir.name}: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    
    def download_example(self, version_id: str, output_dir: Path) -> bool:
        """Download an example version."""
        response = self.session.get(f"{self.base_url}/examples/download/{version_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Create output directory
            example_dir = output_dir / f"downloaded_{data['version_tag']}"
            example_dir.mkdir(parents=True, exist_ok=True)
            
            # Write files
            for filename, content in data['files'].items():
                file_path = example_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Write meta.yaml
            with open(example_dir / 'meta.yaml', 'w', encoding='utf-8') as f:
                f.write(data['meta_yaml'])
            
            # Write test.yaml if present
            if data['test_yaml']:
                with open(example_dir / 'test.yaml', 'w', encoding='utf-8') as f:
                    f.write(data['test_yaml'])
            
            print(f"✅ Downloaded to: {example_dir}")
            return True
        else:
            print(f"❌ Failed to download: {response.status_code} - {response.text}")
            return False
    
    def create_zip_from_directory(self, directory_path: Path, output_path: Path) -> bool:
        """Create a zip file from a directory."""
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in directory_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        arcname = file_path.relative_to(directory_path)
                        zipf.write(file_path, arcname)
            
            print(f"✅ Created zip file: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create zip: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Upload examples from examples/ directory")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL of the API")
    parser.add_argument("--auth-token", help="Bearer token for authentication")
    parser.add_argument("--examples-dir", default="examples", 
                       help="Directory containing example subdirectories")
    parser.add_argument("--repository-name", default="Local Examples",
                       help="Name of the repository to create/use")
    parser.add_argument("--download", help="Download example by version ID")
    parser.add_argument("--download-dir", default="downloads",
                       help="Directory to download examples to")
    parser.add_argument("--list-only", action="store_true",
                       help="Only list examples without uploading")
    parser.add_argument("--create-zips", action="store_true",
                       help="Create zip files from example directories")
    parser.add_argument("--zips-dir", default="example_zips",
                       help="Directory to store created zip files")
    
    args = parser.parse_args()
    
    uploader = ExampleUploader(args.base_url, args.auth_token)
    
    # Handle download
    if args.download:
        output_dir = Path(args.download_dir)
        output_dir.mkdir(exist_ok=True)
        success = uploader.download_example(args.download, output_dir)
        sys.exit(0 if success else 1)
    
    # Find examples directory
    examples_dir = Path(args.examples_dir)
    if not examples_dir.exists():
        print(f"Error: Examples directory '{examples_dir}' not found")
        sys.exit(1)
    
    # List example directories
    example_subdirs = [d for d in examples_dir.iterdir() if d.is_dir()]
    
    if not example_subdirs:
        print(f"No example directories found in {examples_dir}")
        sys.exit(1)
    
    print(f"Found {len(example_subdirs)} example directories:")
    for subdir in example_subdirs:
        print(f"  - {subdir.name}")
    
    if args.list_only:
        sys.exit(0)
    
    # Handle zip creation
    if args.create_zips:
        zips_dir = Path(args.zips_dir)
        zips_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 Creating zip files in {zips_dir}...")
        
        for example_dir in example_subdirs:
            zip_path = zips_dir / f"{example_dir.name}.zip"
            success = uploader.create_zip_from_directory(example_dir, zip_path)
            if not success:
                print(f"Failed to create zip for {example_dir.name}")
        
        print(f"\n✅ Zip files created in {zips_dir}")
        print("You can now upload these zip files through the web UI.")
        sys.exit(0)
    
    # Create or get repository
    repository = uploader.create_repository_if_not_exists(
        args.repository_name,
        f"Repository containing examples from {examples_dir}"
    )
    
    if not repository:
        print("Failed to create/get repository")
        sys.exit(1)
    
    # Upload each example
    successful = 0
    failed = 0
    
    for example_dir in example_subdirs:
        try:
            success = uploader.upload_example(repository['id'], example_dir)
            if success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Error uploading {example_dir.name}: {e}")
            failed += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📁 Total: {len(example_subdirs)}")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()