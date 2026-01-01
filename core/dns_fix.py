
import socket
import requests
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DNS_FIX")

# Save original getaddrinfo
_original_getaddrinfo = socket.getaddrinfo

# Cache for resolved IPs to avoid spamming DoH
_dns_cache = {}
_cache_lock = threading.Lock()

def _resolve_via_doh(host):
    """
    Resolve hostname using Google DNS over HTTPS (8.8.8.8).
    Returns a list of IP strings.
    """
    try:
        # Check cache first
        with _cache_lock:
            if host in _dns_cache:
                return _dns_cache[host]

        # Use 8.8.8.8 directly to avoid DNS resolution for the resolver itself
        url = f"https://8.8.8.8/resolve?name={host}&type=A"
        
        # Verify=False because we are using IP in URL and cert matches dns.google
        # We suppress warnings to keep logs clean
        try:
            from urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        except:
            pass
            
        response = requests.get(url, verify=False, timeout=3)
        data = response.json()
        
        ips = []
        if 'Answer' in data:
            for answer in data['Answer']:
                # Type 1 is A Record (IPv4)
                if answer['type'] == 1:
                    ips.append(answer['data'])
        
        if ips:
            logger.info(f"[DNS_FIX] Resolved {host} via DoH to: {ips}")
            with _cache_lock:
                _dns_cache[host] = ips
            return ips
            
    except Exception as e:
        logger.error(f"[DNS_FIX] DoH Resolution failed for {host}: {e}")
    
    return []

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Custom getaddrinfo that falls back to DoH if system DNS fails
    or if the host is a known blocked domain (Binance).
    """
    # List of domains to force DoH for (optimization + bypass)
    FORCE_DOH_DOMAINS = ['api.binance.com', 'api1.binance.com', 'api2.binance.com', 'api3.binance.com', 'binance.com']
    
    use_doh = False
    
    # Check if we should force DoH
    if host and isinstance(host, str):
        for domain in FORCE_DOH_DOMAINS:
            if domain in host:
                use_doh = True
                break
    
    # Try System DNS first unless forced
    if not use_doh:
        try:
            return _original_getaddrinfo(host, port, family, type, proto, flags)
        except socket.gaierror:
            # Fallback to DoH
            pass
            
    # DoH Logic
    if host and isinstance(host, str):
        ips = _resolve_via_doh(host)
        if ips:
            results = []
            for ip in ips:
                # Create a socket address tuple (ip, port)
                # family=AF_INET (2), type=SOCK_STREAM (1) usually
                # We return multiple permutations if family/type are 0 (any)
                
                # Default to TCP/IPv4
                af = socket.AF_INET
                socktype = socket.SOCK_STREAM
                
                # Respect requested family/type if specific
                if family != 0 and family != socket.AF_INET:
                    continue # We only support IPv4 via DoH for now
                
                sockaddr = (ip, port)
                
                # Append result: (family, type, proto, canonname, sockaddr)
                results.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', sockaddr))
                
            if results:
                return results

    # If DoH failed or returned no results, try original (or raise original error)
    return _original_getaddrinfo(host, port, family, type, proto, flags)

def apply_fix():
    """Apply the socket patch"""
    if socket.getaddrinfo != custom_getaddrinfo:
        socket.getaddrinfo = custom_getaddrinfo
        print("[DNS_FIX] DNS Patch Applied successfully.")
    else:
        print("[DNS_FIX] DNS Patch already active.")

# Auto-apply on import
apply_fix()
