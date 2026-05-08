from datetime import date

from opendart.models import Disclosure, DisclosureSearchParams, MarketType


def test_disclosure_date_parses_yyyymmdd():
    d = Disclosure(
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        corp_cls="Y",
        report_nm="분기보고서",
        rcept_no="20260514000123",
        flr_nm="삼성전자",
        rcept_dt="20260514",
    )
    assert d.disclosure_date == date(2026, 5, 14)
    assert d.is_correction is False


def test_disclosure_correction_flag():
    d = Disclosure(
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        corp_cls="Y",
        report_nm="[기재정정]분기보고서",
        rcept_no="20260514000123",
        flr_nm="삼성전자",
        rcept_dt="20260514",
    )
    assert d.is_correction is True


def test_market_type_values():
    assert MarketType.KOSPI.value == "Y"
    assert MarketType.KOSDAQ.value == "K"


def test_search_params_defaults():
    p = DisclosureSearchParams()
    assert p.page_no == 1
    assert p.page_count == 100
    assert p.last_reprt_at == "N"
