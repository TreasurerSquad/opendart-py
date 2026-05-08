# opendart-py

**Async Python client for DART (Korea FSS) OpenAPI** — the official Korean corporate disclosure system.

[![PyPI](https://img.shields.io/pypi/v/opendart-py.svg)](https://pypi.org/project/opendart-py/)
[![Python](https://img.shields.io/pypi/pyversions/opendart-py.svg)](https://pypi.org/project/opendart-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight async Python client for the [DART OpenAPI](https://opendart.fss.or.kr) — **Korea's equivalent of SEC EDGAR**, run by the Financial Supervisory Service. Fetch filings, financial statements, ownership reports, and major corporate decisions for any KOSPI / KOSDAQ / KONEX listed company in one line.

If you've ever used `sec-edgar-downloader` or `edgar` for US equities, this is the same idea — but for the Korean market (~2,400 listed companies, ~$2T market cap).

- **Async-first** — built on `httpx` + `asyncio`. Drops into FastAPI / aiohttp servers
- **Typed** — Pydantic v2 models for request and response validation
- **No globals** — no env-var or singleton magic. API key is passed explicitly
- **Zero infra** — no Redis or DB dependency. Inject your own cache backend if you need one

## Install

```bash
pip install opendart-py
```

## Quickstart

```python
import asyncio
from opendart import DartClient, DisclosureSearchParams, MarketType

async def main():
    async with DartClient(api_key="YOUR_DART_KEY") as dart:
        disclosures, total = await dart.search_disclosures(
            DisclosureSearchParams(
                bgn_de="20260101",
                end_de="20260131",
                corp_cls=MarketType.KOSPI.value,
            )
        )
        for d in disclosures[:5]:
            print(d.rcept_dt, d.corp_name, d.report_nm)

asyncio.run(main())
```

> Get a DART API key (free, 20,000 requests/day): https://opendart.fss.or.kr/uss/umt/login/loginPage.do

## Stock code → corp_code

DART uses its own 8-digit `corp_code` rather than the 6-digit KRX stock code. To convert:

```python
from opendart import CorpCodeResolver

resolver = CorpCodeResolver(api_key="YOUR_DART_KEY")
samsung = await resolver.resolve("005930")  # → "00126380"
```

The full `corpCode.xml` is downloaded once and cached in memory. For multi-process deployments you can inject any async cache backend (e.g. Redis):

```python
import redis.asyncio as redis

cache = redis.from_url("redis://localhost")
resolver = CorpCodeResolver(api_key="...", cache=cache)
```

## Coverage

| Category | DART group | Methods |
|---|---|---|
| Disclosure search | — | `search_disclosures`, `get_document` |
| Company overview | DS001 | `get_company_overview` |
| Periodic reports | DS002 | `get_dividends`, `get_major_shareholders`, `get_shareholder_changes`, `get_executives`, `get_executive_compensation`, `get_top_compensation`, `get_treasury_stock`, `get_employees`, `get_minor_shareholders`, `get_audit_opinion` |
| Financial statements | DS003 | `get_single_account`, `get_full_statements`, `get_financial_indicators` |
| Ownership reports | DS004 | `get_major_stock_reports`, `get_executive_stock_reports` |
| Major decisions | DS005 | `get_cb_issuance`, `get_bw_issuance`, `get_paid_increase`, `get_free_increase`, `get_capital_reduction`, `get_merger_decision` |
| Securities registration | DS006 | `get_equity_registration`, `get_debt_registration` |

## Examples

### Treasury stock (Korea Value-Up program tracking)

```python
treasury = await dart.get_treasury_stock(
    corp_code="00126380",  # Samsung Electronics
    bsns_year="2025",
    reprt_code="11011",  # Annual report
)
```

`reprt_code`: `11011` annual / `11012` half-year / `11013` Q1 / `11014` Q3.

### Convertible bond issuance monitoring

```python
cb = await dart.get_cb_issuance(
    corp_code="...",
    bgn_de="20260101",
    end_de="20260507",
)
```

### Financial indicators

```python
profitability = await dart.get_financial_indicators(
    corp_code="00126380",
    bsns_year="2025",
    reprt_code="11011",
    idx_cl_code="M210000",  # Profitability
)
```

`idx_cl_code`: `M210000` profitability / `M220000` stability / `M230000` growth / `M240000` activity.

## Production

This library was extracted from the production codebase of [Alpha Lenz](https://alpha-lenz.com) — an AI-powered Korean equity research platform — and is currently used to ingest daily disclosures across 10,000+ KRX-listed tickers.

## Development

```bash
git clone https://github.com/treasurer-co/opendart-py
cd opendart-py
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## See also

- [DART OpenAPI official documentation](https://opendart.fss.or.kr/guide/main.do)
- `pykrx` — KRX market data (complementary)
- `dart-fss` — synchronous DART client (predecessor project)
