#!/usr/bin/env python3
"""
MATLAB Artifact Regenerator

This script finds and re-runs MATLAB tests to generate and store artifacts for existing results.
It does NOT update the Result records - only stores artifacts to MinIO.

Requirements:
- MATLAB engine installed and accessible (unless --list-only or --dry-run)
- Access to PostgreSQL database
- Access to API (for downloading examples/submissions)
- Access to MinIO (for storing artifacts)

Usage:
    # List all MATLAB results (no MATLAB needed)
    python artifact_regenerator.py --env .env --list-only

    # Dry run - show what would be processed
    python artifact_regenerator.py --env .env --dry-run

    # Process results
    python artifact_regenerator.py --env .env --limit 10
    python artifact_regenerator.py --env .env --result-id <uuid>

Environment variables (can be set in .env file):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    API_URL, API_TOKEN
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    MATLAB_TEST_ENGINE_URL, MATLAB_TEST_ENGINE_TOKEN, MATLAB_TEST_ENGINE_VERSION
"""

import argparse
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml
from dotenv import load_dotenv

# Parse arguments first
parser = argparse.ArgumentParser(description="Find and regenerate MATLAB test artifacts")
parser.add_argument("--env", default=".env", help="Path to .env file")
parser.add_argument("--list-only", action="store_true", help="Only list results, don't process them")
parser.add_argument("--csv", default=None, help="CSV file with results (optional, will query DB if not provided)")
parser.add_argument("--export-csv", default=None, help="Export results to CSV file")
parser.add_argument("--result-id", default=None, help="Process single result by ID")
parser.add_argument("--limit", type=int, default=None, help="Limit number of results to process")
parser.add_argument("--offset", type=int, default=0, help="Skip first N results")
parser.add_argument("--dry-run", action="store_true", help="Don't actually run tests or store artifacts")
parser.add_argument("--skip-existing", action="store_true", help="Skip results that already have artifacts in MinIO")
parser.add_argument("--service-slug", default="itpcp.exec.mat", help="MATLAB service slug")
parser.add_argument("--db-host", help="Override POSTGRES_HOST")
parser.add_argument("--db-port", help="Override POSTGRES_PORT")
parser.add_argument("--chunk-size", type=int, default=10, help="Process results in chunks of N (default: 10)")
args = parser.parse_args()

# Load environment
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
env_path = project_root / args.env
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"Warning: {env_path} not found")

import psycopg2
import httpx
from minio import Minio
from minio.error import S3Error


class MatlabArtifactRegenerator:
    """Finds and regenerates artifacts for existing MATLAB test results."""

    def __init__(self):
        self.db_conn = None
        self.minio_client = None
        self.api_base_url = None
        self.api_token = None
        self.matlab_engine = None
        self.test_engine_path = None
        # Cache for downloaded examples: {example_version_id: path}
        self.example_cache = {}
        self.example_cache_dir = None

    def connect_database(self):
        """Connect to PostgreSQL database."""
        host = args.db_host or os.getenv("POSTGRES_HOST", "localhost")
        port = args.db_port or os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        database = os.getenv("POSTGRES_DB", "codeability")

        print(f"Connecting to database: {host}:{port}/{database}")
        self.db_conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        print("  Database connected.")

    def connect_minio(self):
        """Connect to MinIO storage."""
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        if endpoint.startswith("http://"):
            endpoint = endpoint[7:]
        elif endpoint.startswith("https://"):
            endpoint = endpoint[8:]

        access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        print(f"Connecting to MinIO: {endpoint}")
        self.minio_client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        # Ensure results bucket exists
        if not self.minio_client.bucket_exists("results"):
            print("  Creating 'results' bucket...")
            self.minio_client.make_bucket("results")
        print("  MinIO connected.")

    def setup_api(self):
        """Setup API access."""
        self.api_base_url = os.getenv("API_URL", "http://localhost:8000")
        self.api_token = os.getenv("API_TOKEN")

        if not self.api_token:
            print("WARNING: No API_TOKEN set. API calls may fail.")
        print(f"API configured: {self.api_base_url}")

    def setup_matlab(self):
        """Setup MATLAB engine and test environment."""
        import matlab.engine

        # Clone/fetch test engine
        test_engine_url = os.getenv("MATLAB_TEST_ENGINE_URL")
        test_engine_token = os.getenv("MATLAB_TEST_ENGINE_TOKEN")
        test_engine_version = os.getenv("MATLAB_TEST_ENGINE_VERSION", "main")

        if not test_engine_url or not test_engine_token:
            raise ValueError("MATLAB_TEST_ENGINE_URL and MATLAB_TEST_ENGINE_TOKEN must be set")

        self.test_engine_path = os.path.join(tempfile.gettempdir(), "matlab-test-engine")

        print(f"Fetching MATLAB test engine from {test_engine_url}...")
        from computor_types.repositories import Repository
        Repository(
            url=test_engine_url,
            token=test_engine_token,
            branch=test_engine_version
        ).clone_or_fetch(self.test_engine_path)
        print(f"  Test engine ready at: {self.test_engine_path}")

        # Start MATLAB engine
        print("Starting MATLAB engine (this may take a minute)...")
        engines = matlab.engine.find_matlab()
        if engines:
            print(f"  Found existing engine: {engines[0]}")
            self.matlab_engine = matlab.engine.connect_matlab(engines[0])
        else:
            self.matlab_engine = matlab.engine.start_matlab()
            self.matlab_engine.eval("matlab.engine.shareEngine('artifact_regen')", nargout=0)

        # Initialize test environment
        print("  Initializing test environment...")
        init_result = self.matlab_engine.evalc(
            f"clear all; cd ~; run {self.test_engine_path}/initTest.m"
        )
        print(f"  Init result: {init_result[:200]}...")
        print("  MATLAB engine ready.")

    def get_service_info(self, service_slug: str) -> Optional[Dict]:
        """Get service information by slug."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT id, name, slug
            FROM service
            WHERE slug = %s
        """, (service_slug,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return {
            "id": str(row[0]),
            "name": row[1],
            "slug": row[2],
        }

    def list_available_services(self) -> List[Dict]:
        """List all available testing services."""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT slug, name FROM service WHERE slug LIKE '%.exec.%' ORDER BY slug")
        services = [{"slug": row[0], "name": row[1]} for row in cursor.fetchall()]
        cursor.close()
        return services

    def get_matlab_results(self, service_slug: str) -> List[Dict]:
        """Query all finished MATLAB results from database."""
        cursor = self.db_conn.cursor()

        # Get service ID
        service_info = self.get_service_info(service_slug)
        if not service_info:
            raise ValueError(f"Service '{service_slug}' not found")
        service_id = service_info["id"]

        print(f"Found service: {service_info['name']} (ID: {service_id})")

        # Query results - only get the latest result per submission_group
        # This avoids regenerating artifacts for old submissions when a student has submitted multiple times
        cursor.execute("""
            WITH ranked_results AS (
                SELECT
                    r.id,
                    r.submission_artifact_id,
                    r.course_content_id,
                    r.course_member_id,
                    r.version_identifier,
                    r.grade,
                    r.created_at,
                    r.finished_at,
                    r.status,
                    ccd.example_version_id,
                    sa.submission_group_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY sa.submission_group_id
                        ORDER BY r.created_at DESC
                    ) as rn
                FROM result r
                JOIN course_content cc ON r.course_content_id = cc.id
                LEFT JOIN course_content_deployment ccd ON cc.id = ccd.course_content_id AND ccd.deployment_status = 'deployed'
                LEFT JOIN submission_artifact sa ON r.submission_artifact_id = sa.id
                WHERE r.testing_service_id = %s
                  AND r.status = 0
                  AND r.submission_artifact_id IS NOT NULL
            )
            SELECT id, submission_artifact_id, course_content_id, course_member_id,
                   version_identifier, grade, created_at, finished_at, status,
                   example_version_id, submission_group_id
            FROM ranked_results
            WHERE rn = 1
            ORDER BY created_at DESC
        """, (str(service_id),))

        results = []
        for row in cursor.fetchall():
            results.append({
                "result_id": str(row[0]),
                "submission_artifact_id": str(row[1]) if row[1] else None,
                "course_content_id": str(row[2]) if row[2] else None,
                "course_member_id": str(row[3]) if row[3] else None,
                "version_identifier": row[4],
                "grade": row[5],
                "created_at": row[6],
                "finished_at": row[7],
                "status": row[8],
                "example_version_id": str(row[9]) if row[9] else None,
                "submission_group_id": str(row[10]) if row[10] else None,
            })

        cursor.close()
        return results

    def get_single_result(self, result_id: str) -> Optional[Dict]:
        """Get details for a single result."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT
                r.id,
                r.submission_artifact_id,
                r.course_content_id,
                r.course_member_id,
                r.version_identifier,
                r.grade,
                r.created_at,
                r.finished_at,
                r.status,
                ccd.example_version_id,
                sa.submission_group_id
            FROM result r
            JOIN course_content cc ON r.course_content_id = cc.id
            LEFT JOIN course_content_deployment ccd ON cc.id = ccd.course_content_id AND ccd.deployment_status = 'deployed'
            LEFT JOIN submission_artifact sa ON r.submission_artifact_id = sa.id
            WHERE r.id = %s
        """, (result_id,))

        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return {
            "result_id": str(row[0]),
            "submission_artifact_id": str(row[1]) if row[1] else None,
            "course_content_id": str(row[2]) if row[2] else None,
            "course_member_id": str(row[3]) if row[3] else None,
            "version_identifier": row[4],
            "grade": row[5],
            "created_at": row[6],
            "finished_at": row[7],
            "status": row[8],
            "example_version_id": str(row[9]) if row[9] else None,
            "submission_group_id": str(row[10]) if row[10] else None,
        }

    def check_artifacts_exist(self, result_id: str) -> bool:
        """Check if artifacts already exist in MinIO for this result."""
        prefix = f"{result_id}/artifacts/"
        try:
            objects = list(self.minio_client.list_objects("results", prefix=prefix))
            return len(objects) > 0
        except S3Error:
            return False

    def download_example(self, example_version_id: str, target_dir: str) -> str:
        """Download reference example from API (with caching)."""
        # Check cache first
        if example_version_id in self.example_cache:
            cached_path = self.example_cache[example_version_id]
            if os.path.exists(cached_path):
                print(f"      (using cached example)")
                # Copy from cache to target_dir
                example_path = os.path.join(target_dir, "reference")
                shutil.copytree(cached_path, example_path)
                return example_path

        url = f"{self.api_base_url}/examples/download/{example_version_id}"
        params = {"with_dependencies": "true"}
        headers = {"X-API-Token": self.api_token} if self.api_token else {}

        response = httpx.get(url, params=params, headers=headers, timeout=60.0)
        response.raise_for_status()

        data = response.json()

        # Save main example files
        example_path = os.path.join(target_dir, "reference")
        os.makedirs(example_path, exist_ok=True)

        files = data.get("files", {})
        for filename, content in files.items():
            file_path = os.path.join(example_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self._write_file_content(file_path, content)

        # Save dependencies
        for dep in data.get("dependencies", []):
            dep_dir = dep.get("directory", "")
            dep_path = os.path.join(example_path, "dependencies", dep_dir)
            os.makedirs(dep_path, exist_ok=True)

            for filename, content in dep.get("files", {}).items():
                file_path = os.path.join(dep_path, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                self._write_file_content(file_path, content)

        # Store in cache
        if self.example_cache_dir:
            cache_path = os.path.join(self.example_cache_dir, example_version_id)
            shutil.copytree(example_path, cache_path)
            self.example_cache[example_version_id] = cache_path
            print(f"      (cached for reuse)")

        return example_path

    def download_submission(self, artifact_id: str, target_dir: str) -> str:
        """Download student submission from API."""
        url = f"{self.api_base_url}/submissions/artifacts/{artifact_id}/download"
        headers = {"X-API-Token": self.api_token} if self.api_token else {}

        response = httpx.get(url, headers=headers, timeout=60.0)
        response.raise_for_status()

        # Extract ZIP
        submission_path = os.path.join(target_dir, "student")
        os.makedirs(submission_path, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zf:
            zf.extractall(submission_path)

        # Check if ZIP had single directory
        items = os.listdir(submission_path)
        if len(items) == 1 and os.path.isdir(os.path.join(submission_path, items[0])):
            submission_path = os.path.join(submission_path, items[0])

        return submission_path

    def _write_file_content(self, file_path: str, content):
        """Write file content, handling base64 encoding."""
        import base64

        if isinstance(content, dict) and "base64" in content:
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(content["base64"]))
        elif isinstance(content, str):
            if content.startswith('data:') and ';base64,' in content:
                base64_data = content.split(';base64,', 1)[1]
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(base64_data))
            else:
                with open(file_path, 'w') as f:
                    f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)

    def run_matlab_test(self, reference_path: str, student_path: str, work_dir: str) -> Dict:
        """Run MATLAB test and return results."""
        # Setup directories
        artifacts_path = os.path.join(work_dir, "artifacts")
        output_path = os.path.join(work_dir, "output")
        test_files_path = os.path.join(work_dir, "test_files")

        os.makedirs(artifacts_path, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(test_files_path, exist_ok=True)

        # Create specification file
        spec_file_path = os.path.join(work_dir, "specification.yaml")
        spec_data = {
            "executionDirectory": student_path,
            "studentDirectory": student_path,
            "referenceDirectory": reference_path,
            "outputDirectory": output_path,
            "testDirectory": test_files_path,
            "artifactDirectory": artifacts_path,
            "studentTestCounter": 2,
            "storeGraphicsArtifacts": True,
        }

        with open(spec_file_path, 'w') as f:
            yaml.dump(spec_data, f)

        # Copy test files if meta.yaml specifies them
        meta_path = os.path.join(reference_path, "meta.yaml")
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = yaml.safe_load(f) or {}
            test_files = meta.get("properties", {}).get("testFiles", [])
            for tf in test_files:
                src = os.path.join(reference_path, tf)
                dst = os.path.join(test_files_path, tf)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

        # Test file path
        test_file_path = os.path.join(reference_path, "test.yaml")
        if not os.path.exists(test_file_path):
            raise FileNotFoundError(f"test.yaml not found in {reference_path}")

        # Clear workspace and reinitialize test environment before each test
        # This matches what matlab-server.py does in the connect() method
        print("    Clearing workspace and reinitializing test environment...")
        try:
            init_cmd = f"clear all; cd ~; run {self.test_engine_path}/initTest.m"
            self.matlab_engine.evalc(init_cmd)
        except Exception as e:
            print(f"    Warning: Failed to reinitialize: {e}")

        # Run MATLAB test
        command = f"CodeAbilityTestSuite('{test_file_path}','{spec_file_path}')"
        print(f"    Running: {command}")

        try:
            result = self.matlab_engine.evalc(command)
            print(f"    MATLAB output: {result[:500]}...")
        except Exception as e:
            print(f"    MATLAB error: {e}")
            return {"error": str(e), "artifacts_path": artifacts_path}

        # Read test summary if exists
        summary_path = os.path.join(output_path, "testSummary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                test_results = json.load(f)
        else:
            test_results = {"note": "No testSummary.json generated"}

        return {
            "test_results": test_results,
            "artifacts_path": artifacts_path,
            "matlab_output": result[:1000] if result else None,
        }

    def store_artifacts(self, result_id: str, artifacts_path: str) -> int:
        """Store artifacts to MinIO."""
        stored = 0

        if not os.path.exists(artifacts_path):
            return 0

        for root, dirs, files in os.walk(artifacts_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, artifacts_path)
                object_key = f"{result_id}/artifacts/{rel_path}"

                # Guess content type
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = "application/octet-stream"

                # Upload to MinIO
                file_size = os.path.getsize(file_path)
                with open(file_path, 'rb') as f:
                    self.minio_client.put_object(
                        "results",
                        object_key,
                        f,
                        file_size,
                        content_type=content_type,
                    )
                stored += 1
                print(f"      Stored: {rel_path} ({file_size} bytes)")

        return stored

    def process_result(self, result: Dict, dry_run: bool = False) -> Dict:
        """Process a single result: download, test, store artifacts."""
        result_id = result["result_id"]
        print(f"\n  Processing result: {result_id}")
        print(f"    Grade: {result.get('grade')}, Created: {result.get('created_at')}")

        if not result.get("example_version_id"):
            return {"status": "skipped", "reason": "no example_version_id"}

        if not result.get("submission_artifact_id"):
            return {"status": "skipped", "reason": "no submission_artifact_id"}

        if dry_run:
            print("    [DRY RUN] Would process this result")
            return {"status": "dry_run"}

        with tempfile.TemporaryDirectory(prefix=f"matlab_regen_{result_id}_") as work_dir:
            try:
                # Download reference example
                print(f"    Downloading example {result['example_version_id']}...")
                reference_path = self.download_example(
                    result["example_version_id"],
                    work_dir
                )

                # Download student submission
                print(f"    Downloading submission {result['submission_artifact_id']}...")
                student_path = self.download_submission(
                    result["submission_artifact_id"],
                    work_dir
                )

                # Run test
                print("    Running MATLAB test...")
                test_result = self.run_matlab_test(reference_path, student_path, work_dir)

                if "error" in test_result:
                    return {"status": "error", "error": test_result["error"]}

                # Store artifacts
                artifacts_path = test_result["artifacts_path"]
                artifact_files = []
                if os.path.exists(artifacts_path):
                    artifact_files = os.listdir(artifacts_path)

                if artifact_files:
                    print(f"    Storing {len(artifact_files)} artifacts...")
                    stored = self.store_artifacts(result_id, artifacts_path)
                    return {"status": "success", "artifacts_stored": stored}
                else:
                    print("    No artifacts generated")
                    return {"status": "success", "artifacts_stored": 0, "note": "no artifacts generated"}

            except Exception as e:
                print(f"    ERROR: {e}")
                return {"status": "error", "error": str(e)}

    def list_results(self, results: List[Dict]):
        """Display results in a formatted table."""
        print("\n" + "=" * 110)
        print("MATLAB TEST RESULTS")
        print("=" * 110)
        print(f"Total: {len(results)}")
        print("\n" + "-" * 110)
        print(f"{'Result ID':<38} {'Created At':<22} {'Grade':<8} {'Version':<40}")
        print("-" * 110)

        # Show first 50
        for r in results[:50]:
            version_str = str(r.get('version_identifier', 'N/A'))[:40]
            grade = r.get('grade')
            grade_str = f"{grade:.2f}" if grade is not None else 'N/A'
            created = r.get('created_at')
            created_str = str(created)[:22] if created else 'N/A'
            print(f"{r['result_id']:<38} {created_str:<22} {grade_str:<8} {version_str:<40}")

        if len(results) > 50:
            print(f"... and {len(results) - 50} more")

        print("-" * 110)

    def export_to_csv(self, results: List[Dict], csv_path: str):
        """Export results to CSV file."""
        with open(csv_path, "w") as f:
            f.write("result_id,created_at,finished_at,status,grade,version_identifier,")
            f.write("submission_artifact_id,course_member_id,course_content_id,")
            f.write("submission_group_id,example_version_id\n")
            for r in results:
                f.write(f"{r.get('result_id')},{r.get('created_at')},{r.get('finished_at')},")
                f.write(f"{r.get('status')},{r.get('grade')},{r.get('version_identifier')},")
                f.write(f"{r.get('submission_artifact_id')},{r.get('course_member_id')},")
                f.write(f"{r.get('course_content_id')},{r.get('submission_group_id')},")
                f.write(f"{r.get('example_version_id')}\n")
        print(f"\nCSV exported to: {csv_path}")

    def run(self):
        """Main execution."""
        print("=" * 80)
        print("MATLAB Artifact Regenerator")
        print("=" * 80)

        # Connect to database (always needed)
        self.connect_database()

        # Get results to process
        if args.result_id:
            results = [self.get_single_result(args.result_id)]
            if not results[0]:
                print(f"Result {args.result_id} not found")
                return
        elif args.csv:
            csv_path = Path(args.csv)
            if not csv_path.exists():
                print(f"CSV file not found: {csv_path}")
                return
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                results = list(reader)
            print(f"Loaded {len(results)} results from CSV")
        else:
            print(f"\nQuerying MATLAB results (service: {args.service_slug})...")
            service_info = self.get_service_info(args.service_slug)
            if not service_info:
                print(f"ERROR: Service with slug '{args.service_slug}' not found!")
                print("\nAvailable testing services:")
                for svc in self.list_available_services():
                    print(f"  - {svc['slug']}: {svc['name']}")
                self.db_conn.close()
                return
            results = self.get_matlab_results(args.service_slug)

        print(f"Found {len(results)} results")

        # Apply offset and limit
        if args.offset > 0:
            results = results[args.offset:]
            print(f"After offset ({args.offset}): {len(results)} results")
        if args.limit:
            results = results[:args.limit]
            print(f"After limit ({args.limit}): {len(results)} results")

        # List-only mode: just show results and optionally export CSV
        if args.list_only:
            self.list_results(results)
            if args.export_csv:
                self.export_to_csv(results, args.export_csv)
            self.db_conn.close()
            print("\nDone (list-only mode).")
            return

        # Export CSV if requested (even when not list-only)
        if args.export_csv:
            self.export_to_csv(results, args.export_csv)

        # Connect to other services for processing
        self.connect_minio()
        self.setup_api()

        # Initialize example cache directory
        self.example_cache_dir = tempfile.mkdtemp(prefix="matlab_example_cache_")
        print(f"Example cache directory: {self.example_cache_dir}")

        if not args.dry_run:
            self.setup_matlab()

        total_results = len(results)
        chunk_size = args.chunk_size
        total_chunks = (total_results + chunk_size - 1) // chunk_size  # ceiling division

        print(f"\nProcessing {total_results} results in {total_chunks} chunk(s) of {chunk_size}")

        if args.dry_run:
            print("\n*** DRY RUN MODE ***\n")

        # Process results in chunks
        stats = {"success": 0, "skipped": 0, "error": 0}

        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * chunk_size
            chunk_end = min(chunk_start + chunk_size, total_results)
            chunk = results[chunk_start:chunk_end]

            print(f"\n{'='*80}")
            print(f"CHUNK {chunk_idx + 1}/{total_chunks} (results {chunk_start + 1}-{chunk_end} of {total_results})")
            print(f"{'='*80}")

            for i, result in enumerate(chunk):
                global_idx = chunk_start + i
                print(f"\n[{global_idx + 1}/{total_results}]", end="")

                # Skip if artifacts exist and --skip-existing
                if args.skip_existing and self.check_artifacts_exist(result["result_id"]):
                    print(f"  {result['result_id']} - SKIPPED (artifacts exist)")
                    stats["skipped"] += 1
                    continue

                outcome = self.process_result(result, dry_run=args.dry_run)

                if outcome["status"] == "success" or outcome["status"] == "dry_run":
                    stats["success"] += 1
                elif outcome["status"] == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["error"] += 1

            # Chunk summary
            print(f"\n--- Chunk {chunk_idx + 1} complete. Running totals: Success={stats['success']}, Skipped={stats['skipped']}, Errors={stats['error']} ---")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total:    {len(results)}")
        print(f"Success:  {stats['success']}")
        print(f"Skipped:  {stats['skipped']}")
        print(f"Errors:   {stats['error']}")
        print(f"Examples cached: {len(self.example_cache)}")

        # Cleanup
        if self.matlab_engine:
            print("\nShutting down MATLAB engine...")
            # Don't quit - leave it running for potential reuse
            # self.matlab_engine.quit()

        # Cleanup example cache
        if self.example_cache_dir and os.path.exists(self.example_cache_dir):
            shutil.rmtree(self.example_cache_dir, ignore_errors=True)
            print("Example cache cleaned up.")

        self.db_conn.close()
        print("Done.")


if __name__ == "__main__":
    regenerator = MatlabArtifactRegenerator()
    regenerator.run()
