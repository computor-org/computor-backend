# Computor System Architecture Overview

## Backend (src/ctutor_backend)
- **Entry Points**: `src/server.py` starts a FastAPI app and runs `startup_logic()` from `ctutor_backend.server`; `src/cli.py` exposes a rich CLI (`ctutor_backend.cli`).
- **Runtime Configuration**: `ctutor_backend.settings.BackendSettings` reads environment flags (debug mode, storage roots, auth plugin config). Database (`ctutor_backend.database`) builds a pooled SQLAlchemy engine from PostgreSQL env vars, and `redis_cache.py` configures an aiocache Redis client.
- **FastAPI Application**: `ctutor_backend/server.py` wires routers via helper builders (`CrudRouter`, `LookUpRouter`). Routes cover users, organizations, courses, course content, submissions, results, storage, messaging, tasks, SSO, etc. Startup seeds admin accounts, mirrors Git-backed content to local storage, and (optionally) initializes auth plugins.
- **Domain Models & DTOs**: SQLAlchemy models live under `model/`. Each resource exposes a matching Pydantic interface in `interface/` (e.g. `CourseInterface`, `UserInterface`). These interfaces declare endpoint names, CRUD schemas, filters, and post-processing hooks consumed by the router builders.
- **Permissions & Roles**: `permissions/` describes claims, role assignment bootstrapping, auth dependencies (`get_current_principal`), and role claim management. Roles are applied on startup with `db_apply_roles`, and request handlers rely on dependency-injected `Principal` objects.
- **Storage & Integrations**: `minio_client.py` and `services/storage_service.py` wrap MinIO for object storage. `api/filesystem.py` manages repository mirroring (currently mostly stubbed). GitLab helpers (`gitlab_utils.py`, `generator/git_helper.py`) and deployment interfaces orchestrate course repositories.
- **Async Tasks**: `tasks/` integrates with Temporal (`temporal_client.py`, `temporal_*` workflows). `api/tasks.py` exposes control endpoints that delegate to a task executor registry.
- **Plugins & Auth**: `plugins/registry.py` loads authentication plugins (built-in Keycloak provider under `auth/`). Configuration is file-driven, with temporary configs generated from env when none supplied.
- **Services & Utilities**: `services/` exposes Git, storage, deployment sync, and version resolution helpers. `repositories/` implements persistence helpers beyond CRUD. `utils/`, `helpers.py`, and `custom_types/` centralize shared helpers (validation, enums, typed dictionaries).
- **Testing & Tooling**: `tests/` contains backend tests; `testing/` and `manual_testing.py` host manual scenarios. `cli/` provides scripts for type generation, releases, imports, and Temporal workers.

## Shared Defaults (src/defaults)
- Contains pre-seeded deployment templates (`defaults/deployments/...`) used when provisioning assignments, documents, submissions, and student workspaces.

## Frontend (frontend/)
- **Tech Stack**: React 19 with TypeScript, React Router, MUI 6, React Query, TanStack Table, React Hook Form, Redux Toolkit, Recharts. Scripts managed via CRA (`react-scripts`).
- **App Structure**: `App.tsx` hosts routing, top bar, and authenticated layout. Context providers (`hooks/useAuth`, `hooks/useSidebar`) manage auth state (SSO, Basic Auth, mock fallback) and navigation context.
- **Pages**: `pages/` contains dashboards, admin views (courses, users, organizations, tasks, roles, examples), and debug utilities. Each page consumes domain hooks/services to fetch backend data and drive UI components.
- **Components & Hooks**: `components/` implements navigation (sidebar), modals (SSO login), tables, forms, etc. `hooks/` encapsulate auth, sidebar state, data fetching helpers. `services/` wraps HTTP clients for auth, tasks, and domain endpoints, typically aligning with backend routes.
- **API Layer**: `api/` and `types/` define request helpers, Axios clients, and TypeScript types mirroring backend DTOs. `utils/` centralizes formatting, permission checking, and error handling.
- **Styling & Theming**: `styles/` includes global theme configuration and layout helpers for the MUI design system.

## Observations & Notable Behaviors
- Startup relies on environment variables for database, Redis, MinIO, Temporal, and auth; missing secrets (e.g. `TOKEN_SECRET`) impact token encryption utilities.
- Automated CRUD routing heavily depends on interface definitions staying in sync with SQLAlchemy models; cross-module coupling is high but deliberate.
- Repository mirroring groundwork exists but is partially commented out; expect additional implementation before relying on filesystem exports.
- Temporal task integration is a first-class concept—task APIs assume a running Temporal cluster and registered workflows in `tasks/temporal_*` modules.
- Frontend authentication supports multiple strategies (SSO, Basic, mock) and persists selection via dedicated service classes with `localStorage` coordination.

## Next Steps
- Validate this map with team SMEs and extend documentation with sequence diagrams once refactor plans stabilize.
- Coordinate frontend refactor requirements with backend contract expectations before modifying shared DTOs or endpoints.
