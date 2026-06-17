"""
Service layer for business logic and external integrations.
"""

__all__ = ["GitService", "StorageService", "get_storage_service"]


def __getattr__(name):
    if name == "GitService":
        from .git_service import GitService
        return GitService
    if name in {"StorageService", "get_storage_service"}:
        from .storage_service import StorageService, get_storage_service
        return {
            "StorageService": StorageService,
            "get_storage_service": get_storage_service,
        }[name]
    raise AttributeError(name)
