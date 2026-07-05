"""Business logic for the GDPR consent gate.

Responsibilities:
- Resolve the current policy version (DB, cached in Redis) — through ONE
  shared helper (resolve_current_policy_version) used by both the middleware
  and the consent endpoints, so the version the gate enforces and the version
  the API reports/accepts can never disagree for longer than a single cache
  read.
- Check / record / withdraw user consent (DB, per-user gate result cached in
  Redis).
- Serve policy Markdown texts from MinIO (``policies/{version}/{lang}.md``,
  write-once) with language fallback and a Redis content cache (the texts are
  immutable per (version, lang)).

Redis keys (shared with the consent middleware):
- ``consent:current_version``            -> current version string (sentinel ``__none__`` if unconfigured)
- ``consent:{user_id}:{policy_version}`` -> "1"/"0" gate result
- ``consent:policytext:{version}:{lang}``-> cached Markdown content

Because the per-user key includes the policy version, publishing a new version
automatically invalidates all stale "1" entries (they are keyed by the old
version and simply stop being read).
"""

import hashlib
import io
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.model.consent import PolicyVersion, UserConsent
from computor_backend.repositories.consent import ConsentRepository, PolicyVersionRepository

logger = logging.getLogger(__name__)

CURRENT_VERSION_KEY = "consent:current_version"
CURRENT_VERSION_TTL = 300  # seconds; also invalidated explicitly on publish
CONSENT_STATUS_TTL = 300  # seconds
POLICY_TEXT_TTL = 3600  # seconds; content is immutable per (version, lang)
NO_VERSION_SENTINEL = "__none__"

POLICY_OBJECT_TEMPLATE = "policies/{version}/{lang}.md"
POLICY_TEXT_CACHE_KEY = "consent:policytext:{version}:{lang}"
FALLBACK_LANGUAGE = "en"


def consent_cache_key(user_id: str, policy_version: str) -> str:
    return f"consent:{user_id}:{policy_version}"


# ---------------------------------------------------------------------------
# Current-version resolution (Redis-cached; the single source of truth for
# both the middleware and the endpoints)
# ---------------------------------------------------------------------------

def _load_current_version_from_db() -> Optional[str]:
    from computor_backend.database import get_db_session

    with get_db_session() as db:
        current = PolicyVersionRepository(db).get_current()
        return current.version if current else None


async def resolve_current_policy_version() -> Optional[str]:
    """The policy version currently in force, or None if none is configured.

    Redis-cached (CURRENT_VERSION_TTL); on a miss, reads the DB in a
    threadpool using its own short session and refreshes the cache.
    """
    cached = await get_cached_current_version()
    if cached is not None:
        return None if cached == NO_VERSION_SENTINEL else cached

    version = await run_in_threadpool(_load_current_version_from_db)
    await cache_current_version(version)
    return version


# ---------------------------------------------------------------------------
# Redis cache helpers (async, used by endpoints and the middleware)
# ---------------------------------------------------------------------------

async def get_cached_current_version() -> Optional[str]:
    """Cached current version. Returns None on cache miss, the sentinel string
    NO_VERSION_SENTINEL when 'no policy configured' is cached."""
    from computor_backend.redis_cache import get_redis_client
    redis = await get_redis_client()
    return await redis.get(CURRENT_VERSION_KEY)


async def cache_current_version(version: Optional[str]) -> None:
    from computor_backend.redis_cache import get_redis_client
    redis = await get_redis_client()
    await redis.set(CURRENT_VERSION_KEY, version or NO_VERSION_SENTINEL, ex=CURRENT_VERSION_TTL)


async def invalidate_current_version_cache() -> None:
    from computor_backend.redis_cache import get_redis_client
    redis = await get_redis_client()
    await redis.delete(CURRENT_VERSION_KEY)


async def cache_consent_status(user_id: str, policy_version: str, has_consent: bool) -> None:
    from computor_backend.redis_cache import get_redis_client
    redis = await get_redis_client()
    await redis.set(consent_cache_key(user_id, policy_version), "1" if has_consent else "0", ex=CONSENT_STATUS_TTL)


async def invalidate_consent_cache(user_id: str, policy_version: str) -> None:
    from computor_backend.redis_cache import get_redis_client
    redis = await get_redis_client()
    await redis.delete(consent_cache_key(user_id, policy_version))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ConsentService:
    def __init__(self, db: Session):
        self.db = db
        self.consents = ConsentRepository(db)
        self.policy_versions = PolicyVersionRepository(db)

    # -- gate checks -----------------------------------------------------------

    def has_valid_consent(self, user_id: str, policy_version: str) -> bool:
        """True iff the user has an active consent row for the given version."""
        return self.consents.get_active_consent(user_id, policy_version) is not None

    def get_status(self, user_id: str, required_version: Optional[str]) -> dict:
        """Status against the version the gate enforces (pass the value from
        resolve_current_policy_version so gate and status agree)."""
        if required_version is None:
            return {"required_version": None, "has_consented": True, "granted_at": None}
        active = self.consents.get_active_consent(user_id, required_version)
        return {
            "required_version": required_version,
            "has_consented": active is not None,
            "granted_at": active.granted_at if active else None,
        }

    # -- consent lifecycle -----------------------------------------------------

    def record_consent(
        self,
        user_id: str,
        policy_version: str,
        required_version: Optional[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        purposes: Optional[dict] = None,
    ) -> UserConsent:
        """Record consent for policy_version, which must equal required_version
        (the gate-enforced version resolved by the caller)."""
        if required_version is None:
            raise BadRequestException("No policy version is configured; consent is not required")
        if policy_version != required_version:
            raise BadRequestException(f"Policy version mismatch: current version is '{required_version}'")
        return self.consents.create_consent(
            user_id=user_id,
            policy_version=policy_version,
            ip_address=ip_address,
            user_agent=user_agent,
            purposes=purposes,
        )

    def withdraw_consent(self, user_id: str) -> int:
        return self.consents.withdraw(user_id)

    # -- policy text (MinIO) -----------------------------------------------------

    def resolve_language(self, policy: PolicyVersion, lang: Optional[str]) -> str:
        languages = policy.languages or []
        if lang and lang in languages:
            return lang
        if FALLBACK_LANGUAGE in languages:
            return FALLBACK_LANGUAGE
        if languages:
            return languages[0]
        raise NotFoundException(f"Policy version '{policy.version}' has no language variants")

    async def get_policy_text(self, required_version: Optional[str], lang: Optional[str] = None) -> dict:
        """Policy version + Markdown text, with language fallback.

        The content is immutable per (version, lang), so it is cached in Redis;
        MinIO is only hit on a cache miss.
        """
        if required_version is None:
            raise NotFoundException("No policy version is configured")
        policy = self.policy_versions.get_by_version(required_version)
        if policy is None:
            raise NotFoundException(f"Policy version '{required_version}' not found")
        served_lang = self.resolve_language(policy, lang)

        content = await _get_policy_text_cached(policy.version, served_lang)
        return {
            "version": policy.version,
            "lang": served_lang,
            "languages": policy.languages or [],
            "effective_from": policy.effective_from,
            "content": content,
        }

    # -- publishing (admin) ------------------------------------------------------

    async def publish_policy_version(
        self,
        version: str,
        texts: dict,
        effective_from: Optional[datetime] = None,
    ) -> PolicyVersion:
        """Publish a new policy version: upload the texts to MinIO, insert the
        append-only DB row, invalidate the current-version cache.

        Write-once is enforced by the DB row (a version that exists can never
        be published again). Orphaned objects from a previously FAILED publish
        of the same version string may be overwritten — otherwise a failed
        publish would burn the version name forever.
        """
        if self.policy_versions.get_by_version(version) is not None:
            raise BadRequestException(f"Policy version '{version}' already exists (versions are immutable)")

        from computor_backend.services.storage_service import StorageService
        storage = StorageService()

        content_hashes = {}
        for lang, text_content in texts.items():
            raw = text_content.encode("utf-8")
            object_key = POLICY_OBJECT_TEMPLATE.format(version=version, lang=lang)
            await storage.upload_file(
                file_data=io.BytesIO(raw),
                object_key=object_key,
                content_type="text/markdown; charset=utf-8",
                metadata={"policy-version": version, "lang": lang},
            )
            content_hashes[lang] = hashlib.sha256(raw).hexdigest()

        policy = PolicyVersion(
            version=version,
            languages=list(texts.keys()),
            content_hashes=content_hashes,
            **({"effective_from": effective_from} if effective_from else {}),
        )
        self.db.add(policy)
        try:
            self.db.commit()
        except IntegrityError:
            # Concurrent publish of the same version string: the first commit
            # wins. content_hashes on the winning row remain the tamper check
            # if the loser's uploads landed last.
            self.db.rollback()
            raise BadRequestException(f"Policy version '{version}' already exists (versions are immutable)")
        self.db.refresh(policy)

        await invalidate_current_version_cache()
        logger.info(f"Published policy version '{version}' (languages: {list(texts.keys())})")
        return policy


async def _get_policy_text_cached(version: str, lang: str) -> str:
    from computor_backend.redis_cache import get_redis_client

    cache_key = POLICY_TEXT_CACHE_KEY.format(version=version, lang=lang)
    try:
        redis = await get_redis_client()
        cached = await redis.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        logger.warning("Policy text cache read failed; falling back to storage", exc_info=True)
        redis = None

    from computor_backend.services.storage_service import StorageService
    data = await StorageService().download_file(POLICY_OBJECT_TEMPLATE.format(version=version, lang=lang))
    content = data.decode("utf-8")

    if redis is not None:
        try:
            await redis.set(cache_key, content, ex=POLICY_TEXT_TTL)
        except Exception:
            logger.warning("Policy text cache write failed", exc_info=True)
    return content
