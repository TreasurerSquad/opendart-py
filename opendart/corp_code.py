"""Resolve KRX stock_code → DART corp_code.

DART exposes a single ZIP file (`corpCode.xml`) listing every registered corp.
This module fetches it, parses to a `{stock_code: corp_code}` dict, and caches
in memory for the lifetime of the resolver. Pass your own cache backend via
the `cache` argument for cross-process caching (e.g. Redis).
"""

import io
import json
import zipfile
from typing import Optional, Protocol
from xml.etree import ElementTree as ET

import httpx


class CacheBackend(Protocol):
    """Minimal async cache interface (compatible with redis.asyncio)."""

    async def get(self, key: str) -> Optional[bytes | str]: ...
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None: ...


CACHE_KEY = "opendart:corp_code_map"
CACHE_TTL_SECONDS = 24 * 3600


class CorpCodeResolver:
    """Resolves KRX stock codes (e.g. '005930') to DART corp_code (8-digit)."""

    def __init__(
        self,
        api_key: str,
        *,
        cache: Optional[CacheBackend] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self._cache = cache
        self._http = http_client
        self._memo: Optional[dict[str, str]] = None

    async def _load_map(self) -> dict[str, str]:
        if self._memo is not None:
            return self._memo

        if self._cache is not None:
            cached = await self._cache.get(CACHE_KEY)
            if cached:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8")
                self._memo = json.loads(cached)
                return self._memo

        client = self._http or httpx.AsyncClient(timeout=30.0)
        owns_client = self._http is None
        try:
            resp = await client.get(
                "https://opendart.fss.or.kr/api/corpCode.xml",
                params={"crtfc_key": self.api_key},
            )
            resp.raise_for_status()
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            with zf.open("CORPCODE.xml") as f:
                tree = ET.parse(f)
        finally:
            if owns_client:
                await client.aclose()

        code_map: dict[str, str] = {}
        for el in tree.getroot().findall("list"):
            stock_code = (el.findtext("stock_code") or "").strip()
            corp_code = (el.findtext("corp_code") or "").strip()
            if stock_code and corp_code:
                code_map[stock_code] = corp_code

        if self._cache is not None:
            await self._cache.set(CACHE_KEY, json.dumps(code_map), ex=CACHE_TTL_SECONDS)
        self._memo = code_map
        return code_map

    async def resolve(self, stock_code: str) -> Optional[str]:
        """Return corp_code for a 6-digit KRX stock_code, or None if not listed.

        Accepts an optional 'A' prefix (common in some Korean DBs).
        """
        clean = stock_code.lstrip("A") if stock_code.startswith("A") else stock_code
        code_map = await self._load_map()
        return code_map.get(clean)

    async def all(self) -> dict[str, str]:
        """Full {stock_code: corp_code} mapping."""
        return dict(await self._load_map())
