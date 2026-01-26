# MATLAB Artifact Regeneration Scripts

This directory contains scripts and Docker configuration to regenerate artifacts for existing MATLAB test results.

## Background

The `temporal-worker-matlab` service was missing MinIO environment variables, causing the `store_test_artifacts` function to fail silently. Tests completed successfully and results were stored in the database, but artifacts (plots, figures, etc.) were never uploaded to MinIO.

This tool re-runs the MATLAB tests for those results and stores the generated artifacts.

## Files

| File | Description |
|------|-------------|
| `artifact_regenerator.py` | Main Python script that finds and regenerates artifacts |
| `Dockerfile` | Docker image based on MATLAB worker |
| `docker-compose.yaml` | Docker Compose for easy execution |

## Prerequisites

### 1. Fix the docker-compose files (for future tests)

Add these environment variables to `temporal-worker-matlab` in both `docker-compose-dev.yaml` and `docker-compose-prod.yaml`:

```yaml
- MINIO_ENDPOINT=minio:9000
- MINIO_ACCESS_KEY=${MINIO_ROOT_USER:-minioadmin}
- MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD:-minioadmin}
- MINIO_SECURE=false
```

### 2. Required Environment Variables

The regenerator needs these environment variables (set in `.env` or passed directly):

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# API
API_URL=http://localhost:8000
API_TOKEN=your_api_token  # Token with access to download examples/submissions

# MATLAB Test Engine (GitLab repository)
MATLAB_TEST_ENGINE_URL=https://gitlab.example.com/your/test-engine.git
MATLAB_TEST_ENGINE_TOKEN=your_gitlab_token
MATLAB_TEST_ENGINE_VERSION=main

# MATLAB License (for Docker)
MATLAB_MLM_LICENSE_FILE=port@license-server
```

## Usage

### List results (no MATLAB required)

```bash
# List all MATLAB results
python artifact_regenerator.py --env .env --list-only

# List and export to CSV
python artifact_regenerator.py --env .env --list-only --export-csv results.csv
```

### Dry run (no MATLAB required)

```bash
# See what would be processed without actually running tests
python artifact_regenerator.py --env .env --dry-run --limit 10
```

### Process results

```bash
# Process first 10 results
python artifact_regenerator.py --env .env --limit 10

# Process a specific result
python artifact_regenerator.py --env .env --result-id <uuid>

# Process results, skipping those that already have artifacts
python artifact_regenerator.py --env .env --skip-existing

# Process results 100-200 (pagination)
python artifact_regenerator.py --env .env --offset 100 --limit 100
```

### Docker Compose (Recommended for full processing)

```bash
# From project root directory

# First, make sure the main services are running
docker-compose -f docker-compose-dev.yaml up -d

# List results (no MATLAB needed)
docker-compose -f scripts/rerun-matlab-tests/docker-compose.yaml run --rm regenerator --list-only

# Dry run
docker-compose -f scripts/rerun-matlab-tests/docker-compose.yaml run --rm regenerator --dry-run --limit 10

# Process first 10 results
docker-compose -f scripts/rerun-matlab-tests/docker-compose.yaml run --rm regenerator --limit 10

# Process a specific result
docker-compose -f scripts/rerun-matlab-tests/docker-compose.yaml run --rm regenerator --result-id <uuid>
```

## Command Line Options

```
usage: artifact_regenerator.py [-h] [--env ENV] [--list-only] [--csv CSV]
                                [--export-csv FILE] [--result-id ID]
                                [--limit N] [--offset N] [--dry-run]
                                [--skip-existing] [--service-slug SLUG]

Options:
  --env ENV             Path to .env file (default: .env)
  --list-only           Only list results, don't process them (no MATLAB needed)
  --csv CSV             Load results from CSV file instead of querying DB
  --export-csv FILE     Export results to CSV file
  --result-id ID        Process single result by ID
  --limit N             Limit number of results to process
  --offset N            Skip first N results
  --dry-run             Don't run tests or store artifacts (no MATLAB needed)
  --skip-existing       Skip results that already have artifacts in MinIO
  --service-slug SLUG   MATLAB service slug (default: itpcp.exec.mat)
```

## How It Works

For each result, the regenerator:

1. **Queries the database** to get result details (example_version_id, submission_artifact_id)
2. **Downloads the reference example** from the API (`/examples/download/{id}`)
3. **Downloads the student submission** from the API (`/submissions/artifacts/{id}/download`)
4. **Creates a specification.yaml** file with `artifactDirectory` pointing to a temp folder
5. **Runs the MATLAB test** via `CodeAbilityTestSuite(test.yaml, specification.yaml)`
6. **Uploads generated artifacts** to MinIO at `results/{result_id}/artifacts/`

**Important:** This does NOT modify the Result record in the database. The original grade and status are preserved.

## Troubleshooting

### "Service 'itpcp.exec.mat' not found"

The MATLAB service slug may be different in your deployment. Use `--list-only` to see available services:

```bash
python artifact_regenerator.py --env .env --list-only
```

Or query the database:

```sql
SELECT slug, name FROM service WHERE slug LIKE '%.exec.%';
```

### "No example_version_id found"

The result's course content may not have an active deployment. Check:

```sql
SELECT r.id, cc.name, d.example_version_id
FROM result r
JOIN course_content cc ON r.course_content_id = cc.id
LEFT JOIN deployment d ON cc.id = d.course_content_id AND d.is_active = true
WHERE r.id = '<result-id>';
```

### MATLAB engine startup issues

- Ensure MATLAB license is configured correctly
- Check `MLM_LICENSE_FILE` environment variable
- The first run may take 1-2 minutes to start MATLAB

### Network issues in Docker

If using Docker and can't reach services:

```bash
# Check the network name
docker network ls

# Update docker-compose.yaml with correct network name
# Or use host networking:
docker run --network host ...
```

## Performance Notes

- MATLAB engine startup takes ~60 seconds
- Each test takes 5-30 seconds depending on complexity
- The engine is reused across tests (not restarted)
- Consider using `--limit` and `--offset` for large batches
- Run during off-peak hours to avoid impacting production
