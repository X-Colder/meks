from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from meks.pipeline.crawlers import CrawlResult
from meks.pipeline.tasks import _should_run
from meks.services.sync_service import _date_watermark, _latest_first
from meks.services.paper_analysis_service import _has_required_analysis_keys, _parse_analysis_response


def test_should_run_matching_cron_slot_once():
    now = datetime(2026, 6, 11, 2, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert _should_run("0 2 * * *", None, now)
    assert not _should_run("0 2 * * *", now.astimezone(timezone.utc), now)


def test_should_run_step_expression():
    now = datetime(2026, 6, 11, 2, 10, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert _should_run("*/5 * * * *", None, now)
    assert not _should_run("*/15 * * * *", None, now)


def test_date_watermark_ignores_old_external_id_watermarks():
    assert _date_watermark("PMC123456") is None
    assert _date_watermark("2026-06-11") == "2026-06-11"


def test_latest_first_orders_by_publication_date_then_citation_count():
    older = CrawlResult("a", "older", "", "", "", date(2025, 1, 1), {"citation_count": 100})
    newer_low_citation = CrawlResult("b", "newer", "", "", "", date(2026, 1, 1), {"citation_count": 1})
    newer_high_citation = CrawlResult("c", "newer cited", "", "", "", date(2026, 1, 1), {"citation_count": 2})

    ordered = _latest_first([older, newer_low_citation, newer_high_citation])

    assert [item.external_id for item in ordered] == ["c", "b", "a"]


def test_paper_analysis_requires_all_top_level_sections():
    partial = _parse_analysis_response('{"overall": {"risk_score": 0}}')

    assert not _has_required_analysis_keys(partial)
