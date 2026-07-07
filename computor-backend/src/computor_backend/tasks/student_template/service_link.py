"""Legacy testing-service fallback linking for a course content.

When the slug→service.id resolution didn't populate ``testing_service_id``,
derive the language from the ExampleVersion's typed ``execution_backend``
column (or the ``properties.serviceType`` in the meta.yaml already present
in ``files``) and link the matching enabled Service.
"""
import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_LEGACY_LANGUAGE_MAPPING = {
    'py': 'python',
    'python': 'python',
    'matlab': 'matlab',
    'mat': 'matlab',
}


def _language_from_meta(files: Optional[Dict[str, bytes]]) -> Optional[str]:
    """Language from ``properties.serviceType`` in meta.yaml (new path)."""
    meta_yaml_bytes = files.get('meta.yaml') if files else None
    if not meta_yaml_bytes:
        return None
    import yaml as _yaml
    try:
        meta_data = _yaml.safe_load(meta_yaml_bytes) or {}
    except Exception:
        meta_data = {}
    props = meta_data.get('properties') if isinstance(meta_data.get('properties'), dict) else {}
    service_type_spec = props.get('serviceType') or props.get('service_type')
    if service_type_spec and isinstance(service_type_spec, str) and service_type_spec.startswith('testing.'):
        # e.g., "testing.python" -> "python"
        return service_type_spec.split('.')[-1]
    return None


def _language_from_backend(example_version) -> Optional[str]:
    """Language from the legacy executionBackend.slug suffix."""
    execution_backend = example_version.execution_backend
    backend_slug = execution_backend.get('slug') if isinstance(execution_backend, dict) else None
    if not backend_slug:
        return None
    backend_type = backend_slug.split('.')[-1] if '.' in backend_slug else backend_slug
    return _LEGACY_LANGUAGE_MAPPING.get(backend_type)


def link_testing_service(db: Session, content, files: Optional[Dict[str, bytes]]) -> None:
    """Best-effort link of a testing service to ``content`` by language.

    No-op when the content already has a testing service or no example
    version. Never raises — logs and returns on failure.
    """
    if content.testing_service_id or not content.deployment.example_version:
        return

    try:
        ev = content.deployment.example_version
        language = _language_from_meta(files) or _language_from_backend(ev)
        if not language:
            return

        from sqlalchemy_utils import Ltree
        from ...model.service import Service, ServiceType

        service_type = db.query(ServiceType).filter(
            ServiceType.path == Ltree('testing.temporal')
        ).first()
        if not service_type:
            logger.warning("ServiceType 'testing.temporal' not found - run seed_testing_temporal_service_type.py")
            return

        # Prefer an enabled service whose language matches
        service = db.query(Service).filter(
            Service.service_type_id == service_type.id,
            Service.enabled == True,  # noqa: E712
            Service.properties['language'].astext == language
        ).first()

        if service:
            content.testing_service_id = service.id
            logger.info(f"Linked service '{service.slug}' (language: {language}) to course content {content.path}")
        else:
            logger.warning(f"No enabled Service found for language '{language}' with ServiceType 'testing.temporal'")
    except Exception as e:
        logger.warning(f"Failed to link service: {e}")
