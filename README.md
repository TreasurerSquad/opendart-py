# opendart-py

**Async Python client for DART (Korea FSS) OpenAPI** — 한국 금융감독원 전자공시 비동기 클라이언트.

[![PyPI](https://img.shields.io/pypi/v/opendart.svg)](https://pypi.org/project/opendart/)
[![Python](https://img.shields.io/pypi/pyversions/opendart.svg)](https://pypi.org/project/opendart/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

DART (전자공시시스템, https://opendart.fss.or.kr) OpenAPI를 비동기로 호출하는 가벼운 Python 클라이언트입니다. KOSPI / KOSDAQ / KONEX 상장사의 공시, 재무제표, 지분공시, 주요사항보고서를 한 줄로 가져올 수 있습니다.

- **Async-first**: `httpx` + `asyncio` 기반. FastAPI / aiohttp 서버에서 그대로 사용
- **Typed**: Pydantic v2 모델로 응답 검증
- **No globals**: 환경변수·싱글톤 강제 없음. API key 직접 주입
- **Zero infra**: Redis · DB 의존성 없음 (필요 시 cache backend 주입 가능)

## Install

```bash
pip install opendart
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

> DART API 키 발급: https://opendart.fss.or.kr/uss/umt/login/loginPage.do (무료, 일 20,000건)

## Stock code → corp_code

DART는 자체 8자리 `corp_code`를 사용합니다. KRX 종목코드(`005930`)로 변환하려면:

```python
from opendart import CorpCodeResolver

resolver = CorpCodeResolver(api_key="YOUR_DART_KEY")
samsung = await resolver.resolve("005930")  # → "00126380"
```

`corpCode.xml` 전체를 한 번 다운로드 후 메모리에 캐시합니다. 멀티프로세스 환경에서는 Redis 등 외부 캐시를 주입할 수 있습니다:

```python
import redis.asyncio as redis

cache = redis.from_url("redis://localhost")
resolver = CorpCodeResolver(api_key="...", cache=cache)
```

## Coverage

| 카테고리 | DART 분류 | 메서드 |
|---|---|---|
| 공시 검색 | — | `search_disclosures`, `get_document` |
| 기업개황 | DS001 | `get_company_overview` |
| 정기보고서 | DS002 | `get_dividends`, `get_major_shareholders`, `get_shareholder_changes`, `get_executives`, `get_executive_compensation`, `get_top_compensation`, `get_treasury_stock`, `get_employees`, `get_minor_shareholders`, `get_audit_opinion` |
| 재무제표 | DS003 | `get_single_account`, `get_full_statements`, `get_financial_indicators` |
| 지분공시 | DS004 | `get_major_stock_reports`, `get_executive_stock_reports` |
| 주요사항보고서 | DS005 | `get_cb_issuance`, `get_bw_issuance`, `get_paid_increase`, `get_free_increase`, `get_capital_reduction`, `get_merger_decision` |
| 증권신고서 | DS006 | `get_equity_registration`, `get_debt_registration` |

## Examples

### 자사주 취득 (밸류업 프로그램 추적)

```python
treasury = await dart.get_treasury_stock(
    corp_code="00126380",  # Samsung Electronics
    bsns_year="2025",
    reprt_code="11011",  # 사업보고서
)
```

`reprt_code`: `11011` 사업보고서 / `11012` 반기 / `11013` 1분기 / `11014` 3분기.

### 전환사채 발행 모니터링

```python
cb = await dart.get_cb_issuance(
    corp_code="...",
    bgn_de="20260101",
    end_de="20260507",
)
```

### 재무지표

```python
profitability = await dart.get_financial_indicators(
    corp_code="00126380",
    bsns_year="2025",
    reprt_code="11011",
    idx_cl_code="M210000",  # 수익성
)
```

`idx_cl_code`: `M210000` 수익성 / `M220000` 안정성 / `M230000` 성장성 / `M240000` 활동성.

## Production

이 라이브러리는 [Alpha Lens](https://alphalens.io) — 한국 주식 AI 투자 분석 서비스 — 의 프로덕션 코드에서 분리되었으며, 현재 1만+ 종목 일일 공시 수집에 사용 중입니다.

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

- [DART OpenAPI 공식 문서](https://opendart.fss.or.kr/guide/main.do)
- `pykrx` — KRX 시세 데이터 (보완 관계)
- `dart-fss` — 동기 DART 클라이언트 (선구 프로젝트)
