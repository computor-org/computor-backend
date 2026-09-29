"""Client information extraction utilities for IP and User-Agent."""

from typing import Optional
from fastapi import Request

# Configuration - set to True if behind a trusted proxy (Nginx, Traefik, Cloudflare)
TRUST_PROXY = True


def get_client_ip(request: Request) -> str:
    """
    Extract the best estimate of the real client IP address.
    
    Warning: X-Forwarded-For can be spoofed. Only trust if behind a trusted proxy.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address as string
    """
    if TRUST_PROXY:
        # RFC 7239 Forwarded header
        fwd = request.headers.get("forwarded")
        if fwd:
            # Example: 'for=203.0.113.195;proto=https;by=...'
            try:
                parts = [p.strip() for p in fwd.split(";")]
                for p in parts:
                    if p.lower().startswith("for="):
                        ip = p.split("=", 1)[1].strip().strip('"').strip("[]")
                        if ip:
                            return ip
            except (ValueError, IndexError):
                # Malformed Forwarded header — fall through to other detection.
                pass
        
        # X-Forwarded-For: first IP is the client
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Format: "client, proxy1, proxy2"
            first = xff.split(",")[0].strip()
            if first:
                return first
        
        # Cloudflare-specific header
        cf = request.headers.get("cf-connecting-ip")
        if cf:
            return cf
        
        # NGINX X-Real-IP
        xri = request.headers.get("x-real-ip")
        if xri:
            return xri
    
    # Fallback: direct socket IP (may be proxy)
    if request.client:
        return request.client.host
    return "0.0.0.0"


def get_user_agent(request: Request) -> str:
    """
    Extract User-Agent header.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User-Agent string or empty string
    """
    return request.headers.get("user-agent", "")


def make_device_label(user_agent: str) -> str:
    """
    Generate a human-readable device description.
    
    Examples:
    - 'Chrome 129 · Windows 11 · Desktop'
    - 'Mobile Safari 17 · iOS · iPhone'
    - 'Firefox 120 · Ubuntu · Desktop'
    
    Requires: pip install user-agents ua-parser
    
    Args:
        user_agent: Raw user-agent string
        
    Returns:
        Human-readable device description
    """
    if not user_agent:
        return "Unknown Device"
    
    try:
        from user_agents import parse as parse_ua
        
        ua = parse_ua(user_agent)
        
        # Browser info
        browser = " ".join([
            ua.browser.family or "Browser",
            ua.browser.version_string or ""
        ]).strip()
        
        # OS info
        os_name = " ".join([
            ua.os.family or "OS",
            ua.os.version_string or ""
        ]).strip()
        
        # Device type
        if ua.is_tablet:
            dev = "Tablet"
        elif ua.is_mobile:
            dev = "Mobile"
        elif ua.is_pc:
            dev = "Desktop"
        else:
            dev = "Device"
        
        # More specific device family if available
        dfam = getattr(ua.device, "family", None) or ""
        if dfam and dfam.lower() not in ("other", "generic smartphone", "generic feature phone"):
            dev = dfam
        
        label = f"{browser} · {os_name} · {dev}".replace("  ", " ").strip(" ·")
        return label
        
    except ImportError:
        # Fallback if user-agents library not installed
        return user_agent[:100]  # Truncate long user agents


# Direct peers whose X-Real-IP header is believed. Mirrors the Traefik
# ``forwardedHeaders.trustedIPs`` of the compose files: on computor.at nginx
# sets X-Real-IP to $remote_addr, Traefik (a trusted hop) keeps it, and the API
# port is only bound to 127.0.0.1. Override with TRUSTED_PROXY_CIDRS.
DEFAULT_TRUSTED_PROXY_CIDRS = "127.0.0.1/32,::1/128,172.16.0.0/12,192.168.0.0/16"


def _trusted_proxy_networks():
    import ipaddress
    import os

    raw = os.environ.get("TRUSTED_PROXY_CIDRS", DEFAULT_TRUSTED_PROXY_CIDRS)
    networks = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                networks.append(ipaddress.ip_network(part, strict=False))
            except ValueError:
                continue
    return networks


def trusted_client_ip(request: Request) -> str:
    """Client IP for security decisions (rate limits), not spoofable by the client.

    Unlike ``get_client_ip`` this never reads Forwarded / X-Forwarded-For,
    which the client controls. It uses X-Real-IP only when the direct TCP
    peer is a trusted proxy (which overwrites that header), else the peer.
    """
    import ipaddress

    peer = request.client.host if request.client else ""
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer or "unknown"
    if any(peer_ip in net for net in _trusted_proxy_networks()):
        real = (request.headers.get("x-real-ip") or "").strip()
        try:
            return str(ipaddress.ip_address(real))
        except ValueError:
            pass
    return str(peer_ip)
