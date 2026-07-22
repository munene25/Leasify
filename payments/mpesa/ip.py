"""
We need a way to filter out MPESA IPs.
"""

import ipaddress

MPESA_SUBNETS = [
    ipaddress.ip_network("196.201.214.0/24"),
    ipaddress.ip_network("196.201.213.0/24"),
    ipaddress.ip_network("196.201.212.0/24"),
]


def is_mpesa_ip(request) -> bool:
    """Check if request originates from M-Pesa servers."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    ip = ip.split(",")[0].strip()
    try:
        ip_addr = ipaddress.ip_address(ip)
        return any(ip_addr in subnet for subnet in MPESA_SUBNETS)
    except ValueError:
        return False