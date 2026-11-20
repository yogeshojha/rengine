"""What an access key may call: every route the app serves, pinned."""

from __future__ import annotations

import pytest

from app.api.deps import access_key_gate, route_facts
from app.config import API_V1_PREFIX
from app.main import app
from shared.definitions.access_keys import (
    READING_POSTS,
    AccessKeyLevel,
    KeyRule,
    allows,
    key_rule,
)
from tests.api.route_table import calls, routes

pytestmark = pytest.mark.api

# ---------- the pinned classification ----------

REFUSED = """
GET /access-keys
POST /access-keys
DELETE /access-keys/{key_id}
DELETE /ai/cache
POST /ai/connections
DELETE /ai/connections/{connection_id}
PATCH /ai/connections/{connection_id}
POST /ai/connections/{connection_id}/test
POST /ai/connections/{connection_id}/use
POST /ai/models
PATCH /ai/settings
POST /ai/test
GET /api-keys
POST /api-keys
GET /api-keys/providers
DELETE /api-keys/{key_id}
PATCH /api-keys/{key_id}
GET /api-keys/{key_id}/reveal
POST /api-keys/{key_id}/test
GET /ask/brief/web-asset
GET /ask/brief/{vulnerability_id}
GET /ask/estate/scans
GET /ask/estate/starters
GET /ask/estate/status
GET /ask/estate/threads
POST /ask/estate/threads
DELETE /ask/estate/threads/{thread_id}
GET /ask/estate/threads/{thread_id}
GET /ask/estate/threads/{thread_id}/blocks
GET /ask/estate/threads/{thread_id}/blocks/{block_id}
PUT /ask/estate/threads/{thread_id}/blocks/{block_id}/query
POST /ask/estate/threads/{thread_id}/messages
DELETE /ask/threads
GET /ask/threads
POST /ask/threads
DELETE /ask/threads/{thread_id}
GET /ask/threads/{thread_id}
POST /ask/threads/{thread_id}/messages
POST /auth/2fa/disable
POST /auth/2fa/login
POST /auth/2fa/setup
GET /auth/2fa/status
POST /auth/2fa/verify
POST /auth/change-password
POST /auth/change-username
POST /auth/login
POST /auth/logout
POST /auth/refresh
PUT /bounty-programs/settings
POST /bounty-programs/sync
POST /bounty-programs/sync-feed
POST /bounty-programs/{platform}/{handle}/sync
POST /bounty-reports/{platform}/sync
GET /connectors
POST /connectors
GET /connectors/actions
GET /connectors/catalog
GET /connectors/client/{kind}
POST /connectors/findings
GET /connectors/host
POST /connectors/ingest
GET /connectors/notices
GET /connectors/scope
GET /connectors/targets
DELETE /connectors/{connector_id}
PATCH /connectors/{connector_id}
GET /connectors/{connector_id}/candidates
POST /connectors/{connector_id}/candidates/state
GET /connectors/{connector_id}/discovered
POST /connectors/{connector_id}/discovered/add
POST /connectors/{connector_id}/discovered/dismiss
POST /connectors/{connector_id}/handoff
POST /connectors/{connector_id}/rotate
POST /connectors/{connector_id}/scan
POST /datasets/{kind}/sync
GET /events/stream
GET /health/queues
PATCH /instance-settings
POST /interest/scan/{scan_id}/judge
POST /interest/scan/{scan_id}/suggestions
POST /investigate/approve
GET /investigate/brief
POST /investigate/decline
POST /investigate/run
POST /issue-trackers
PUT /issue-trackers/routes
DELETE /issue-trackers/routes/{route_id}
POST /issue-trackers/test
DELETE /issue-trackers/{tracker_id}
PATCH /issue-trackers/{tracker_id}
GET /issue-trackers/{tracker_id}/destinations
GET /issue-trackers/{tracker_id}/issue-types
POST /issue-trackers/{tracker_id}/test
POST /mcp
POST /mcp/
GET /mcp/calls
PATCH /mcp/settings
GET /mcp/status
GET /mcp/tokens
POST /mcp/tokens
DELETE /mcp/tokens/{token_id}
PATCH /mcp/tokens/{token_id}
POST /mcp/tokens/{token_id}/revoke
GET /mcp/tools
GET /notification-channels
POST /notification-channels
POST /notification-channels/test
DELETE /notification-channels/{id}
PATCH /notification-channels/{id}
POST /notification-channels/{id}/test
PATCH /oast
POST /oast/reset
POST /oast/test
GET /onboarding/ai
PUT /onboarding/ai
POST /onboarding/complete
PATCH /onboarding/progress
GET /proxies
POST /proxies
DELETE /proxies/{id}
PATCH /proxies/{id}
POST /proxies/{id}/set-default
POST /proxies/{id}/test
GET /remote-control/channels/{channel}/calls
GET /remote-control/channels/{channel}/chats
DELETE /remote-control/channels/{channel}/chats/{chat_id}
PATCH /remote-control/channels/{channel}/chats/{chat_id}
POST /remote-control/channels/{channel}/chats/{chat_id}/revoke
GET /remote-control/channels/{channel}/commands
POST /remote-control/channels/{channel}/connect
POST /remote-control/channels/{channel}/disconnect
GET /remote-control/channels/{channel}/pending
POST /remote-control/channels/{channel}/pending/{code}/approve
POST /remote-control/channels/{channel}/pending/{code}/block
PATCH /remote-control/channels/{channel}/settings
GET /remote-control/channels/{channel}/status
POST /reports
PUT /reports/defaults
POST /reports/fonts
DELETE /reports/fonts/{slug}
POST /reports/themes
DELETE /reports/themes/{slug}
POST /reports/{report_id}/retry
PUT /threat-intel/auto-sync
POST /threat-intel/sync
GET /users
POST /users
DELETE /users/{user_id}
PATCH /users/{user_id}
GET /users/{user_id}/access-keys
DELETE /users/{user_id}/access-keys/{key_id}
PUT /users/{user_id}/projects
POST /vuln-templates/sync
POST /vuln-templates/upload
DELETE /vuln-templates/{template_id}
PATCH /vuln-templates/{template_id}
PUT /vuln-templates/{template_id}/source
POST /wordlists
DELETE /wordlists/{wordlist_id}
"""

READ = """
GET /
GET /about
GET /activity
GET /ai/calls
GET /ai/catalog
GET /ai/connections
GET /ai/status
GET /auth/me
GET /bounty-programs
GET /bounty-programs/events
GET /bounty-programs/settings
GET /bounty-programs/status
GET /bounty-programs/vocabulary
GET /bounty-programs/watches
GET /bounty-programs/watches/stream
GET /bounty-programs/watches/{watch_id}
GET /bounty-programs/watches/{watch_id}/events
GET /bounty-programs/watches/{watch_id}/hosts
GET /bounty-programs/watches/{watch_id}/hosts/counts
GET /bounty-programs/{platform}/{handle}
GET /bounty-programs/{platform}/{handle}/watch/preview
GET /bounty-reports/{platform}
GET /bounty-reports/{platform}/counts
GET /bounty-reports/{platform}/programs
GET /bounty-reports/{platform}/summary
GET /cloud-storage
GET /cloud-storage/target/{target_id}
GET /contexts
GET /contexts/{id}
GET /cves
GET /cves/{cve}
GET /dashboard/activity
GET /dashboard/discovery
GET /dashboard/overview
GET /dashboard/programs
GET /dashboard/readiness
GET /dashboard/surface-risk
GET /dashboard/window
GET /datasets
GET /domain-posture
GET /domain-posture/project
GET /domain-posture/target/{target_id}
GET /endpoints/coverage
GET /endpoints/facets
POST /endpoints/gone
GET /endpoints/host
POST /endpoints/search
POST /endpoints/search/counts
POST /endpoints/search/groups
POST /endpoints/search/leads
POST /endpoints/search/tabs
GET /endpoints/structure
GET /endpoints/summary
POST /endpoints/tree
POST /endpoints/tree/hosts
POST /endpoints/tree/leaves
GET /endpoints/{endpoint_id}
GET /engines
GET /engines/catalog
GET /engines/{id}
GET /engines/{id}/export
GET /exports
POST /exports
GET /exports/{export_id}
GET /exports/{export_id}/download
GET /health/health
GET /http-assets/{asset_id}
GET /instance-settings
GET /interest/catalog
GET /interest/dismissals
GET /interest/rules
POST /interest/project
POST /interest/scan/{scan_id}
GET /ips/facets
POST /ips/search
POST /ips/search/counts
POST /ips/search/groups
POST /ips/search/leads
POST /ips/search/tabs
GET /issue-trackers
GET /issue-trackers/issues
GET /issue-trackers/routes
GET /lookalikes
GET /lookalikes/target/{target_id}
GET /media/screenshot
GET /notes
GET /notes/facets
GET /notes/tags
GET /notes/{note_id}
GET /notifications
GET /notifications/stats
GET /oast
GET /onboarding/status
GET /organizations
GET /ports/ai
GET /ports/exposure
GET /ports/facets
GET /ports/origins
POST /ports/search
POST /ports/search/counts
POST /ports/search/groups
POST /ports/search/leads
POST /ports/search/tabs
POST /ports/timeline
GET /projects
GET /reference
GET /reports
GET /reports/catalog
GET /reports/defaults
GET /reports/templates
GET /reports/themes/{slug}/source
GET /reports/{report_id}
GET /reports/{report_id}/download
GET /reports/{report_id}/preview
GET /scan-tags
GET /scans
GET /scans/compare
GET /scans/compare/diff
GET /scans/compare/rows
GET /scans/daily
GET /scans/latest
GET /scans/rescan/schema
GET /scans/stats
GET /scans/trends
GET /scans/{id}
GET /scans/{id}/activities
GET /scans/{id}/commands
GET /scans/{id}/commands/{command_id}
GET /scans/{id}/comparable
GET /scans/{scan_id}/rechecks
GET /schedules
GET /secrets/coverage
GET /secrets/facets
POST /secrets/search
POST /secrets/search/counts
POST /secrets/search/groups
GET /secrets/{secret_id}
GET /software/coverage
GET /software/facets
POST /software/search
POST /software/search/counts
GET /subdomains/correlation
GET /subdomains/correlation-graph
GET /subdomains/facets
GET /subdomains/hosting
GET /subdomains/hygiene
GET /subdomains/insights
GET /subdomains/posture
POST /subdomains/search
POST /subdomains/search/counts
POST /subdomains/search/groups
POST /subdomains/search/leads
POST /subdomains/search/renders
POST /subdomains/search/tabs
GET /subdomains/tech
POST /subdomains/timeline
POST /subdomains/timeline/renders
GET /surface/overview
GET /surface/schemas
GET /tags
GET /targets
GET /targets/counts
GET /targets/estate
GET /targets/ids
GET /targets/search
GET /targets/stats
GET /targets/{target_id}
POST /targets/{target_id}/assets
GET /targets/{target_id}/bgp
GET /targets/{target_id}/detail
GET /targets/{target_id}/dns
GET /targets/{target_id}/estate
GET /targets/{target_id}/infostealer
GET /targets/{target_id}/programs
GET /targets/{target_id}/relations
GET /targets/{target_id}/seeds
GET /targets/{target_id}/summary
GET /threat-intel/changes
GET /threat-intel/finding/{vulnerability_id}
GET /threat-intel/signal/{kind}
GET /threat-intel/status
GET /toolbox/catalog
GET /toolbox/runs
GET /toolbox/runs/{run_id}
POST /tools/viewdns/cached-counts
GET /tools/whois/correlations/nameserver
GET /tools/whois/correlations/network
GET /tools/whois/correlations/registrant
GET /tools/whois/correlations/registrar
GET /tools/whois/correlations/target/{target_id}
GET /tools/whois/correlations/targets
GET /tools/whois/records/{record_id}
GET /tripwires
GET /tripwires/catalog
GET /tripwires/runs/{run_id}
GET /tripwires/{tripwire_id}/runs
GET /tripwires/{tripwire_id}/runs/counts
GET /users/{user_id}/summary
POST /vuln-templates/search
GET /vuln-templates/stats
GET /vuln-templates/{template_id}/source
GET /vulnerabilities/coverage
GET /vulnerabilities/facets
GET /vulnerabilities/overview
POST /vulnerabilities/search
POST /vulnerabilities/search/counts
POST /vulnerabilities/search/groups
POST /vulnerabilities/search/issues
POST /vulnerabilities/search/leads
POST /vulnerabilities/search/tabs
POST /vulnerabilities/timeline
GET /vulnerabilities/{vulnerability_id}
GET /whats-new
GET /whats-new/unseen
GET /whats-new/visual
GET /wordlists
GET /wordlists/{wordlist_id}/preview
"""

WRITE = """
POST /bounty-programs/events/seen
POST /bounty-programs/watches/validate-query
DELETE /bounty-programs/watches/{watch_id}
PATCH /bounty-programs/watches/{watch_id}
POST /bounty-programs/watches/{watch_id}/hosts/{host_id}/mute
POST /bounty-programs/watches/{watch_id}/seen
POST /bounty-programs/{platform}/{handle}/import
POST /bounty-programs/{platform}/{handle}/watch
PATCH /cloud-storage/triage
POST /contexts
DELETE /contexts/{id}
PATCH /contexts/{id}
POST /contexts/{id}/duplicate
POST /endpoints/verify
POST /engines
POST /engines/import
POST /engines/preview
DELETE /engines/{id}
PATCH /engines/{id}
POST /engines/{id}/duplicate
DELETE /exports/{export_id}
POST /exports/{export_id}/rerun
POST /interest/dismiss
POST /interest/dismiss/bulk
DELETE /interest/dismissals/{dismissal_id}
POST /interest/rules
POST /interest/rules/preview
DELETE /interest/rules/{rule_id}
PATCH /interest/rules/{rule_id}
POST /issue-trackers/issues
POST /issue-trackers/issues/plan
DELETE /issue-trackers/issues/{issue_id}
POST /issue-trackers/issues/{issue_id}/refresh
POST /issue-trackers/issues/{issue_id}/retry
PATCH /lookalikes/triage
POST /notes
DELETE /notes/{note_id}
PATCH /notes/{note_id}
DELETE /notifications
POST /notifications/read-all
DELETE /notifications/{notification_id}
PATCH /notifications/{notification_id}/read
POST /organizations
DELETE /organizations/{organization_id}
PATCH /organizations/{organization_id}
POST /projects
POST /reports/estimate
POST /reports/templates
DELETE /reports/templates/{template_id}
PATCH /reports/templates/{template_id}
DELETE /reports/{report_id}
POST /scan-tags/assign
POST /scans/batch
POST /scans/cancel-all
POST /scans/preview
POST /scans/rescan
POST /scans/rescan/preview
DELETE /scans/{id}
POST /scans/{id}/cancel
POST /scans/{id}/pause
POST /scans/{id}/resume
POST /schedules
DELETE /schedules/{id}
PATCH /schedules/{id}
POST /schedules/{id}/pause
POST /schedules/{id}/resume
POST /schedules/{id}/run-now
POST /surface/delete
POST /tags
DELETE /tags/{tag_id}
PATCH /tags/{tag_id}
POST /targets
POST /targets/bulk
POST /targets/enrich/bulk
PATCH /targets/estate/triage
POST /targets/import/csv
POST /targets/import/json
POST /targets/organizations/bulk
POST /targets/tags/bulk
POST /targets/validate
POST /targets/validate/batch
DELETE /targets/{target_id}
PATCH /targets/{target_id}
POST /targets/{target_id}/bgp/refresh
POST /targets/{target_id}/dns/refresh
POST /targets/{target_id}/infostealer/refresh
PUT /targets/{target_id}/seeds
DELETE /targets/{target_id}/seeds/{seed_id}
POST /targets/{target_id}/whois/refresh
POST /toolbox/run
DELETE /toolbox/runs
GET /tools/viewdns/reverse-ip/{host}
GET /tools/viewdns/reverse-ns/{nameserver}
GET /tools/viewdns/reverse-whois
POST /tools/whois/records/{record_id}/refresh
POST /tripwires
POST /tripwires/backtest
POST /tripwires/daily/preview
POST /tripwires/preview
DELETE /tripwires/{tripwire_id}
PATCH /tripwires/{tripwire_id}
POST /vuln-templates/seen
POST /vuln-templates/selection
POST /vulnerabilities/triage/bulk
PATCH /vulnerabilities/triage/{fingerprint}
POST /whats-new/seen
"""


PINNED: dict[tuple[str, str], KeyRule] = {
    tuple(line.split(" ", 1)): rule
    for rule, block in (
        (KeyRule.REFUSED, REFUSED),
        (KeyRule.READ, READ),
        (KeyRule.WRITE, WRITE),
    )
    for line in block.strip().splitlines()
}


# served outside the gate: FastAPI's documentation under DEBUG alone
NO_DEPENDANT = frozenset({"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"})


def _gated(route) -> bool:
    return getattr(route, "dependant", None) is not None


def _served() -> dict[tuple[str, str], KeyRule]:
    found: dict[tuple[str, str], KeyRule] = {}
    for route in routes(app):
        if not _gated(route):
            continue
        facts = route_facts(route, API_V1_PREFIX)
        for method in route.methods:
            found[(method, facts.path)] = key_rule(
                method, facts.path, gated=facts.gated
            )
    return found


SERVED = _served()


def test_every_served_route_is_pinned():
    unpinned = sorted(
        f"{m} {p} -> {r}" for (m, p), r in SERVED.items() if (m, p) not in PINNED
    )
    gone = sorted(f"{m} {p}" for (m, p) in PINNED if (m, p) not in SERVED)
    assert not unpinned, "classify these routes for access keys:\n  " + "\n  ".join(
        unpinned
    )
    assert not gone, "these pinned routes are no longer served:\n  " + "\n  ".join(gone)


def test_the_classification_matches_the_pin():
    moved = sorted(
        f"{m} {p}: pinned {PINNED[(m, p)]}, now {rule}"
        for (m, p), rule in SERVED.items()
        if (m, p) in PINNED and PINNED[(m, p)] is not rule
    )
    assert not moved, "\n  ".join(moved)


def test_every_route_passes_through_the_gate():
    loose = [
        route.path
        for route in routes(app)
        if _gated(route) and access_key_gate not in calls(route.dependant)
    ]
    assert not loose


def test_every_route_outside_the_gate_is_listed():
    outside = sorted(
        getattr(route, "path", repr(route))
        for route in routes(app)
        if not _gated(route) and getattr(route, "path", None) not in NO_DEPENDANT
    )
    assert not outside, "these routes skip the access key gate:\n  " + "\n  ".join(
        outside
    )


def test_a_mount_is_caught(monkeypatch):
    from starlette.routing import Mount  # noqa: PLC0415

    monkeypatch.setattr(app.router, "routes", [*app.router.routes, Mount("/x", app)])
    with pytest.raises(AssertionError, match="skip the access key gate"):
        test_every_route_outside_the_gate_is_listed()


def test_every_administrator_and_stream_route_is_refused():
    for route in routes(app):
        if not _gated(route):
            continue
        facts = route_facts(route, API_V1_PREFIX)
        if facts.gated:
            for method in route.methods:
                assert SERVED[(method, facts.path)] is KeyRule.REFUSED, facts.path


def test_every_reading_post_is_served():
    assert {p for (m, p) in SERVED if m == "POST"} >= READING_POSTS


@pytest.mark.parametrize(
    ("method", "path", "gated", "rule"),
    [
        ("GET", "/targets", False, KeyRule.READ),
        ("HEAD", "/targets", False, KeyRule.READ),
        ("POST", "/subdomains/search", False, KeyRule.READ),
        ("POST", "/subdomains/search/x", False, KeyRule.WRITE),
        ("POST", "/targets", False, KeyRule.WRITE),
        ("PUT", "/targets/{target_id}/seeds", False, KeyRule.WRITE),
        ("DELETE", "/targets/{target_id}", False, KeyRule.WRITE),
        ("GET", "/users", True, KeyRule.REFUSED),
        ("GET", "/auth/me", False, KeyRule.READ),
        ("GET", "/auth/2fa/status", False, KeyRule.REFUSED),
        ("POST", "/auth/new-route", False, KeyRule.REFUSED),
        ("GET", "/askew", False, KeyRule.READ),
        ("GET", "/ask/threads", False, KeyRule.REFUSED),
        ("GET", "/anything/stream", False, KeyRule.READ),
        ("POST", "/interest/scan/{scan_id}/judge", False, KeyRule.REFUSED),
        ("POST", "/interest/scan/{scan_id}/suggestions", False, KeyRule.REFUSED),
        ("POST", "/reports", False, KeyRule.REFUSED),
        ("POST", "/reports/{report_id}/retry", False, KeyRule.REFUSED),
        ("POST", "/reports/estimate", False, KeyRule.WRITE),
        ("POST", "/interest/project", False, KeyRule.READ),
        ("POST", "/interest/scan/{scan_id}", False, KeyRule.READ),
        ("GET", "/tools/viewdns/reverse-whois", False, KeyRule.WRITE),
        ("POST", "/tools/viewdns/cached-counts", False, KeyRule.READ),
        ("POST", "/targets/{target_id}/assets", False, KeyRule.READ),
        ("OPTIONS", "/targets", False, KeyRule.WRITE),
    ],
)
def test_the_rule(method, path, gated, rule):
    assert key_rule(method, path, gated=gated) is rule


def test_a_level_allows():
    assert allows(AccessKeyLevel.READ, KeyRule.READ)
    assert not allows(AccessKeyLevel.READ, KeyRule.WRITE)
    assert allows(AccessKeyLevel.WRITE, KeyRule.WRITE)
    assert not allows(AccessKeyLevel.WRITE, KeyRule.REFUSED)
