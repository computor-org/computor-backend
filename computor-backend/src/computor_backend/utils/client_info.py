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
            except Exception:
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
