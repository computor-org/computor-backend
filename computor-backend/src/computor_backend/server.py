from contextlib import asynccontextmanager
import asyncio
import os
from computor_backend.exceptions.exceptions import NotFoundException
from computor_backend.permissions.role_setup import claims_organization_manager, claims_user_manager, claims_workspace_user, claims_workspace_maintainer, claims_git_manager, claims_example_manager
from computor_backend.permissions.core import db_apply_roles
from computor_backend.model.auth import User
from computor_backend.model.role import UserRole
from computor_backend.redis_cache import get_redis_client
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from computor_backend.api.api_builder import CrudRouter, LookUpRouter
from computor_backend.api.tests import tests_router
from computor_backend.permissions.auth import get_current_principal, get_current_principal_optional
from computor_backend.api.auth import auth_router
from computor_backend.api.sessions import session_router
from computor_backend.plugins.registry import initialize_plugin_registry
from sqlalchemy.orm import Session
from computor_backend.database import get_db_session

from computor_backend.interfaces import (
    AccountInterface,
    UserInterface,
    CourseInterface,
    CourseFamilyInterface,
    CourseMemberInterface,
    RoleInterface,
    ExampleRepositoryInterface,
    # ServiceTypeInterface,
    GroupInterface,
    SessionInterface,
    SubmissionGroupMemberInterface,
    SubmissionGroupInterface,
    CourseGroupInterface,
    CourseRoleInterface,
    OrganizationRoleInterface,
    OrganizationMemberInterface,
    CourseFamilyRoleInterface,
    CourseFamilyMemberInterface,
    CourseContentTypeInterface,
    CourseContentKindInterface,
    LanguageInterface,
)

from computor_backend.api.service_type import service_type_router
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
from computor_backend.api.courses import course_router
from computor_backend.api.course_families import course_family_router
from computor_backend.api.user_roles import user_roles_router
from computor_backend.api.role_claims import role_claim_router
from computor_backend.api.user import user_router
from computor_backend.api.user_ban import user_ban_router
from computor_backend.api.tasks import tasks_router
from computor_backend.api.storage import storage_router
from computor_backend.api.submissions import submissions_router
from computor_backend.api.examples import examples_router
from computor_backend.api.extensions import extensions_router
from computor_backend.api.course_member_comments import router as course_member_comments_router
from computor_backend.api.messages import messages_router
from computor_backend.api.services import services_router
from computor_backend.api.api_tokens import api_tokens_router
from computor_backend.api.git_servers import git_servers_router
from computor_backend.api.course_git import course_git_router
from computor_backend.api.course_workspaces import course_workspaces_router
from computor_backend.api.course_deployment import course_deployment_router
from computor_backend.api.course_member_import import course_member_import_router
from computor_backend.api.course_member_gradings import course_member_gradings_router
from computor_backend.api.workspace_roles import workspace_roles_router
from computor_backend.api.maintenance import maintenance_router
from computor_backend.api.update import update_router
from computor_backend.api.invites import invites_router
from computor_backend.api.consent import consent_router
from computor_backend.api.instance import instance_router
from computor_backend.api.accounts import accounts_router
from computor_backend.api.documents import documents_router
from computor_backend.exceptions import register_exception_handlers
from computor_backend.websocket.router import ws_router
from computor_backend.websocket.connection_manager import manager as ws_manager
import json
import tempfile
from pathlib import Path

# Coder integration (now part of computor_backend)
from computor_backend.api.coder import router as coder_api_router


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
        except OSError:
            logger.debug("Failed to remove temporary plugin config %s", config_file, exc_info=True)

async def startup_logic():

    with get_db_session() as db:
        db_apply_roles("_user_manager",claims_user_manager(),db)
        db_apply_roles("_organization_manager",claims_organization_manager(),db)
        db_apply_roles("_example_manager",claims_example_manager(),db)
        db_apply_roles("_workspace_user",claims_workspace_user(),db)
        db_apply_roles("_workspace_maintainer",claims_workspace_maintainer(),db)
        db_apply_roles("_git_manager",claims_git_manager(),db)

    # Initialize plugin registry with configuration (loads Keycloak provider, etc.)
    await initialize_plugin_registry_with_config()

    # If Keycloak is enabled, ensure the bootstrap admin exists (create-or-reset
    # password + add to the 'administrators' group). The computor User row and
    # _admin role follow on first login via the group claim. Non-fatal: retries
    # briefly in case Keycloak is still coming up.
    if settings.ENABLE_KEYCLOAK:
        admin_email = settings.API_ADMIN_EMAIL
        admin_password = settings.API_ADMIN_PASSWORD
        if admin_email and admin_password:
            import asyncio
            from computor_backend.business_logic.auth import ensure_keycloak_admin
            for attempt in range(1, 6):
                try:
                    await ensure_keycloak_admin(admin_email, admin_password)
                    break
                except Exception as e:
                    if attempt == 5:
                        print(f"[STARTUP] Admin provisioning failed after retries (non-fatal): {e}")
                    else:
                        await asyncio.sleep(3)
        else:
            print("[STARTUP] API_ADMIN_EMAIL/API_ADMIN_PASSWORD not set — skipping admin provisioning")

        # Register this deployment's redirect URIs on the Keycloak client so
        # Keycloak accepts both (a) the login callback and (b) the post-logout
        # redirect back to the app root. X-Forwarded-Proto from nginx gives the
        # correct scheme at request time, but the URIs must be pre-registered.
        # Use NEXT_PUBLIC_API_URL (the public domain, set by setup-env.sh) as base.
        # Retries because Keycloak may still be coming up (mirrors admin
        # provisioning above): if this registration is skipped, every login
        # fails with invalid_redirect_uri until the next clean restart.
        api_public_url = os.environ.get("NEXT_PUBLIC_API_URL", "").rstrip("/")
        if api_public_url:
            import asyncio
            from computor_backend.auth.keycloak_admin import KeycloakAdminClient
            from urllib.parse import urlparse
            origin = f"{urlparse(api_public_url).scheme}://{urlparse(api_public_url).netloc}"
            for attempt in range(1, 6):
                try:
                    await KeycloakAdminClient().ensure_client_redirect_uris(
                        redirect_uris=[
                            f"{api_public_url}/auth/keycloak/callback",  # SSO login callback
                            f"{origin}/",                                # post-logout redirect target
                        ],
                        web_origins=[origin],
                    )
                    break
                except Exception as e:
                    if attempt == 5:
                        print(f"[STARTUP] Keycloak redirect URI registration failed after retries (non-fatal): {e}")
                    else:
                        await asyncio.sleep(3)

        # If Forgejo is the git server, reconcile the 'forgejo' Keycloak client's
        # redirect URI to the current public FORGEJO_ROOT_URL. The client itself is
        # declared in the realm import with its scopes and a localhost dev callback,
        # but the realm is imported only on Keycloak's first boot and can't know the
        # public domain — so the prod callback is added here on every startup (the
        # same pattern the backend client uses). Best-effort and idempotent.
        forgejo_root = os.environ.get("FORGEJO_ROOT_URL", "").rstrip("/")
        if os.environ.get("GIT_SERVER") == "forgejo" and forgejo_root:
            import asyncio
            from computor_backend.auth.keycloak_admin import KeycloakAdminClient
            for attempt in range(1, 6):
                try:
                    await KeycloakAdminClient().ensure_client_redirect_uris(
                        redirect_uris=[f"{forgejo_root}/user/oauth2/Keycloak/callback"],
                        web_origins=[],  # forgejo client uses webOrigins=["+"] — leave as is
                        client_id="forgejo",
                    )
                    break
                except Exception as e:
                    if attempt == 5:
                        print(f"[STARTUP] Forgejo Keycloak redirect URI reconcile failed after retries (non-fatal): {e}")
                    else:
                        await asyncio.sleep(3)

    # Register the managed Forgejo in the git-server registry so it is offered
    # when creating courses (mints the service token on first run). Independent
    # of Keycloak; best-effort + idempotent; off-thread since it does sync HTTP.
    if os.environ.get("GIT_SERVER") == "forgejo":
        import asyncio
        from computor_backend.business_logic.git_registry import ensure_managed_forgejo_registered
        try:
            await asyncio.to_thread(ensure_managed_forgejo_registered)
        except Exception as e:
            print(f"[STARTUP] Managed Forgejo registry seeding failed (non-fatal): {e}")

    # Apply bootstrap deployments (data/deployments/*): seed the default testing
    # worker Service + its predefined token idempotently, so courses can run tests
    # out of the box. Best-effort + off-thread (sync DB work).
    from computor_backend.business_logic.bootstrap import ensure_bootstrap_services
    try:
        await asyncio.to_thread(ensure_bootstrap_services)
    except Exception as e:
        print(f"[STARTUP] Bootstrap services seeding failed (non-fatal): {e}")

    # Publish privacy notices from data/consent/* idempotently (write-once), so a
    # fresh system comes up with its consent notice already in force. Awaited
    # directly (not off-thread): publishing uploads Markdown to MinIO via async
    # storage. Best-effort; never blocks startup. Disable with
    # CONSENT_BOOTSTRAP_ENABLED=false to keep publishing an explicit CLI/UI action.
    from computor_backend.business_logic.bootstrap import ensure_bootstrap_policies
    try:
        await ensure_bootstrap_policies()
    except Exception as e:
        print(f"[STARTUP] Bootstrap policies seeding failed (non-fatal): {e}")

    # If Coder is enabled, wait for it and ensure admin user exists
    if os.environ.get("CODER_ENABLED", "false").lower() in ("true", "1"):
        from computor_backend.coder.client import CoderClient
        from computor_backend.coder.config import get_coder_settings

        coder_settings = get_coder_settings()
        client = CoderClient(coder_settings)
        try:
            result = await client.ensure_initial_admin(
                username=os.environ.get("CODER_ADMIN_USERNAME", "admin"),
                email=coder_settings.admin_email,
                password=coder_settings.admin_password,
            )

            if not result:
                print("[STARTUP] Coder admin setup failed — Coder features will be unavailable")
                print("[STARTUP]   Check Coder server logs and .env credentials")
            else:
                # Check if templates exist in Coder — if not, auto-push them
                try:
                    templates = await client.list_templates()
                    if not templates:
                        print("[STARTUP] No Coder templates found — submitting build+push workflow")
                        from computor_backend.api.coder import _build_template_parameters
                        from computor_backend.tasks import get_task_executor, TaskSubmission

                        params = _build_template_parameters(coder_settings)
                        params["templates"] = None  # all templates
                        params["build_images"] = True

                        executor = get_task_executor()
                        running_tasks = await executor.list_tasks(limit=1000, status="STARTED")
                        template_push_running = any(
                            task.get("task_name") == "push_coder_templates"
                            for task in running_tasks.get("tasks", [])
                        )
                        if template_push_running:
                            print(
                                "[STARTUP] Template build+push already running — "
                                "skipping duplicate submission"
                            )
                        else:
                            workflow_id = await executor.submit_task(TaskSubmission(
                                task_name="push_coder_templates",
                                parameters=params,
                                queue="coder-tasks",
                            ))
                            print(f"[STARTUP] Template build+push workflow submitted: {workflow_id}")
                    else:
                        print(f"[STARTUP] Coder has {len(templates)} template(s) — skipping auto-push")
                except Exception as e:
                    # Non-fatal — templates can be pushed manually via API
                    print(f"[STARTUP] Template check/push failed (non-fatal): {e}")
        except Exception as e:
            print(f"[STARTUP] Coder initialization failed (non-fatal): {e}")
            print("[STARTUP]   Server will start without Coder — workspace features unavailable")
        finally:
            await client.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from computor_backend.maintenance_scheduler import MaintenanceReminderScheduler

    await startup_logic()

    # Start WebSocket connection manager
    await ws_manager.start()

    # Start maintenance reminder scheduler (depends on pub/sub from ws_manager)
    maintenance_scheduler = MaintenanceReminderScheduler()
    await maintenance_scheduler.start()

    yield

    # Stop maintenance reminder scheduler
    await maintenance_scheduler.stop()

    # Stop WebSocket connection manager
    await ws_manager.stop()


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

# Middleware order (last added = outermost = runs first):
# 1. CORS (outermost) - ensures CORS headers on all responses including 503/403
# 2. Maintenance - blocks non-GET for non-admins during maintenance
# 3. Consent gate - 403 consent_required for authenticated users without
#    current GDPR consent. Auth in this app is a per-route dependency, so the
#    gate resolves the user itself from the Redis principal/session caches
#    (see middleware/consent.py); it must only run inside CORS so blocked
#    responses carry CORS headers.
# 4. Upload size limiter (innermost) - enforces body size limits
from computor_backend.middleware import UploadSizeLimiterMiddleware, MaintenanceMiddleware, ConsentGateMiddleware
app.add_middleware(UploadSizeLimiterMiddleware)
app.add_middleware(ConsentGateMiddleware)
app.add_middleware(MaintenanceMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition is not CORS-safelisted: without it the browser can
    # read a download's bytes but not the filename the backend chose.
    expose_headers=["X-Total-Count", "Content-Disposition"],
)

def _guard_no_archive_admin(entity, permissions, db):
    """Prevent archiving a user who holds the _admin role."""
    from computor_backend.model.role import UserRole
    from computor_backend.exceptions import ForbiddenException
    is_admin_target = db.query(UserRole).filter(
        UserRole.user_id == entity.id,
        UserRole.role_id == "_admin",
    ).first() is not None
    if is_admin_target:
        raise ForbiddenException(detail="Admin users cannot be archived")

_user_router = CrudRouter(UserInterface)
_user_router.pre_archive.append(_guard_no_archive_admin)
_user_router.register_routes(app)
# Ban / unban lifecycle endpoints (PATCH /users/{id}/ban|unban). Distinct paths
# from the CrudRouter, gated on admin / _user_manager inside the handlers.
app.include_router(user_ban_router, tags=["users", "admin"])
# accounts_router must be registered before CrudRouter(AccountInterface) so that
# GET /accounts/providers is matched before the authenticated GET /accounts/{id} route.
app.include_router(accounts_router, tags=["accounts"])
CrudRouter(AccountInterface).register_routes(app)
CrudRouter(GroupInterface).register_routes(app)
# ProfileInterface and StudentProfileInterface use custom routers for fine-grained permissions
CrudRouter(SessionInterface).register_routes(app)
course_router.register_routes(app)
organization_router.register_routes(app)
course_family_router.register_routes(app)
CrudRouter(CourseGroupInterface).register_routes(app)
from computor_backend.interfaces.course_member import guard_course_member_delete
_course_member_router = CrudRouter(CourseMemberInterface)
_course_member_router.pre_delete.append(guard_course_member_delete)
_course_member_router.register_routes(app)
LookUpRouter(CourseRoleInterface).register_routes(app)
LookUpRouter(OrganizationRoleInterface).register_routes(app)
LookUpRouter(CourseFamilyRoleInterface).register_routes(app)
CrudRouter(OrganizationMemberInterface).register_routes(app)
CrudRouter(CourseFamilyMemberInterface).register_routes(app)
LookUpRouter(RoleInterface).register_routes(app)
LookUpRouter(LanguageInterface).register_routes(app)
CrudRouter(ExampleRepositoryInterface).register_routes(app)
# CrudRouter(ExampleInterface).register_routes(app) # Examples should only be created via upload

CrudRouter(SubmissionGroupInterface).register_routes(app)
CrudRouter(SubmissionGroupMemberInterface).register_routes(app)

# Service Types - replaced ExecutionBackend
app.include_router(
    service_type_router,
    prefix="/service-types",
    tags=["service types"],
    dependencies=[Depends(get_current_principal)]
)

CrudRouter(CourseContentKindInterface).register_routes(app)
CrudRouter(CourseContentTypeInterface).register_routes(app)

course_content_router.register_routes(app)

app.include_router(result_router)

app.include_router(
    system_router,
    prefix="/system",
    tags=["system"],
    dependencies=[Depends(get_current_principal),Depends(get_redis_client)]
)

app.include_router(
    maintenance_router,
    prefix="/system/maintenance",
    tags=["system", "maintenance"],
    dependencies=[Depends(get_current_principal), Depends(get_redis_client)]
)

app.include_router(
    update_router,
    prefix="/system/update",
    tags=["system", "update"],
    dependencies=[Depends(get_current_principal), Depends(get_redis_client)]
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

app.include_router(
    documents_router,
    dependencies=[Depends(get_current_principal)],
)

app.include_router(
    user_roles_router,
    prefix="/user-roles",
    # First tag drives the generated client class name — keep it distinct from
    # the "user" tag (/user endpoints) so codegen emits UserRolesClient rather
    # than colliding on UserClient and overwriting the /user methods.
    tags=["user-roles"]
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

app.include_router(
    services_router,
    prefix="/service-accounts",
    tags=["services", "admin"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    api_tokens_router,
    prefix="/api-tokens",
    tags=["tokens", "authentication"],
    dependencies=[Depends(get_current_principal)]
)

# Course-level git: server registry (admin/_organization_manager) and the
# lecturer-facing per-course binding. Auth is enforced per-endpoint.
app.include_router(git_servers_router, tags=["git-servers"])
app.include_router(course_git_router, tags=["course-git"])
# Unconditional (not inside the CODER_ENABLED block): the course-template
# association is meaningful config even while the Coder integration is off;
# the student-workspace routes fail via the client when Coder is down.
app.include_router(course_workspaces_router, tags=["course-workspaces"])
# Single-course deploy from an uploaded course_deployment.yaml (web create page).
app.include_router(course_deployment_router, tags=["course-deployment"])

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
    course_member_import_router,
    tags=["course-member-import", "bulk-operations"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    course_member_gradings_router,
    prefix="/course-member-gradings",
    tags=["course-member-gradings", "progress"],
    dependencies=[Depends(get_current_principal)]
)

app.include_router(
    auth_router,
    tags=["authentication", "sso"]
)

app.include_router(
    invites_router,
    tags=["invites", "user-management"]
)

# GDPR consent gate endpoints. Whitelisted in ConsentGateMiddleware — they must
# be reachable by authenticated-but-unconsented users.
app.include_router(
    consent_router,
    prefix="/consent",
    tags=["consent", "gdpr"]
)

# Public instance navigation URLs (web app + managed Forgejo). Also whitelisted
# in ConsentGateMiddleware so a consent-blocked client can discover where to
# accept the privacy policy.
app.include_router(
    instance_router,
    tags=["instance"]
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
    tags=["extensions"]
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

# WebSocket router (authentication handled internally)
app.include_router(
    ws_router,
    tags=["websocket"]
)

# Coder workspace role management
app.include_router(
    workspace_roles_router,
    prefix="/workspaces/roles",
    tags=["workspaces", "roles"],
    dependencies=[Depends(get_current_principal)],
)

# Coder integration API (only registered when CODER_ENABLED=true)
if os.environ.get("CODER_ENABLED", "false").lower() in ("true", "1"):
    app.include_router(coder_api_router)


@app.head("/", status_code=204)
def get_status_head():
    return

@app.get(
    "/extensions-public",
    response_model=str,
)
async def get_public_extension_url():
    """Public endpoint to get extension download URL.

    This endpoint requires no authentication and returns the URL
    specified in the EXTENSION_PUBLIC_DOWNLOAD_URL environment variable.
    """
    download_link = os.environ.get("EXTENSION_PUBLIC_DOWNLOAD_URL", None)
    if not download_link:
        raise NotFoundException(detail="Public extension download URL not configured")

    return download_link

@app.get(
    "/extensions-getting-started",
    response_model=str,
)
async def get_getting_started_url():
    """Public endpoint to get extension getting started guide URL.

    This endpoint requires no authentication and returns the URL
    specified in the EXTENSION_GETTING_STARTED_URL environment variable.
    """
    getting_started_link = os.environ.get("EXTENSION_GETTING_STARTED_URL", None)
    if not getting_started_link:
        raise NotFoundException(detail="Extension getting started guide URL not configured")

    return getting_started_link
