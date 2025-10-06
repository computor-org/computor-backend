#!/usr/bin/env python3
"""
Simple test script for the Examples API.

This script provides basic functionality to test the examples API endpoints.
"""

import requests
import json
import sys
from pathlib import Path


class ExampleAPITester:
    """Simple tester for the Examples API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def test_repositories(self):
        """Test repository endpoints."""
        print("🧪 Testing Repository Endpoints")
        print("=" * 40)
        
        # List repositories
        print("\n1. Listing repositories...")
        response = self.session.get(f"{self.base_url}/example-repositories")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            repos = response.json()
            print(f"   Found {len(repos)} repositories")
            for repo in repos[:3]:  # Show first 3
                print(f"   - {repo['name']} ({repo['source_type']})")
        else:
            print(f"   Error: {response.text}")
        
        # Create test repository
        print("\n2. Creating test repository...")
        repo_data = {
            "name": "API Test Repository",
            "description": "Test repository created by API tester",
            "source_type": "minio",
            "source_url": "test-bucket/api-test"
        }
        
        response = self.session.post(f"{self.base_url}/example-repositories", json=repo_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            repo = response.json()
            print(f"   Created: {repo['name']} (ID: {repo['id']})")
            return repo['id']
        else:
            print(f"   Error: {response.text}")
            return None
    
    def test_examples(self, repository_id: str):
        """Test example endpoints."""
        print("\n🧪 Testing Example Endpoints")
        print("=" * 40)
        
        # List examples
        print("\n1. Listing examples...")
        response = self.session.get(f"{self.base_url}/examples")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            examples = response.json()
            print(f"   Found {len(examples)} examples")
        
        # Create test example
        print("\n2. Creating test example...")
        example_data = {
            "example_repository_id": repository_id,
            "directory": "test-example",
            "identifier": "api.test.example",
            "title": "API Test Example",
            "description": "Example created by API tester",
            "subject": "python",
            "tags": ["test", "api"]
        }
        
        response = self.session.post(f"{self.base_url}/examples", json=example_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            example = response.json()
            print(f"   Created: {example['title']} (ID: {example['id']})")
            return example['id']
        else:
            print(f"   Error: {response.text}")
            return None
    
    def test_upload_download(self, repository_id: str):
        """Test upload and download functionality."""
        print("\n🧪 Testing Upload/Download")
        print("=" * 40)
        
        # Test upload
        print("\n1. Testing upload...")
        upload_data = {
            "repository_id": repository_id,
            "directory": "hello-world",
            "version_tag": "1.0",
            "files": {
                "main.py": "print('Hello, World!')\n",
                "README.md": "# Hello World Example\n\nA simple hello world program.\n"
            },
            "meta_yaml": """slug: api.test.hello.world
version: '1.0'
title: Hello World
description: Simple hello world example
language: en
properties:
  studentSubmissionFiles:
  - main.py
""",
            "test_yaml": """type: python
name: Hello World Test
description: Test for hello world
version: '1.0'
properties:
  tests:
  - type: output
    name: hello_output
    expected: "Hello, World!"
"""
        }
        
        response = self.session.post(f"{self.base_url}/examples/upload", json=upload_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            version = response.json()
            print(f"   Uploaded version: {version['version_tag']} (ID: {version['id']})")
            
            # Test download
            print("\n2. Testing download...")
            response = self.session.get(f"{self.base_url}/examples/download/{version['id']}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                download_data = response.json()
                print(f"   Downloaded {len(download_data['files'])} files:")
                for filename in download_data['files'].keys():
                    print(f"   - {filename}")
                print(f"   Has meta.yaml: {bool(download_data['meta_yaml'])}")
                print(f"   Has test.yaml: {bool(download_data['test_yaml'])}")
                return True
            else:
                print(f"   Download Error: {response.text}")
        else:
            print(f"   Upload Error: {response.text}")
        
        return False
    
    def test_search(self):
        """Test search functionality."""
        print("\n🧪 Testing Search")
        print("=" * 40)
        
        # Search examples
        search_params = {
            "search": "test",
            "limit": 5
        }
        
        response = self.session.get(f"{self.base_url}/examples", params=search_params)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            examples = response.json()
            print(f"   Found {len(examples)} examples matching 'test'")
            for example in examples:
                print(f"   - {example['title']} ({example['identifier']})")
        else:
            print(f"   Error: {response.text}")
    
    def run_all_tests(self):
        """Run all API tests."""
        print("🚀 Starting Examples API Tests")
        print("=" * 50)
        
        try:
            # Test repositories
            repo_id = self.test_repositories()
            if not repo_id:
                print("❌ Repository tests failed, stopping")
                return False
            
            # Test examples
            example_id = self.test_examples(repo_id)
            
            # Test upload/download
            upload_success = self.test_upload_download(repo_id)
            
            # Test search
            self.test_search()
            
            print("\n✅ All tests completed!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print(f"Testing API at: {base_url}")
    
    tester = ExampleAPITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()