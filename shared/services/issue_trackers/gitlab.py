"""GitLab Issues, gitlab.com or self-managed."""

from __future__ import annotations

from urllib.parse import quote

from shared.definitions.issue_trackers import (
    DESTINATION_LIMIT,
    RemoteCategory,
    TrackerKind,
)
from shared.services.issue_trackers.base import (
    Option,
    RemoteIssue,
    RemoteNotFoundError,
    RemoteStatus,
    Tracker,
    TrackerError,
)
from shared.services.issue_trackers.document import Doc, to_markdown
from shared.services.issue_trackers.github import UNREADABLE

API = "/api/v4"
PUBLIC = "public"


def gitlab_status(issue: dict) -> RemoteStatus:
    if issue.get("state") == "closed":
        return RemoteStatus(name="Closed", category=RemoteCategory.DONE.value)
    return RemoteStatus(name="Open", category=RemoteCategory.TODO.value)


def _project(path: str) -> str:
    return quote(path, safe="")


class GitLabIssues(Tracker):
    kind = TrackerKind.GITLAB.value
    initial_status = "Open"

    def headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": str(self.config.get("token", ""))}

    def verify(self) -> str:
        me = self.request_dict("GET", f"{API}/user")
        return str(me.get("username") or me.get("name") or "")

    def destinations(self, query: str = "") -> list[Option]:
        params: dict = {
            "membership": "true",
            "per_page": DESTINATION_LIMIT,
            "order_by": "last_activity_at",
            "simple": "true",
        }
        if query.strip():
            params["search"] = query.strip()
        projects = self.request_list("GET", f"{API}/projects", params=params)
        return [
            Option(
                key=str(p["path_with_namespace"]),
                name=str(p.get("name_with_namespace") or p["path_with_namespace"]),
            )
            for p in projects
            if p.get("path_with_namespace")
        ]

    def public_destination(self, destination: str) -> bool:
        project = self.request_dict("GET", f"{API}/projects/{_project(destination)}")
        return project.get("visibility") == PUBLIC

    def _issue(self, destination: str, made: dict) -> RemoteIssue:
        iid = made.get("iid")
        if not iid:
            msg = "GitLab did not return an issue number."
            raise TrackerError(msg)
        return RemoteIssue(
            key=f"{destination}#{iid}",
            external_id=str(iid),
            url=str(made.get("web_url") or ""),
        )

    def create(
        self,
        destination: str,
        issue_type: str | None,  # noqa: ARG002
        title: str,
        body: Doc,
        labels: list[str],
    ) -> RemoteIssue:
        made = self.request_dict(
            "POST",
            f"{API}/projects/{_project(destination)}/issues",
            json={
                "title": title,
                "description": to_markdown(body),
                "labels": ",".join(labels),
            },
        )
        return self._issue(destination, made)

    def comment(self, destination: str, external_id: str, body: Doc) -> None:
        self.request(
            "POST",
            f"{API}/projects/{_project(destination)}/issues/{external_id}/notes",
            json={"body": to_markdown(body)},
        )

    def find_marker(self, destination: str, marker: str) -> RemoteIssue | None:
        found = self.request_list(
            "GET",
            f"{API}/projects/{_project(destination)}/issues",
            params={"search": marker, "in": "description", "per_page": 20},
        )
        for issue in found:
            if marker in str(issue.get("description") or ""):
                return self._issue(destination, issue)
        return None

    def statuses(
        self, destination: str, external_ids: list[str]
    ) -> dict[str, RemoteStatus | None]:
        out: dict[str, RemoteStatus | None] = {}
        for iid in external_ids:
            try:
                issue = self.request_dict(
                    "GET", f"{API}/projects/{_project(destination)}/issues/{iid}"
                )
            except RemoteNotFoundError:
                out[iid] = None
                continue
            except TrackerError:
                out[iid] = RemoteStatus(name=UNREADABLE, category=None)
                continue
            out[iid] = gitlab_status(issue)
        return out
