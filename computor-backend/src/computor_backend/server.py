from contextlib import asynccontextmanager
import os
import shutil
from computor_backend.api.filesystem import mirror_db_to_filesystem
from computor_backend.permissions.role_setup import claims_organization_manager, claims_user_manager
from computor_backend.permissions.core import db_apply_roles
from computor_types.tokens import encrypt_api_key
from computor_backend.model.auth import User
from computor_backend.model.execution import ExecutionBackend
from computor_backend.model.role import UserRole
from computor_backend.redis_cache import get_redis_client
from fastapi import Depends, FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from computor_backend.api.api_builder import CrudRouter, LookUpRouter
from computor_backend.api.tests import tests_router
from computor_backend.permissions.auth import get_current_principal
from computor_backend.api.auth import auth_router
from computor_backend.api.sessions import session_router
from computor_backend.plugins.registry import initialize_plugin_registry
from sqlalchemy.orm import Session
from computor_backend.database import get_db

from computor_backend.interfaces import (
    AccountInterface,
    UserInterface,
    CourseFamilyInterface,
    CourseMemberInterface,
    RoleInterface,
    ExampleRepositoryInterface,
    ExecutionBackendInterface,
    GroupInterface,
    SessionInterface,
    SubmissionGroupMemberInterface,
    SubmissionGroupInterface,
    CourseGroupInterface,
    CourseRoleInterface,
    CourseContentTypeInterface,
    CourseContentKindInterface,
    LanguageInterface,
)

from computor_backend.api.course_execution_backend import course_execution_backend_router
from computor_backend.api.courses import course_router
from computor_backend.api.system import system_router
from computor_backend.api.course_contents import course_content_router
from computor_backend.settings import settings 
from computor_backend.api.students import student_router
from computor_backend.api.profiles import profile_router
from computor_backend.api.student_profiles import student_profile_router
from computor_backend.api.results import result_router
from computor_backend.api.tutor import tutor_router
from computor_backend.api.lecturer import lecturer_router
from computor_backend.api.organizations import organization_router
from computor_backend.api.user_roles import user_roles_router
from computor_backend.api.role_claims import role_claim_router
from computor_backend.api.user import user_router
from computor_backend.api.tasks import tasks_router
from computor_backend.api.storage import storage_router
from computor_backend.api.submissions import submissions_router
from computor_backend.api.examples import examples_router
from computor_backend.api.extensions import extensions_router
from computor_backend.api.course_member_comments import router as course_member_comments_router
from computor_backend.api.messages import messages_router
from computor_backend.api.team_management import team_management_router
from computor_backend.exceptions import register_exception_handlers
import json
import tempfile
from pathlib import Path

async def initialize_plugin_registry_with_config():
    """Initialize plugin registry with configuration from settings."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if we should use a custom config file
    if settings.AUTH_PLUGINS_CONFIG:
        config_file = settings.AUTH_PLUGINS_CONFIG
        logger.info(f"Using custom plugin config from: {config_file}")
    else:
        # Create a temporary config based on settings
        config = {}
        
        # Configure Keycloak based on settings
        if settings.ENABLE_KEYCLOAK:
            logger.info("Keycloak authentication is ENABLED")
            config["keycloak"] = {
                "enabled": True,
                "settings": {
                    # These can be overridden by environment variables in KeycloakAuthPlugin
                    "server_url": os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180"),
                    "realm": os.environ.get("KEYCLOAK_REALM", "computor"),
                    "client_id": os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend"),
                    "client_secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", "computor-backend-secret")
                }
            }
        else:
            logger.info("Keycloak authentication is DISABLED")
            config["keycloak"] = {
                "enabled": False
            }
        
        # Write config to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2)
            config_file = f.name
            logger.debug(f"Created temporary plugin config at: {config_file}")
    
    # Initialize registry with the config file
    await initialize_plugin_registry(config_file)
    
    # Clean up temp file if we created one
    if not settings.AUTH_PLUGINS_CONFIG and config_file:
        try:
            Path(config_file).unlink()
            logger.debug("Cleaned up temporary plugin config")
        except:
            pass

async def init_admin_user(db: Session):

    username = os.environ.get("EXECUTION_BACKEND_API_USER")
    password = os.environ.get("EXECUTION_BACKEND_API_PASSWORD")

    admin = db.query(User).filter(User.username == username).first()

    if admin != None:
        return
    
    try:
        admin_user = User(
            given_name="Admin",
            family_name="System",
            username=username,
            password=encrypt_api_key(password)
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        db.add(
            UserRole(
                user_id=admin_user.id,
                role_id="_admin"
            )
        )
        db.commit()

    except:
        print("[CRITICAL BUG] Admin user could not be created. The backend is shutting down.")
        quit(1)

async def startup_logic():

    with next(get_db()) as db:
        db_apply_roles("_user_manager",claims_user_manager(),db)
        db_apply_roles("_organization_manager",claims_organization_manager(),db)

        repo_dirs = os.path.join(settings.API_LOCAL_STORAGE_DIR,"repositories")
        if os.path.exists(repo_dirs):
            shutil.rmtree(repo_dirs)

        await init_admin_user(db)
        await mirror_db_to_filesystem(db)
    
    # Initialize plugin registry with configuration
    # await initialize_plugin_registry_with_config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # redis_client = await get_redis_client()
    # RedisCache(redis_client)

    if settings.DEBUG_MODE == "production":
        await startup_logic()
    # else:
        # Initialize plugin registry in development mode
        # await initialize_plugin_registry_with_config()

    yield

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register custom exception handlers for structured error responses
register_exception_handlers(app)

origins = [
    "http://localhost:3000",  # Next.js frontend
    "http://localhost:3001",  # Alternative frontend port
    "http://localhost:8000",  # Backend (for docs)
]

# Add upload size limiter middleware (should be before CORS)
from computor_backend.middleware import UploadSizeLimiterMiddleware
app.add_middleware(UploadSizeLimiterMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

CrudRouter(UserInterface).register_routes(app)
CrudRouter(AccountInterface).register_routes(app)
CrudRouter(GroupInterface).register_routes(app)
# ProfileInterface and StudentProfileInterface use custom routers for fine-grained permissions
CrudRouter(SessionInterface).register_routes(app)
course_router.register_routes(app)
organization_router.register_routes(app)
CrudRouter(CourseFamilyInterface).register_routes(app)
CrudRouter(CourseGroupInterface).register_routes(app)
CrudRouter(CourseMemberInterface).register_routes(app)
LookUpRouter(CourseRoleInterface).register_routes(app)
LookUpRouter(RoleInterface).register_routes(app)
LookUpRouter(LanguageInterface).register_routes(app)
CrudRouter(ExecutionBackendInterface).register_routes(app)
CrudRouter(ExampleRepositoryInterface).register_routes(app)
# CrudRouter(ExampleInterface).register_routes(app) # Examples should only be created via upload

CrudRouter(SubmissionGroupInterface).register_routes(app)
CrudRouter(SubmissionGroupMemberInterface).register_routes(app)

app.include_router(
    course_execution_backend_router,
    prefix="/course-execution-backends",
    tags=["course execution backends"],
    dependencies=[Depends(get_current_principal)]
)

CrudRouter(CourseContentKindInterface).register_routes(app)
CrudRouter(CourseContentTypeInterface).register_routes(app)

# ProfileInterface and StudentProfileInterface use custom routers (see below)
# CrudRouter(StudentProfileInterface).register_routes(app)
# CrudRouter(ProfileInterface).register_routes(app)

course_content_router.register_routes(app)

app.include_router(result_router)

app.include_router(
    system_router,
    prefix="/system",
    tags=["system"],
    dependencies=[Depends(get_current_principal),Depends(get_redis_client)]
)

app.include_router(
    tests_router,
    prefix="/tests",
    tags=["tests"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    student_router,
    prefix="/students",
    tags=["students"],
    dependencies=[Depends(get_current_principal),Depends(get_redis_client)]
)

app.include_router(
    profile_router,
    prefix="/profiles",
    tags=["profiles"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    student_profile_router,
    prefix="/student-profiles",
    tags=["student-profiles"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    tutor_router,
    prefix="/tutors",
    tags=["tutors"],
    dependencies=[Depends(get_current_principal),Depends(get_redis_client)]
)

app.include_router(
    lecturer_router,
    prefix="/lecturers",
    tags=["lecturers"],
    dependencies=[Depends(get_current_principal),Depends(get_redis_client)]
)

# app.include_router(
#     services_router,
#     prefix="/services",
#     tags=["services"]
# )

app.include_router(
    user_roles_router,
    prefix="/user-roles",
    tags=["user","roles"]
)

app.include_router(
    role_claim_router,
    prefix="/role-claims",
    tags=["roles", "claims"]
)

app.include_router(
    user_router,
    prefix="/user",
    tags=["user", "me"]
)

# app.include_router(
#     info_router,
#     prefix="/info",
#     tags=["info"]
# )

app.include_router(
    tasks_router,
    tags=["tasks"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    team_management_router,
    tags=["team-management"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    auth_router,
    tags=["authentication", "sso"]
)

app.include_router(
    storage_router,
    tags=["storage"],
    dependencies=[Depends(get_current_principal), Depends(get_redis_client)]
)

app.include_router(
    examples_router,
    tags=["examples"],
    dependencies=[Depends(get_current_principal), Depends(get_redis_client)]
)

app.include_router(
    extensions_router,
    tags=["extensions"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    submissions_router,
    tags=["submissions"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    course_member_comments_router,
    prefix="/course-member-comments",
    tags=["course member comments"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    messages_router,
    prefix="/messages",
    tags=["messages"],
    dependencies=[Depends(get_current_principal)]
)

# Session management router
app.include_router(
    session_router,
    tags=["sessions"]
)


@app.head("/", status_code=204)
def get_status_head():
    return
