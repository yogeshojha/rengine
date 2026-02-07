"""RDAP provider using the whoisit library.

README: https://github.com/meeb/whoisit/blob/main/README.md

"""

from typing import Any

import whoisit
from whoisit.errors import BootstrapError, QueryError, UnsupportedError

from shared.logging import get_logger

logger = get_logger(__name__)


class RDAPProviderError(Exception):
    """Raised when the RDAP provider encounters an error."""


class RDAPProvider:
    def __init__(self) -> None:
        self._bootstrap_data: str | None = None

    @property
    def is_bootstrapped(self) -> bool:
        return whoisit.is_bootstrapped()

    def bootstrap(self, overrides: bool = True) -> None:
        try:
            whoisit.bootstrap(overrides=overrides)
            self._bootstrap_data = whoisit.save_bootstrap_data()
            logger.info("RDAP bootstrap completed successfully")
        except BootstrapError as e:
            msg = f"Failed to bootstrap RDAP: {e}"
            raise RDAPProviderError(msg) from e

    def ensure_bootstrapped(self) -> None:
        """Ensured bootstrapped."""
        if self.is_bootstrapped:
            return

        if self._bootstrap_data:
            try:
                whoisit.load_bootstrap_data(self._bootstrap_data, overrides=True)
                logger.debug("RDAP bootstrap restored from cache")
                return
            except BootstrapError:
                logger.warning("Failed to restore cached bootstrap data, re-fetching")
                self._bootstrap_data = None

        self.bootstrap()

    def refresh_if_stale(self, max_age_days: int = 3) -> None:
        """Refresh bootstrap data if it's older than max_age_days.

        Args:
            max_age_days: Maximum age of bootstrap data in days.
        """
        if not self.is_bootstrapped:
            self.bootstrap()
            return

        try:
            if whoisit.bootstrap_is_older_than(days=max_age_days):
                logger.info(
                    f"RDAP bootstrap data older than {max_age_days} days, refreshing"
                )
                whoisit.clear_bootstrapping()
                self.bootstrap()
        except BootstrapError:
            self.bootstrap()

    def save_bootstrap_data(self) -> str | None:
        if not self.is_bootstrapped:
            return None
        try:
            return whoisit.save_bootstrap_data()
        except BootstrapError:
            return None

    def load_bootstrap_data(self, data: str) -> None:
        try:
            whoisit.load_bootstrap_data(data, overrides=True)
            self._bootstrap_data = data
            logger.debug("RDAP bootstrap data loaded from external source")
        except BootstrapError as e:
            msg = f"Failed to load bootstrap data: {e}"
            raise RDAPProviderError(msg) from e

    def lookup_domain(self, domain: str) -> dict[str, Any]:
        """Look up WHOIS data for a domain.

        Args:
            domain: Domain name (e.g. "example.com"), a valid domain name

        Returns:
            Raw parsed dict from whoisit.

        Raises:
            RDAPProviderError: On lookup failure.
        """
        self.ensure_bootstrapped()
        try:
            return whoisit.domain(domain, allow_insecure_ssl=True)
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
        """Look up WHOIS data for an IP address or CIDR.

        Args:
            ip: IP address or CIDR (e.g. "1.1.1.1", "1.1.1.0/24", "2001:db8::/32").

        Returns:
            Raw parsed dict from whoisit.

        Raises:
            RDAPProviderError: On lookup failure.
        """
        self.ensure_bootstrapped()
        try:
            return whoisit.ip(ip, allow_insecure_ssl=True)
        except QueryError as e:
            msg = f"RDAP query failed for IP {ip}: {e}"
            raise RDAPProviderError(msg) from e
        except Exception as e:
            msg = f"Unexpected error looking up IP {ip}: {e}"
            raise RDAPProviderError(msg) from e

    def lookup_asn(self, asn: int) -> dict[str, Any]:
        """Look up WHOIS data for an ASN.

        Args:
            asn: Autonomous System Number (e.g. 13335).

        Returns:
            Raw parsed dict from whoisit.

        Raises:
            RDAPProviderError: On lookup failure.
        """
        self.ensure_bootstrapped()
        try:
            return whoisit.asn(asn, allow_insecure_ssl=True)
        except QueryError as e:
            msg = f"RDAP query failed for ASN {asn}: {e}"
            raise RDAPProviderError(msg) from e
        except Exception as e:
            msg = f"Unexpected error looking up ASN {asn}: {e}"
            raise RDAPProviderError(msg) from e
