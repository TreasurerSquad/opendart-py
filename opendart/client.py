"""Async client for DART (Korea FSS) OpenAPI."""

import asyncio
import io
import zipfile
from typing import Any, Optional

import httpx

from .exceptions import DartAPIError
from .models import Disclosure, DisclosureSearchParams


class DartClient:
    """Async client for https://opendart.fss.or.kr/api.

    Usage:
        async with DartClient(api_key="...") as dart:
            disclosures, total = await dart.search_disclosures(
                DisclosureSearchParams(bgn_de="20260101", end_de="20260131")
            )
    """

    BASE_URL = "https://opendart.fss.or.kr/api"
    DEFAULT_HEADERS = {
        "User-Agent": "opendart-py/0.1",
        "Accept": "application/json",
    }

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        if not api_key:
            raise ValueError("api_key is required (issue at https://opendart.fss.or.kr)")
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "DartClient":
        return self

    async def __aexit__(self, *_exc) -> None:
        await self.close()

    async def close(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        params = {**params, "crtfc_key": self.api_key}

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._client.get(url, params=params)
                response.raise_for_status()

                if endpoint.endswith(".json"):
                    data = response.json()
                    status = data.get("status")
                    if status and status not in ("000", "013"):
                        raise DartAPIError(status, data.get("message", "Unknown error"))
                    if status == "013":
                        data["list"] = []
                        data["total_count"] = 0
                    return data
                return {"content": response.content, "text": response.text}

            except httpx.HTTPStatusError as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
            except DartAPIError:
                raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise last_error or RuntimeError("DART request failed")

    # ── Disclosure search ────────────────────────────────────────────────

    async def search_disclosures(
        self, params: DisclosureSearchParams
    ) -> tuple[list[Disclosure], int]:
        """공시 검색 (list.json). Returns (disclosures, total_count)."""
        request_params: dict[str, Any] = {
            "page_no": str(params.page_no),
            "page_count": str(params.page_count),
            "last_reprt_at": params.last_reprt_at,
            "sort": params.sort,
            "sort_mth": params.sort_mth,
        }
        for key in ("corp_code", "bgn_de", "end_de", "pblntf_ty", "pblntf_detail_ty"):
            value = getattr(params, key)
            if value:
                request_params[key] = value
        if params.corp_cls:
            request_params["corp_cls"] = params.corp_cls

        data = await self._request("list.json", request_params)

        total_count = int(data.get("total_count", 0))
        disclosures: list[Disclosure] = []
        for item in data.get("list", []):
            try:
                disclosures.append(Disclosure(**{
                    "corp_code": item.get("corp_code", ""),
                    "corp_name": item.get("corp_name", ""),
                    "stock_code": item.get("stock_code"),
                    "corp_cls": item.get("corp_cls", ""),
                    "report_nm": item.get("report_nm", ""),
                    "rcept_no": item.get("rcept_no", ""),
                    "flr_nm": item.get("flr_nm", ""),
                    "rcept_dt": item.get("rcept_dt", ""),
                    "rm": item.get("rm"),
                }))
            except Exception:
                continue

        return disclosures, total_count

    async def get_document(self, rcept_no: str) -> str:
        """공시 원문 조회 (document.xml). Returns concatenated HTML/XML text."""
        data = await self._request("document.xml", {"rcept_no": rcept_no})
        content = data.get("content", b"")
        if not content:
            return ""

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                parts: list[str] = []
                for name in zf.namelist():
                    if not name.endswith((".html", ".htm", ".xml")):
                        continue
                    raw = zf.read(name)
                    decoded: Optional[str] = None
                    for encoding in ("utf-8", "euc-kr", "cp949"):
                        try:
                            decoded = raw.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    if decoded is None:
                        decoded = raw.decode("utf-8", errors="ignore")
                    parts.append(decoded)
                return "\n".join(parts)
        except zipfile.BadZipFile:
            return data.get("text", "")

    # ── DS001: Company overview ──────────────────────────────────────────

    async def get_company_overview(self, corp_code: str) -> dict[str, Any]:
        """기업개황 (company.json)."""
        return await self._request("company.json", {"corp_code": corp_code})

    # ── DS002: Periodic reports ──────────────────────────────────────────

    async def get_dividends(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """배당에 관한 사항 (alotMatter.json)."""
        return await self._request(
            "alotMatter.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_major_shareholders(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """최대주주 현황 (hyslrSttus.json)."""
        return await self._request(
            "hyslrSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_shareholder_changes(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """최대주주 변동현황 (hyslrChg.json)."""
        return await self._request(
            "hyslrChg.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_executives(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """임원 현황 (exctvSttus.json)."""
        return await self._request(
            "exctvSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_executive_compensation(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """이사·감사 개인별 보수 (hmvAuditAllSttus.json)."""
        return await self._request(
            "hmvAuditAllSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_top_compensation(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """5억 이상 보수지급 (indvdlByPay.json)."""
        return await self._request(
            "indvdlByPay.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_treasury_stock(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """자기주식 취득·처분 (tesstkAcqsDspsSttus.json)."""
        return await self._request(
            "tesstkAcqsDspsSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_employees(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """직원 현황 (empSttus.json)."""
        return await self._request(
            "empSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_minor_shareholders(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """소액주주 현황 (mrhlSttus.json)."""
        return await self._request(
            "mrhlSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    async def get_audit_opinion(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
        """회계감사인·감사의견 (accnutAdtorNmNdAdtOpinion.json)."""
        return await self._request(
            "accnutAdtorNmNdAdtOpinion.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    # ── DS003: Financial statements ──────────────────────────────────────

    async def get_single_account(
        self, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "OFS"
    ) -> dict[str, Any]:
        """단일회사 주요계정 (fnlttSinglAcnt.json). fs_div: OFS or CFS."""
        return await self._request(
            "fnlttSinglAcnt.json",
            {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code,
                "fs_div": fs_div,
            },
        )

    async def get_full_statements(
        self, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "OFS"
    ) -> dict[str, Any]:
        """단일회사 전체 재무제표 (fnlttSinglAcntAll.json)."""
        return await self._request(
            "fnlttSinglAcntAll.json",
            {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code,
                "fs_div": fs_div,
            },
        )

    async def get_financial_indicators(
        self, corp_code: str, bsns_year: str, reprt_code: str, idx_cl_code: str = ""
    ) -> dict[str, Any]:
        """재무지표 (fnlttSinglIndx.json). idx_cl_code: M210000/M220000/M230000/M240000."""
        params: dict[str, Any] = {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
        }
        if idx_cl_code:
            params["idx_cl_code"] = idx_cl_code
        return await self._request("fnlttSinglIndx.json", params)

    # ── DS004: Stock ownership ───────────────────────────────────────────

    async def get_major_stock_reports(self, corp_code: str) -> dict[str, Any]:
        """대량보유 상황보고서 (majorstock.json)."""
        return await self._request("majorstock.json", {"corp_code": corp_code})

    async def get_executive_stock_reports(self, corp_code: str) -> dict[str, Any]:
        """임원·주요주주 소유보고서 (elestock.json)."""
        return await self._request("elestock.json", {"corp_code": corp_code})

    # ── DS005: Major decisions ───────────────────────────────────────────

    async def get_cb_issuance(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """전환사채 발행결정 (cvbdIsDecsn.json)."""
        return await self._request(
            "cvbdIsDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_bw_issuance(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """신주인수권부사채 발행결정 (bdwtIsDecsn.json)."""
        return await self._request(
            "bdwtIsDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_paid_increase(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """유상증자 결정 (piicDecsn.json)."""
        return await self._request(
            "piicDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_free_increase(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """무상증자 결정 (fricDecsn.json)."""
        return await self._request(
            "fricDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_capital_reduction(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """감자 결정 (crstDecsn.json)."""
        return await self._request(
            "crstDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_merger_decision(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """합병 결정 (cmpMgDecsn.json)."""
        return await self._request(
            "cmpMgDecsn.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    # ── DS006: Securities registration ───────────────────────────────────

    async def get_equity_registration(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """지분증권 증권신고서 (esRgistSttus.json)."""
        return await self._request(
            "esRgistSttus.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )

    async def get_debt_registration(self, corp_code: str, bgn_de: str, end_de: str) -> dict[str, Any]:
        """채무증권 증권신고서 (dbRgistSttus.json)."""
        return await self._request(
            "dbRgistSttus.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de},
        )
