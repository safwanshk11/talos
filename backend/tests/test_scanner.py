import os
import pytest
from app.services.usage_finder_service import UsageFinderService
from app.services.readiness_service import ReadinessService
from app.services.scanner_service import ScannerService

FIXTURE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "vulnerable_repo"))


def test_usage_finder_service():
    usages = UsageFinderService.find_package_usages(FIXTURE_PATH, "axios")
    assert len(usages) > 0
    assert any("index.js" in u for u in usages)


def test_readiness_service():
    res = ReadinessService.evaluate_repository(FIXTURE_PATH)
    assert res["manifest_found"] is True
    assert res["build_script_found"] is True
    assert res["test_script_found"] is True
    assert res["lint_script_found"] is True
    assert res["score_level"] in ["HIGH", "MEDIUM"]


@pytest.mark.asyncio
async def test_osv_vulnerability_query():
    queries = [{"package": {"name": "axios", "ecosystem": "npm"}, "version": "0.21.1"}]
    results = await ScannerService.query_osv_vulnerabilities(queries)
    assert len(results) > 0
    vulns = results[0].get("vulns", [])
    assert len(vulns) > 0
    # OSV API returns advisories (GHSA-c2qf-rxjj-qqgw / GHSA-4w2v-q235-vp99)
    advisory_ids = [v.get("id") for v in vulns]
    assert any(adv for adv in advisory_ids if adv.startswith("GHSA") or adv.startswith("CVE") or adv.startswith("OSV"))
