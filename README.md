# Computor Server
## Getting started

Required for development
* psql (Postgres 16)
  * On MacOS, if `psql` is not available after install, do `brew link postgresql@16`
* docker, docker-compose
  * Windows: Docker Desktop (makes `docker` command available also in WSL)
  * MacOS: OrbStack
  * Linux: Docker
* python 3.10
* git
  * Be sure to set your name and email in git!

Clone the repos
```bash
git clone git@github.com:computor-org/computor-fullstack.git
```

Setup a virtual environment on Python 3.10 with
```bash
deactivate
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
```

Make sure that Docker (or orbstack on MacOS) are running. Start the development environment with
```bash
bash startup.sh
```

You can also pass additional docker-compose arguments:
```bash
# Rebuild containers
bash startup.sh dev --build

# Production mode with rebuild
bash startup.sh prod --build

# Force recreate containers
bash startup.sh dev --build --force-recreate
```

This will start all services, except the Python FastAPI. This Python service already needs an existing database. For development this process is done manually.

Be sure that the local PostgreSQL server is disabled, so the one exposed by Docker is used! E.g. on Ubuntu
```
sudo systemctl stop postgresql
sudo systemctl disable postgresql
```

Start the migration with
```bash
bash migrations.sh
```


Start
```bash
bash migrations.sh
```
to migrate the schema to the current version.

Start the server with
```
bash api.sh
```
Check if the server is running API docs on http://0.0.0.0:8000/docs .

Install the CLI with
```bash
pip install -e src
```

Start the CLI with
```bash
computor
```
and see if it runs.
## Creating a Course
You find the course definition template in `docs/course.yaml`. To create a course, you need a gitlab group. Add the relevant group members. The system will need API tokens with `owner` privileges. Now create a group access token with role `owner` and access to

* api
* read_repository
* write_repository
* create_runner
* manage_runner

Make a copy of `docs/course.yaml` and edit it. Be **careful** not to put dashes, numbers alone, or any special characters into any fields.

* Set `organization.gitlab.parent` to the parent group ID in gitlab. Set your organization and course family name.
* Set `course.executionBackends.slug` to `itp-python`.

If you have access to an already existing course, you can create a new course from the assignments repository with

* Set `course.source.url` to `https://gitlab.com/.../assignments.git`
* Create a read access token for the source repository and copy it to `course.source.token`.


Login with

```bash
computor login
Auth method (basic, gitlab, github): basic
API url: http://localhost:8000
Username: admin
Password: admin
```
These are the defaults in the template `.env`

Create the course with

```bash
computor apply -f course.yaml -d true
```

Get the course ID with

```bash
computor rest list -t courses
```

Copy `docs/users.csv`, keep the header line and add your own GitLab user with role `_maintainer` (with an underline). You can retrieve your GitLab username by clicking your profile picture. Then run

```bash
computor import users -f users.csv -c <course_id>
```

Don't forget to stop the services with CTRL+C !

## Task Queue System (Temporal)

The Computor platform uses Temporal.io for managing long-running workflows and asynchronous operations. Temporal provides durable workflow execution with automatic retries and state persistence.

### Starting Temporal Services

Temporal services are included in the Docker Compose setup:

```bash
# Development mode (includes Temporal server, UI, and workers)
bash startup.sh dev

# Access Temporal UI
open http://localhost:8088
```

### Running Task Workers

Task workers process workflows from different queues:

```bash
# Start a worker (processes all queues by default)
ctutor worker start

# Start worker for specific queue
ctutor worker start --queues=computor-tasks

# Check worker status
ctutor worker status

# Submit a test task
ctutor worker test-job example_long_running --params='{"duration": 10}' --wait
```

### Workflow Types

The system includes several example workflows:

- **example_long_running**: Simulates long-running operations
- **example_data_processing**: Processes data in chunks  
- **example_error_handling**: Demonstrates error handling and retries
- **student_testing**: Executes student code tests
- **release_students**: GitLab student release operations
- **create_organization/course_family/course**: Hierarchy creation with GitLab

### Custom Queues

Workflows can define their own task queues for better organization:

```python
@workflow.defn(name="my_workflow")
class MyWorkflow(BaseWorkflow):
    @classmethod
    def get_task_queue(cls) -> str:
        return "my-custom-queue"  # Custom queue name
```

## Testing

Run the test suite with:

```bash
# Run all tests
bash test.sh

# Run specific test files
python -m pytest src/computor_backend/tests/test_temporal_client.py -v
python -m pytest src/computor_backend/tests/test_temporal_executor.py -v
python -m pytest src/computor_backend/tests/test_temporal_workflows.py -v

# Run integration tests (requires Temporal server)
SKIP_TEMPORAL_TESTS=false python -m pytest src/computor_backend/tests/test_temporal_integration.py -v
```

### Test Coverage

The Temporal implementation includes comprehensive tests:

- **test_temporal_client.py**: Tests for Temporal client configuration and connection management
- **test_temporal_executor.py**: Tests for task submission, status tracking, and result retrieval
- **test_temporal_workflows.py**: Tests for workflow implementations and activities
- **test_temporal_integration.py**: End-to-end integration tests (requires running Temporal server)

## API Endpoints

Task management endpoints are available at:

- `POST /tasks/submit` - Submit a new workflow
- `GET /tasks/{task_id}` - Get workflow status  
- `GET /tasks/{task_id}/result` - Get workflow result
- `DELETE /tasks/{task_id}` - Returns 501 (Temporal doesn't support deletion)
- `GET /tasks/types` - List available workflow types
- `GET /tasks/workers/status` - Check worker status

## Monitoring

Monitor workflows and workers through:

- **Temporal UI**: http://localhost:8088 - Visual workflow history and debugging
- **API Status**: `ctutor worker status` - Command line worker status
- **Task List UI**: http://localhost:3000/admin/tasks - React frontend for task management
