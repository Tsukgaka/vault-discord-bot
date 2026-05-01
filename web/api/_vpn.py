"""A"""
import requests


PRIVATE_PREFIXES = ("10.", "192.168.", "127.", "::1")


def is_private_ip(ip: str) -> bool:
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES) or ip.startswith("172.1") or ip.startswith("172.2") or ip.startswith("172.3")


def check_ip(ip: str) -> dict:
    """Check IP using ip-api.com (free, 45 req/min)"""
    if is_private_ip(ip):
        return {"is_vpn": False, "is_proxy": False, "is_hosting": False, "country": "LOCAL"}

    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,proxy,hosting,country,isp"},
            timeout=3,
        )
        data = resp.json()
        return {
            "is_vpn": data.get("proxy", False) or data.get("hosting", False),
            "is_proxy": data.get("proxy", False),
            "is_hosting": data.get("hosting", False),
            "country": data.get("country", ""),
        }
    except Exception:
        # Fail open — don't block if API is down
        return {"is_vpn": False, "is_proxy": False, "is_hosting": False, "country": ""}


def get_client_ip(environ: dict) -> str:
    """Extract real IP from Vercel/WSGI environ"""
    return (
        environ.get("HTTP_X_REAL_IP")
        or (environ.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip())
        or environ.get("REMOTE_ADDR", "127.0.0.1")
    )
