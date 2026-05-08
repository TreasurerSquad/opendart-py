"""opendart — Async Python client for DART OpenAPI.

DART (https://opendart.fss.or.kr) is Korea's equivalent of SEC EDGAR,
operated by the Financial Supervisory Service. This client provides
async access to filings, financial statements, and ownership reports
for KOSPI / KOSDAQ / KONEX listed companies.

Built and maintained by Alpha Lenz (https://alpha-lenz.com), an
AI-powered Korean equity research platform.
"""

from .client import DartClient
from .corp_code import CorpCodeResolver
from .exceptions import DartAPIError
from .models import (
    Disclosure,
    DisclosureSearchParams,
    MarketType,
)

__version__ = "0.1.0"

__all__ = [
    "DartClient",
    "CorpCodeResolver",
    "DartAPIError",
    "Disclosure",
    "DisclosureSearchParams",
    "MarketType",
    "__version__",
]
