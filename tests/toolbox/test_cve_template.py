from __future__ import annotations

import uuid

from shared.definitions.vulnerabilities import Protocol
from shared.models.threat_intel import CveIntel
from shared.models.vuln_template import VulnTemplate
from toolbox import estate
from toolbox.base import ToolContext
from toolbox.tools.cve import (
    HAS_TEMPLATE,
    NO_TEMPLATE,
    CveLookup,
    Input,
    _library_note,
    _template,
)

CVE = "CVE-2021-44228"


def _intel(available: bool | None) -> CveIntel:
    return CveIntel(cve=CVE, template_available=available)


def test_library_check_wins_over_an_empty_provider_cache():
    assert _template(None, 2, True) == HAS_TEMPLATE
    assert _template(_intel(None), 1, True) == HAS_TEMPLATE
    assert _template(_intel(False), 1, True) == HAS_TEMPLATE


def test_provider_answer_is_used_when_the_library_has_no_check():
    assert _template(_intel(True), 0, True) == HAS_TEMPLATE
    assert _template(_intel(False), 0, True) == NO_TEMPLATE


def test_loaded_library_without_the_check_is_none_and_empty_library_is_unknown():
    assert _template(None, 0, True) == NO_TEMPLATE
    assert _template(None, 0, False) == ""


def test_note_names_the_library_count_or_its_absence():
    assert _library_note(38, HAS_TEMPLATE) == "38 checks in the library"
    assert _library_note(1, HAS_TEMPLATE) == "1 check in the library"
    assert _library_note(0, HAS_TEMPLATE) == "not in the library"
    assert _library_note(0, NO_TEMPLATE) is None


def _check(template_id: str, cves: list[str], *, enabled: bool = True) -> VulnTemplate:
    return VulnTemplate(
        template_id=template_id,
        path=f"http/cves/{template_id}-{uuid.uuid4().hex[:6]}.yaml",
        name=template_id,
        protocol=Protocol.HTTP.value,
        cve_ids=cves,
        enabled=enabled,
    )


async def test_library_checks_counts_enabled_checks_naming_the_cve(session):
    session.add_all(
        [
            _check(CVE, [CVE]),
            _check("solr-log4j", [CVE, "CVE-2021-45046"]),
            _check("disabled-log4j", [CVE], enabled=False),
            _check("other", ["CVE-2014-0160"]),
        ]
    )
    await session.flush()
    assert await estate.library_checks(session, CVE) == (2, True)
    assert await estate.library_checks(session, "CVE-2000-0001") == (0, True)


async def test_lookup_reports_the_library_check_without_provider_data(session):
    session.add(_check(CVE, [CVE]))
    await session.flush()
    outcome = await CveLookup().run(ToolContext(session=session), Input(cve=CVE))
    assert outcome.raw["library_checks"] == 1
    mark = next(m for m in outcome.blocks[0].marks if m.label == "Nuclei template")
    assert mark.note == "1 in the library"
