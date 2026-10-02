"""Jira Cloud (REST v3, ADF) and Jira Data Center (REST v2, wiki markup)."""

from __future__ import annotations

import base64
from typing import ClassVar

from shared.definitions.issue_trackers import (
    DESTINATION_LIMIT,
    JIRA_CATEGORIES,
    STATUS_BATCH,
    TrackerKind,
)
from shared.services.issue_trackers.base import (
    UNREADABLE,
    CredentialsError,
    Option,
    RateLimitedError,
    RemoteIssue,
    RemoteNotFoundError,
    RemoteStatus,
    Tracker,
    TrackerError,
)
from shared.services.issue_trackers.document import Doc, to_adf, to_wiki

PREFERRED_TYPES = ("Bug", "Task")
STANDARD_LEVEL = 0


def _status(issue: dict) -> RemoteStatus:
    fields = issue.get("fields")
    status = fields.get("status") if isinstance(fields, dict) else None
    status = status if isinstance(status, dict) else {}
    category = status.get("statusCategory")
    key = category.get("key") if isinstance(category, dict) else None
    return RemoteStatus(
        name=str(status.get("name") or ""),
        category=JIRA_CATEGORIES.get(str(key)),
    )


def _dicts(value: object) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


class _Jira(Tracker):
    api: ClassVar[str]

    def _body(self, doc: Doc) -> object:
        raise NotImplementedError

    def _search(self, jql: str) -> list[dict]:
        raise NotImplementedError

    def verify(self) -> str:
        me = self.request_dict("GET", f"{self.api}/myself")
        return str(
            me.get("displayName") or me.get("emailAddress") or me.get("name") or ""
        )

    def issue_types(self, destination: str) -> list[Option]:
        project = self.request_dict("GET", f"{self.api}/project/{destination}")
        out: list[Option] = []
        for row in _dicts(project.get("issueTypes")):
            if not row.get("name") or row.get("subtask"):
                continue
            level = row.get("hierarchyLevel")
            if level is not None and level != STANDARD_LEVEL:
                continue
            out.append(Option(key=str(row["name"]), name=str(row["name"])))
        return out

    def _default_type(self, destination: str) -> str:
        names = [o.name for o in self.issue_types(destination)]
        for name in PREFERRED_TYPES:
            if name in names:
                return name
        if not names:
            msg = f"Jira project {destination} has no issue type."
            raise TrackerError(msg)
        return names[0]

    def _issue(self, found: dict) -> RemoteIssue | None:
        key = str(found.get("key") or "")
        if not key:
            return None
        return RemoteIssue(
            key=key,
            external_id=str(found.get("id") or key),
            url=f"{self.url}/browse/{key}",
        )

    def create(
        self,
        destination: str,
        issue_type: str | None,
        title: str,
        body: Doc,
        labels: list[str],
    ) -> RemoteIssue:
        fields = {
            "project": {"key": destination},
            "summary": title,
            "description": self._body(body),
            "issuetype": {"name": issue_type or self._default_type(destination)},
            "labels": labels,
        }
        made = self._issue(
            self.request_dict("POST", f"{self.api}/issue", json={"fields": fields})
        )
        if made is None:
            msg = "Jira did not return an issue key."
            raise TrackerError(msg)
        return made

    def comment(self, destination: str, external_id: str, body: Doc) -> None:  # noqa: ARG002
        self.request(
            "POST",
            f"{self.api}/issue/{external_id}/comment",
            json={"body": self._body(body)},
        )

    def find_marker(self, destination: str, marker: str) -> RemoteIssue | None:
        token = marker.rsplit("-", 1)[-1]
        for found in self._search(f'project = "{destination}" AND text ~ "{token}"'):
            made = self._issue(found)
            if made is not None:
                return made
        return None

    def _one(self, issue_id: str) -> RemoteStatus | None:
        try:
            issue = self.request_dict(
                "GET", f"{self.api}/issue/{issue_id}", params={"fields": "status"}
            )
        except RemoteNotFoundError:
            return None
        except (RateLimitedError, CredentialsError):
            raise
        except TrackerError:
            return RemoteStatus(name=UNREADABLE, category=None)
        return _status(issue)

    def statuses(
        self,
        destination: str,  # noqa: ARG002
        external_ids: list[str],
    ) -> dict[str, RemoteStatus | None]:
        out: dict[str, RemoteStatus | None] = {}
        for start in range(0, len(external_ids), STATUS_BATCH):
            chunk = external_ids[start : start + STATUS_BATCH]
            try:
                issues = self._search(f"id in ({','.join(chunk)})")
            except TrackerError:
                issues = []
            for issue in issues:
                out[str(issue.get("id"))] = _status(issue)
            for issue_id in chunk:
                if issue_id not in out:
                    out[issue_id] = self._one(issue_id)
        return out


class JiraCloud(_Jira):
    kind = TrackerKind.JIRA_CLOUD.value
    api = "/rest/api/3"

    def headers(self) -> dict[str, str]:
        raw = f"{self.config.get('email', '')}:{self.config.get('token', '')}"
        return {
            "Authorization": f"Basic {base64.b64encode(raw.encode()).decode()}",
            "Accept": "application/json",
        }

    def _body(self, doc: Doc) -> object:
        return to_adf(doc)

    def destinations(self, query: str = "") -> list[Option]:
        page = self.request_dict(
            "GET",
            f"{self.api}/project/search",
            params={"query": query, "maxResults": DESTINATION_LIMIT},
        )
        return [
            Option(key=str(p["key"]), name=str(p.get("name") or p["key"]))
            for p in _dicts(page.get("values"))
            if p.get("key")
        ]

    def _search(self, jql: str) -> list[dict]:
        page = self.request_dict(
            "POST",
            f"{self.api}/search/jql",
            json={"jql": jql, "fields": ["status"], "maxResults": STATUS_BATCH},
        )
        return _dicts(page.get("issues"))


class JiraDataCenter(_Jira):
    kind = TrackerKind.JIRA_DC.value
    api = "/rest/api/2"

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.get('token', '')}",
            "Accept": "application/json",
        }

    def _body(self, doc: Doc) -> object:
        return to_wiki(doc)

    def destinations(self, query: str = "") -> list[Option]:
        projects = self.request_list("GET", f"{self.api}/project")
        needle = query.strip().lower()
        return [
            Option(key=str(p["key"]), name=str(p.get("name") or p["key"]))
            for p in projects
            if p.get("key")
            and (
                not needle
                or needle in str(p["key"]).lower()
                or needle in str(p.get("name") or "").lower()
            )
        ][:DESTINATION_LIMIT]

    def _search(self, jql: str) -> list[dict]:
        page = self.request_dict(
            "POST",
            f"{self.api}/search",
            json={"jql": jql, "fields": ["status"], "maxResults": STATUS_BATCH},
        )
        return _dicts(page.get("issues"))
