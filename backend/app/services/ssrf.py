"""SSRF guard for user-supplied import URLs.

Every URL a user pastes for a URL-import project MUST pass
:func:`validate_public_url` before any network fetch. It rejects
non-HTTP(S) schemes and any URL whose host resolves to a private,
loopback, link-local, multicast, or otherwise reserved address.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from app.config import settings
from app.exceptions import ValidationError

logger = logging.getLogger("segmently.services.ssrf")

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}
# Common cloud metadata endpoints - always blocked regardless of resolution.
_BLOCKED_LITERALS = {"169.254.169.254", "fd00:ec2::254"}


def _is_disallowed_ip(ip: ipaddress._BaseAddress) -> bool:
    """Return ``True`` if *ip* is not a routable public address."""
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _resolve_addresses(host: str) -> list[str]:
    """Resolve *host* to the set of IP strings it points at."""
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValidationError(f"Could not resolve host '{host}'") from exc
    return sorted({info[4][0] for info in infos})


def validate_public_url(url: str) -> str:
    """Validate that *url* is safe to fetch server-side.

    Args:
        url: The user-supplied URL.

    Returns:
        The normalised URL string (unchanged) when it is safe.

    Raises:
        ValidationError: If the scheme is unsupported, the host is missing,
            or the host resolves to a non-public address range.
    """
    parsed = urlparse(url.strip())

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValidationError("Only http and https URLs are supported")

    host = parsed.hostname
    if not host:
        raise ValidationError("URL is missing a host")

    if settings.SSRF_ALLOW_PRIVATE:  # pragma: no cover - dev escape hatch
        logger.warning("SSRF_ALLOW_PRIVATE is on - skipping private-range check for %s", host)
        return url

    lowered = host.lower()
    if lowered in _BLOCKED_HOSTNAMES or lowered in _BLOCKED_LITERALS:
        raise ValidationError("URL host is not allowed")

    # If the host is an IP literal, check it directly.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _is_disallowed_ip(literal):
            raise ValidationError("URL points at a non-public address")
        return url

    for addr in _resolve_addresses(host):
        if addr in _BLOCKED_LITERALS:
            raise ValidationError("URL host is not allowed")
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:  # pragma: no cover - defensive
            raise ValidationError("URL resolved to an invalid address") from None
        if _is_disallowed_ip(ip):
            logger.warning("Blocked SSRF attempt: %s -> %s", host, addr)
            raise ValidationError("URL resolves to a private or reserved address")

    return url
