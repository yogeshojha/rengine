"""GitHub Issues, github.com or Enterprise Server."""

from __future__ import annotations

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

NOT_PLANNED = "not_planned"
REPO_PAGES = 5
UNREADABLE = "Unavailable"


def github_status(issue: dict) -> RemoteStatus:
    if issue.get("state") == "closed":
        name = (
            "Closed as not planned"
            if issue.get("state_reason") == NOT_PLANNED
            else "Closed"
        )
        return RemoteStatus(name=name, category=RemoteCategory.DONE.value)
    return RemoteStatus(name="Open", category=RemoteCategory.TODO.value)


class GitHubIssues(Tracker):
    kind = TrackerKind.GITHUB.value
    initial_status = "Open"

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.get('token', '')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def verify(self) -> str:
        me = self.request_dict("GET", "/user")
        return str(me.get("login") or "")

    def destinations(self, query: str = "") -> list[Option]:
        needle = query.strip().lower()
        out: list[Option] = []
        for page in range(1, REPO_PAGES + 1):
            repos = self.request_list(
                "GET",
                "/user/repos",
                params={"per_page": 100, "sort": "updated", "page": page},
            )
            out.extend(
                Option(key=str(r["full_name"]), name=str(r["full_name"]))
                for r in repos
                if r.get("full_name")
                and r.get("has_issues", True)
                and (not needle or needle in str(r["full_name"]).lower())
            )
            if len(out) >= DESTINATION_LIMIT or len(repos) < 100:  # noqa: PLR2004
                break
        return out[:DESTINATION_LIMIT]

    def public_destination(self, destination: str) -> bool:
        repo = self.request_dict("GET", f"/repos/{destination}")
        return repo.get("private") is False

    def _issue(self, destination: str, made: dict) -> RemoteIssue:
        number = made.get("number")
        if not number:
            msg = "GitHub did not return an issue number."
            raise TrackerError(msg)
        return RemoteIssue(
            key=f"{destination}#{number}",
            external_id=str(number),
            url=str(made.get("html_url") or ""),
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
            f"/repos/{destination}/issues",
            json={"title": title, "body": to_markdown(body), "labels": labels},
        )
        return self._issue(destination, made)

    def comment(self, destination: str, external_id: str, body: Doc) -> None:
        self.request(
            "POST",
            f"/repos/{destination}/issues/{external_id}/comments",
            json={"body": to_markdown(body)},
        )

    def find_marker(self, destination: str, marker: str) -> RemoteIssue | None:
        mine = self.verify()
        recent = self.request_list(
            "GET",
            f"/repos/{destination}/issues",
            params={
                "creator": mine,
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": 100,
            },
        )
        for issue in recent:
            if "pull_request" not in issue and marker in str(issue.get("body") or ""):
                return self._issue(destination, issue)
        return None

    def statuses(
        self, destination: str, external_ids: list[str]
    ) -> dict[str, RemoteStatus | None]:
        out: dict[str, RemoteStatus | None] = {}
        for number in external_ids:
            try:
                issue = self.request_dict(
                    "GET", f"/repos/{destination}/issues/{number}"
                )
            except RemoteNotFoundError:
                out[number] = None
                continue
            except TrackerError:
                out[number] = RemoteStatus(name=UNREADABLE, category=None)
                continue
            out[number] = github_status(issue)
        return out
