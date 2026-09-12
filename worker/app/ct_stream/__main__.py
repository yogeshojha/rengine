"""Run certspotter over the watched apexes and hand every certificate to the worker."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

import redis

from app.config import settings
from app.database import get_sync_session
from shared.definitions.watch import (
    CT_CERT_RETENTION_DAYS,
    CT_POLL_SECONDS,
    CT_STATUS_KEY,
    CT_STATUS_TTL,
    WatchItem,
)
from shared.logging import get_logger
from shared.services import watch_sync
from shared.services.celery_dispatch import dispatch_watch_certificate
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

STATE_DIR = Path(os.environ.get("CT_STATE_DIR", "/app/ct-state"))
SPOOL_DIR = STATE_DIR / "spool"
CERT_DIR = STATE_DIR / "certspotter"
WATCHLIST = STATE_DIR / "watchlist"
HOOK = Path(__file__).with_name("hook.sh")
BINARY = shutil.which("certspotter") or "certspotter"
HEALTHCHECK = "1h"
STOP_GRACE_SECONDS = 10
PRUNE_SECONDS = 3600
FAST_EXIT_SECONDS = 60
MAX_BACKOFF_SECONDS = 600
FAST_EXIT_LIMIT = 3


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            out[key] = value
    return out


def _names_for(event: dict[str, str]) -> list[str]:
    raw = event.get("JSON_FILENAME")
    if raw:
        try:
            data = json.loads(Path(raw).read_text(errors="replace"))
            names = data.get("dns_names") or []
            if names:
                return [str(n) for n in names]
        except (OSError, ValueError):
            pass
    subject = event.get("SUBJECT_DN") or ""
    for part in subject.split(","):
        key, sep, value = part.strip().partition("=")
        if sep and key.upper() == "CN" and value:
            return [value]
    return []


class Supervisor:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.items: list[str] = []
        self.started_at: datetime | None = None
        self.certs_seen = 0
        self.last_certificate_at: datetime | None = None
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self.version = self._version()
        self.fast_exits = 0
        self.restart_after = 0.0
        self.started_mono = 0.0
        self._redis = redis.from_url(settings.redis_url)
        for path in (SPOOL_DIR, CERT_DIR):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _version() -> str | None:
        try:
            out = subprocess.run(  # noqa: S603
                [BINARY, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return (out.stdout or out.stderr).strip().splitlines()[0][:80]
        except (OSError, subprocess.SubprocessError, IndexError):
            return None

    # ---------- watchlist ----------

    def _items_from_db(self) -> list[str]:
        with get_sync_session() as session:
            rows = [w.watch_items for w in watch_sync.active_watches(session)]
        items: set[str] = set()
        for raw in rows:
            for entry in raw or []:
                item = WatchItem.from_dict(entry).item
                if item:
                    items.add(item)
        return sorted(items)

    def _write_watchlist(self, items: list[str]) -> bool:
        body = "\n".join(items) + ("\n" if items else "")
        current = WATCHLIST.read_text() if WATCHLIST.exists() else None
        if current == body:
            return False
        tmp = WATCHLIST.with_suffix(".tmp")
        tmp.write_text(body)
        tmp.replace(WATCHLIST)
        return True

    # ---------- process ----------

    def _running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _start(self) -> None:
        cmd = [
            BINARY,
            "-watchlist",
            str(WATCHLIST),
            "-state_dir",
            str(CERT_DIR),
            "-script",
            str(HOOK),
            "-start_at_end",
            "-healthcheck",
            HEALTHCHECK,
        ]
        env = {**os.environ, "CT_SPOOL_DIR": str(SPOOL_DIR)}
        try:
            self.proc = subprocess.Popen(cmd, env=env)  # noqa: S603
        except OSError as exc:
            self.proc = None
            self.last_error = f"certspotter did not start: {exc}"[:500]
            self.last_error_at = utc_now()
            self.restart_after = time.monotonic() + MAX_BACKOFF_SECONDS
            logger.warning("certspotter did not start", error=str(exc))
            return
        self.started_at = utc_now()
        self.started_mono = time.monotonic()
        logger.info("certspotter started", pid=self.proc.pid, items=len(self.items))

    def _stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=STOP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        self.started_at = None

    # ---------- spool ----------

    def _drain(self) -> None:
        for path in sorted(SPOOL_DIR.glob("*.env")):
            try:
                done = self._handle(_parse_env(path))
            except Exception:
                logger.warning("spool entry failed", path=str(path), exc_info=True)
                done = True
            if done:
                path.unlink(missing_ok=True)

    def _handle(self, event: dict[str, str]) -> bool:
        """True when the entry is consumed; a failed dispatch keeps it for the next tick."""
        kind = event.get("EVENT")
        if kind == "discovered_cert":
            names = _names_for(event)
            if not names:
                return True
            cert = {
                "names": names,
                "sha256": event.get("CERT_SHA256"),
                "issuer": event.get("ISSUER_DN"),
                "not_before": event.get("NOT_BEFORE_RFC3339"),
                "not_after": event.get("NOT_AFTER_RFC3339"),
                "log": event.get("LOG_URI"),
                "watch_item": event.get("WATCH_ITEM"),
            }
            if not dispatch_watch_certificate(cert):
                self.last_error = "Certificate not queued. Check that redis is running."
                self.last_error_at = utc_now()
                return False
            self.certs_seen += 1
            self.last_certificate_at = utc_now()
            self.last_error = None
            self.last_error_at = None
            return True
        summary = (event.get("SUMMARY") or kind or "certspotter error")[:500]
        self.last_error = summary
        self.last_error_at = utc_now()
        logger.warning("certspotter event", summary=summary)
        return True

    def _prune(self) -> None:
        cutoff = time.time() - CT_CERT_RETENTION_DAYS * 86400
        saved = CERT_DIR / "certs"
        if not saved.exists():
            return
        for path in saved.rglob("*"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue

    # ---------- status ----------

    def _publish(self) -> None:
        payload = {
            "running": self._running(),
            "items": len(self.items),
            "started_at": _iso(self.started_at),
            "updated_at": _iso(utc_now()),
            "last_certificate_at": _iso(self.last_certificate_at),
            "certificates_seen": self.certs_seen,
            "last_error": self.last_error,
            "last_error_at": _iso(self.last_error_at),
            "version": self.version,
        }
        try:
            self._redis.set(CT_STATUS_KEY, json.dumps(payload), ex=CT_STATUS_TTL)
        except redis.RedisError:
            logger.warning("stream status not written", exc_info=True)

    # ---------- loop ----------

    def _note_exit(self) -> None:
        """Back off when certspotter keeps exiting right after start."""
        if self.proc is None or self.proc.poll() is None:
            return
        code = self.proc.returncode
        if time.monotonic() - self.started_mono < FAST_EXIT_SECONDS:
            self.fast_exits += 1
        else:
            self.fast_exits = 0
        self.proc = None
        self.started_at = None
        if self.fast_exits >= FAST_EXIT_LIMIT:
            delay = min(MAX_BACKOFF_SECONDS, CT_POLL_SECONDS * 2**self.fast_exits)
            self.restart_after = time.monotonic() + delay
            self.last_error = (
                f"certspotter exited with code {code} {self.fast_exits} times in a row."
            )
            self.last_error_at = utc_now()
            logger.warning("certspotter exit loop", code=code, delay=delay)

    def tick(self) -> None:
        self._note_exit()
        try:
            items = self._items_from_db()
        except Exception:
            logger.warning("watch items not read", exc_info=True)
            items = self.items
        changed = self._write_watchlist(items)
        self.items = items
        if not items:
            if self._running():
                logger.info("no watched apexes, certspotter stopped")
            self._stop()
        elif changed or not self._running():
            if self._running():
                logger.info("watchlist changed, restarting certspotter")
                self.fast_exits = 0
            if time.monotonic() >= self.restart_after:
                self._stop()
                self._start()
        self._drain()
        self._publish()

    def run(self) -> None:
        last_prune = 0.0
        stopping = False

        def _term(*_args) -> None:
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, _term)
        signal.signal(signal.SIGINT, _term)
        while not stopping:
            self.tick()
            if time.time() - last_prune > PRUNE_SECONDS:
                self._prune()
                last_prune = time.time()
            deadline = time.time() + CT_POLL_SECONDS
            while not stopping and time.time() < deadline:
                time.sleep(1)
        self._stop()
        self._drain()


if __name__ == "__main__":
    Supervisor().run()
