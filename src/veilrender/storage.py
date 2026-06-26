"""Two-tier render cache: in-memory L1 + S3-compatible L2.

L1 uses the vendored TTLCache for fast in-process lookups.
L2 uses the minio client for persistent S3-compatible storage
(Cloudflare R2, Oracle Object Storage, AWS S3, MinIO, etc.).

S3 operations run in asyncio.to_thread() since minio is synchronous.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import io
import json
import logging

from veilrender._vendor.cache import TTLCache
from veilrender.config import settings

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages L1 (in-memory) and L2 (S3) render caches.

    Args:
        cache_enabled: Whether caching is active.
        s3_configured: Whether S3 credentials are provided for L2.
    """

    def __init__(self) -> None:
        self._l1: TTLCache | None = None
        self._s3 = None  # minio.Minio instance or None
        self._bucket: str = settings.s3_bucket

        if not settings.cache_enabled:
            logger.info("Cache disabled")
            return

        # L1: in-memory TTL cache
        self._l1 = TTLCache(
            maxsize=settings.cache_l1_maxsize,
            ttl=settings.cache_ttl,
        )
        logger.info(
            "L1 cache enabled (maxsize=%d, ttl=%ds)",
            settings.cache_l1_maxsize,
            settings.cache_ttl,
        )

        # L2: S3-compatible storage
        if settings.s3_endpoint and settings.s3_access_key and settings.s3_secret_key:
            try:
                from minio import Minio

                self._s3 = Minio(
                    settings.s3_endpoint,
                    access_key=settings.s3_access_key,
                    secret_key=settings.s3_secret_key,
                    region=settings.s3_region if settings.s3_region != "auto" else None,
                    secure=settings.s3_secure,
                )
                logger.info(
                    "L2 S3 cache enabled (endpoint=%s, bucket=%s)",
                    settings.s3_endpoint,
                    self._bucket,
                )
            except ImportError:
                logger.warning(
                    "minio package not installed, L2 cache disabled. "
                    "Install with: pip install minio"
                )
            except Exception:
                logger.warning("Failed to initialize S3 client", exc_info=True)
        else:
            logger.info("L2 S3 cache not configured (L1-only mode)")

    @property
    def enabled(self) -> bool:
        """Whether any cache tier is active."""
        return self._l1 is not None

    @property
    def s3_enabled(self) -> bool:
        """Whether L2 S3 storage is active."""
        return self._s3 is not None

    async def ensure_bucket(self) -> None:
        """Create the S3 bucket if it doesn't exist."""
        if not self._s3:
            return
        try:
            exists = await asyncio.to_thread(self._s3.bucket_exists, self._bucket)
            if not exists:
                await asyncio.to_thread(self._s3.make_bucket, self._bucket)
                logger.info("Created S3 bucket: %s", self._bucket)
        except Exception:
            logger.warning(
                "Failed to ensure S3 bucket '%s'", self._bucket, exc_info=True
            )

    @staticmethod
    def make_key(url: str, formats: list[str], wait_until: str) -> str:
        """Generate a deterministic cache key from render parameters.

        Args:
            url: The target URL.
            formats: Requested output formats.
            wait_until: Playwright wait strategy.

        Returns:
            S3 object key like ``render/a1b2c3d4e5f6g7h8.json.gz``.
        """
        normalized = f"{url}|{','.join(sorted(formats))}|{wait_until}"
        digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"render/{digest}.json.gz"

    async def get(self, key: str) -> dict | None:
        """Look up a cached render result.

        Checks L1 first, then L2. L2 hits are promoted to L1.

        Args:
            key: Cache key from ``make_key()``.

        Returns:
            Cached response dict, or None on miss.
        """
        if not self._l1:
            return None

        # L1 check
        try:
            result = self._l1[key]
            logger.debug("L1 cache hit: %s", key)
            return result
        except KeyError:
            pass

        # L2 check
        if not self._s3:
            return None

        try:
            response = await asyncio.to_thread(self._s3.get_object, self._bucket, key)
            try:
                raw = response.read()
            finally:
                response.close()
                response.release_conn()

            data = json.loads(gzip.decompress(raw))
            # Promote to L1
            self._l1[key] = data
            logger.debug("L2 cache hit (promoted to L1): %s", key)
            return data
        except Exception:
            logger.debug("L2 cache miss: %s", key)
            return None

    async def put(self, key: str, data: dict) -> None:
        """Store a render result in L1 and L2.

        Args:
            key: Cache key from ``make_key()``.
            data: Serializable response dict.
        """
        if not self._l1:
            return

        # L1 store
        self._l1[key] = data

        # L2 store
        if not self._s3:
            return

        try:
            compressed = gzip.compress(json.dumps(data).encode())
            buf = io.BytesIO(compressed)
            await asyncio.to_thread(
                self._s3.put_object,
                self._bucket,
                key,
                buf,
                length=len(compressed),
                content_type="application/json",
                metadata={"Content-Encoding": "gzip"},
            )
            logger.debug("Stored to L2: %s (%d bytes)", key, len(compressed))
        except Exception:
            logger.warning("Failed to store to L2: %s", key, exc_info=True)


storage_manager = StorageManager()
