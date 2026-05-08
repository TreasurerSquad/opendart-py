from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    """법인 구분 (corp_cls)."""

    KOSPI = "Y"
    KOSDAQ = "K"
    KONEX = "N"
    OTHER = "E"
    ALL = ""


class DisclosureSearchParams(BaseModel):
    """Parameters for `list.json` (공시 검색)."""

    corp_code: Optional[str] = None
    bgn_de: Optional[str] = None
    end_de: Optional[str] = None
    last_reprt_at: str = "N"
    pblntf_ty: Optional[str] = None
    pblntf_detail_ty: Optional[str] = None
    corp_cls: str = ""
    sort: str = "date"
    sort_mth: str = "desc"
    page_no: int = 1
    page_count: int = 100


class Disclosure(BaseModel):
    """A single disclosure item returned by `list.json`."""

    corp_code: str = Field(..., description="고유번호 (8-digit)")
    corp_name: str = Field(..., description="회사명")
    stock_code: Optional[str] = Field(None, description="종목코드")
    corp_cls: str = Field(..., description="법인구분 (Y/K/N/E)")
    report_nm: str = Field(..., description="보고서명")
    rcept_no: str = Field(..., description="접수번호")
    flr_nm: str = Field(..., description="공시제출인명")
    rcept_dt: str = Field(..., description="접수일자 (YYYYMMDD)")
    rm: Optional[str] = Field(None, description="비고")

    @property
    def disclosure_date(self) -> date:
        return datetime.strptime(self.rcept_dt, "%Y%m%d").date()

    @property
    def is_correction(self) -> bool:
        return "정정" in self.report_nm
