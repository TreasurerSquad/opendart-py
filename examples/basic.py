"""Minimal example: list recent KOSPI disclosures + Samsung Electronics overview."""

import asyncio
import os

from opendart import DartClient, CorpCodeResolver, DisclosureSearchParams, MarketType


async def main() -> None:
    api_key = os.environ["DART_API_KEY"]

    async with DartClient(api_key=api_key) as dart:
        disclosures, total = await dart.search_disclosures(
            DisclosureSearchParams(
                bgn_de="20260501",
                end_de="20260507",
                corp_cls=MarketType.KOSPI.value,
                page_count=10,
            )
        )
        print(f"KOSPI disclosures (total={total}):")
        for d in disclosures:
            print(f"  [{d.rcept_dt}] {d.corp_name} — {d.report_nm}")

        resolver = CorpCodeResolver(api_key=api_key)
        samsung_corp_code = await resolver.resolve("005930")
        if samsung_corp_code:
            overview = await dart.get_company_overview(samsung_corp_code)
            print(f"\nSamsung Electronics ({samsung_corp_code}):")
            print(f"  CEO: {overview.get('ceo_nm')}")
            print(f"  Established: {overview.get('est_dt')}")
            print(f"  Homepage: {overview.get('hm_url')}")


if __name__ == "__main__":
    asyncio.run(main())
