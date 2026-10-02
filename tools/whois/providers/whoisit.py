"""RDAP provider using the whoisit library."""

import contextlib
import logging
import os
import threading
from typing import Any

import whoisit
from whoisit.errors import QueryError, UnsupportedError, WhoisItError

from shared.logging import get_logger

logger = get_logger(__name__)

for _name in ("bootstrap", "parser", "query", "utils"):
    _library_logger = logging.getLogger(_name)
    _library_logger.handlers.clear()
    _library_logger.setLevel(logging.WARNING)

_PROXY_ENV = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")
_PROXY_LOCK = threading.Lock()


class _BootstrapLock:
    """Shared for lookups, exclusive for bootstrap and refresh."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers = 0
        self._writing = False
        self._waiting = 0

    @contextlib.contextmanager
    def shared(self):
        with self._cond:
            self._cond.wait_for(lambda: not self._writing and not self._waiting)
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                if not self._readers:
                    self._cond.notify_all()

    @contextlib.contextmanager
    def exclusive(self):
        with self._cond:
            self._waiting += 1
            try:
                self._cond.wait_for(lambda: not self._writing and not self._readers)
            finally:
                self._waiting -= 1
            self._writing = True
        try:
            yield
        finally:
            with self._cond:
                self._writing = False
                self._cond.notify_all()


_BOOTSTRAP_LOCK = _BootstrapLock()


def _stale(max_age_days: int) -> bool:
    try:
        return whoisit.bootstrap_is_older_than(days=max_age_days)
    except WhoisItError:
        return True


class RDAPProviderError(Exception):
    """Raised when the RDAP provider encounters an error."""


class RDAPProvider:
    def __init__(self, proxy_url: str | None = None) -> None:
        self._proxy_url = proxy_url

    @contextlib.contextmanager
    def _proxied(self):
        """Route whoisit's requests through the proxy."""
        if not self._proxy_url:
            yield
            return
        with _PROXY_LOCK:
            previous = {name: os.environ.get(name) for name in _PROXY_ENV}
            for name in _PROXY_ENV:
                os.environ[name] = self._proxy_url
            try:
                yield
            finally:
                for name, value in previous.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    @property
    def is_bootstrapped(self) -> bool:
        return whoisit.is_bootstrapped()

    def _bootstrap(self) -> None:
        try:
            with self._proxied():
                whoisit.bootstrap(overrides=True)
            logger.info("RDAP bootstrap completed successfully")
        except WhoisItError as e:
            msg = f"Failed to bootstrap RDAP: {e}"
            raise RDAPProviderError(msg) from e

    def ensure_bootstrapped(self) -> None:
        """Bootstrap unless already bootstrapped."""
        if self.is_bootstrapped:
            return
        with _BOOTSTRAP_LOCK.exclusive():
            if not self.is_bootstrapped:
                self._bootstrap()

    def refresh_if_stale(self, max_age_days: int = 3) -> None:
        """Refresh bootstrap data if it's older than max_age_days."""
        if not _stale(max_age_days):
            return
        with _BOOTSTRAP_LOCK.exclusive():
            try:
                if not whoisit.bootstrap_is_older_than(days=max_age_days):
                    return
                saved = whoisit.save_bootstrap_data()
            except WhoisItError:
                self._bootstrap()
                return

            logger.info(
                f"RDAP bootstrap data older than {max_age_days} days, refreshing"
            )
            whoisit.clear_bootstrapping()
            try:
                self._bootstrap()
            except RDAPProviderError:
                if not self.is_bootstrapped:
                    whoisit.load_bootstrap_data(saved, overrides=True)
                raise

    def lookup_domain(self, domain: str) -> dict[str, Any]:
        """Look up WHOIS data for a domain."""
        try:
            self.ensure_bootstrapped()
            with _BOOTSTRAP_LOCK.shared(), self._proxied():
                return whoisit.domain(domain, allow_insecure_ssl=True)
        except RDAPProviderError:
            raise
        except UnsupportedError as e:
            msg = f"TLD not supported for RDAP lookup: {domain}"
            raise RDAPProviderError(msg) from e
        except QueryError as e:
            msg = f"RDAP query failed for domain {domain}: {e}"
            raise RDAPProviderError(msg) from e
        except Exception as e:
            msg = f"Unexpected error looking up domain {domain}: {e}"
            raise RDAPProviderError(msg) from e

    def lookup_ip(self, ip: str) -> dict[str, Any]:
        """Look up WHOIS data for an IP address or CIDR."""
        try:
            self.ensure_bootstrapped()
            with _BOOTSTRAP_LOCK.shared(), self._proxied():
                return whoisit.ip(ip, allow_insecure_ssl=True)
        except RDAPProviderError:
            raise
        except QueryError as e:
            msg = f"RDAP query failed for IP {ip}: {e}"
            raise RDAPProviderError(msg) from e
        except Exception as e:
            msg = f"Unexpected error looking up IP {ip}: {e}"
            raise RDAPProviderError(msg) from e

    def lookup_asn(self, asn: int) -> dict[str, Any]:
        """Look up WHOIS data for an ASN."""
        try:
            self.ensure_bootstrapped()
            with _BOOTSTRAP_LOCK.shared(), self._proxied():
                return whoisit.asn(asn, allow_insecure_ssl=True)
        except RDAPProviderError:
            raise
        except QueryError as e:
            msg = f"RDAP query failed for ASN {asn}: {e}"
            raise RDAPProviderError(msg) from e
        except Exception as e:
            msg = f"Unexpected error looking up ASN {asn}: {e}"
            raise RDAPProviderError(msg) from e
