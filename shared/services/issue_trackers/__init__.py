"""Issue tracker clients, one module per tracker kind."""

from __future__ import annotations

import json

from shared.models.issue_tracker import IssueTracker
from shared.services.issue_trackers.base import (
    CredentialsError,
    RateLimitedError,
    RemoteIssue,
    RemoteNotFoundError,
    RemoteStatus,
    Tracker,
    TrackerError,
)
from shared.services.issue_trackers.github import GitHubIssues
from shared.services.issue_trackers.gitlab import GitLabIssues
from shared.services.issue_trackers.jira import JiraCloud, JiraDataCenter
from shared.utils.crypto import encrypt_secret, try_decrypt

CLIENTS: dict[str, type[Tracker]] = {
    cls.kind: cls for cls in (JiraCloud, JiraDataCenter, GitHubIssues, GitLabIssues)
}


def open_config(row: IssueTracker) -> dict:
    raw = try_decrypt(row.config_encrypted)
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def seal_config(config: dict) -> str:
    return encrypt_secret(json.dumps(config))


def client_for(kind: str, url: str, config: dict) -> Tracker:
    cls = CLIENTS.get(kind)
    if cls is None:
        msg = f"Unknown tracker type {kind}."
        raise TrackerError(msg)
    return cls(url, config)


def tracker_client(row: IssueTracker) -> Tracker:
    return client_for(row.kind, row.url, open_config(row))


__all__ = [
    "CredentialsError",
    "RateLimitedError",
    "RemoteIssue",
    "RemoteNotFoundError",
    "RemoteStatus",
    "Tracker",
    "TrackerError",
    "client_for",
    "open_config",
    "seal_config",
    "tracker_client",
]
