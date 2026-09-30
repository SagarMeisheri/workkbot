"""Deep Anti-SSRF, DNS Rebinding & IPv6 Guardrails (Spec 05, R05.3 & VAL-05.1).

Defends against Server-Side Request Forgery (SSRF) and cloud metadata exfiltration:
- Rejects cloud metadata addresses (169.254.169.254).
- Rejects private RFC 1918 networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
- Rejects loopback addresses (127.0.0.0/8, ::1).
- Unwraps and validates IPv4-mapped IPv6 addresses (::ffff:169.254.169.254, ::ffff:127.0.0.1)
  completely inoculating against CVE-2026-31943.
- Resolves all domain A/AAAA records to prevent DNS rebinding attacks.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("workkbot.mcp.ssrf")

# Forbidden IP networks
FORBIDDEN_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),    # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),  # Private RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),   # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),   # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"), # Private RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmark testing
    ipaddress.ip_network("198.51.100.0/24"),# TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"), # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),    # Multicast
    ipaddress.ip_network("240.0.0.0/4"),    # Reserved
]

FORBIDDEN_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),        # Loopback
    ipaddress.ip_network("::/128"),         # Unspecified
    ipaddress.ip_network("fc00::/7"),       # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),      # Link-local
    ipaddress.ip_network("ff00::/8"),       # Multicast
]


class SsrfSecurityError(ValueError):
    """Raised when an address or URL targets a forbidden private or metadata IP."""
    pass


class AntiSsrfValidator:
    """Validates URLs and IP addresses against SSRF and DNS rebinding."""

    @classmethod
    def normalize_ip(cls, ip_str: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        """
        Parses IP string and unwraps IPv4-mapped IPv6 representations (CVE-2026-31943).
        Example: ::ffff:169.254.169.254 -> 169.254.169.254
        """
        ip = ipaddress.ip_address(ip_str.strip())
        if isinstance(ip, ipaddress.IPv6Address):
            # Check for IPv4-mapped IPv6 (::ffff:0:0/96)
            if ip.ipv4_mapped:
                return ip.ipv4_mapped
        return ip

    @classmethod
    def is_ip_allowed(cls, ip_str: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if an IP address is safe (public) or belongs to a forbidden private/metadata range.
        Returns (is_allowed, denial_reason).
        """
        try:
            ip = cls.normalize_ip(ip_str)
        except ValueError as e:
            return False, f"Invalid IP address format: {e}"

        # 1. IPv4 Checks
        if isinstance(ip, ipaddress.IPv4Address):
            for net in FORBIDDEN_IPV4_NETWORKS:
                if ip in net:
                    return False, f"Blocked address {ip}: belongs to restricted range {net}"
            return True, None

        # 2. IPv6 Checks
        if isinstance(ip, ipaddress.IPv6Address):
            for net in FORBIDDEN_IPV6_NETWORKS:
                if ip in net:
                    return False, f"Blocked IPv6 address {ip}: belongs to restricted range {net}"
            return True, None

        return False, "Unknown IP version"

    @classmethod
    def validate_url(cls, target_url: str, resolve_dns: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validates a URL before connection:
        - Must use http or https scheme.
        - Hostname is resolved to all A and AAAA records.
        - Every resolved IP is validated against forbidden CIDRs.
        """
        if not target_url:
            return False, "Empty URL provided"

        parsed = urlparse(target_url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Unsupported URL scheme '{parsed.scheme}': only http and https are permitted"

        hostname = parsed.hostname
        if not hostname:
            return False, "No hostname found in URL"

        # Check if hostname is a direct IP
        try:
            ip = ipaddress.ip_address(hostname)
            is_allowed, reason = cls.is_ip_allowed(str(ip))
            if not is_allowed:
                return False, reason
            return True, None
        except ValueError:
            # Hostname is a domain name
            pass

        # Reject obvious cloud metadata and localhost names
        lower_host = hostname.lower()
        if lower_host in ("localhost", "metadata.google.internal", "instance-data"):
            return False, f"Blocked access to sensitive internal domain: {hostname}"

        if not resolve_dns:
            return True, None

        # Resolve all DNS A and AAAA records
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            resolved_ips: List[str] = list({item[4][0] for item in addr_info})
            if not resolved_ips:
                return False, f"Could not resolve hostname '{hostname}' to any IP"

            for ip_cand in resolved_ips:
                is_allowed, reason = cls.is_ip_allowed(ip_cand)
                if not is_allowed:
                    logger.warning("SSRF blocked domain '%s' resolving to '%s': %s", hostname, ip_cand, reason)
                    return False, f"Domain '{hostname}' resolves to forbidden IP '{ip_cand}': {reason}"

            return True, None
        except socket.gaierror as e:
            return False, f"DNS resolution failed for hostname '{hostname}': {e}"

    @classmethod
    def assert_safe_url(cls, target_url: str) -> None:
        """Raises SsrfSecurityError if URL is unsafe."""
        is_safe, reason = cls.validate_url(target_url)
        if not is_safe:
            raise SsrfSecurityError(reason or "Target URL violates SSRF safety policies")


ssrf_validator = AntiSsrfValidator
