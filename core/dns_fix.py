import socket
import dns.resolver
import logging

logger = logging.getLogger(__name__)

# Keep reference to original getaddrinfo
_original_getaddrinfo = socket.getaddrinfo

def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # Only intervene for api.binance.com if it fails to resolve normally? 
    # Or always force it if we know it's problematic?
    # Let's try to resolve normally first, if it fails, try Google DNS.
    # Actually, the timeout for failure might be long, so parallel or force is better.
    # Given the user's issue, forcing it for binance is safer for now.
    
    if host == 'api.binance.com':
        try:
            # logger.info(f"Attempting to resolve {host} using Google DNS (8.8.8.8)...")
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
            answers = resolver.resolve(host, 'A')
            if answers:
                ip = answers[0].address
                # logger.info(f"Resolved {host} to {ip}")
                # Call original with IP instead of hostname
                return _original_getaddrinfo(ip, port, family, type, proto, flags)
        except Exception as e:
            logger.error(f"Custom DNS resolution failed for {host}: {e}")
            # Fallback to original
            pass
            
    return _original_getaddrinfo(host, port, family, type, proto, flags)

def apply_dns_fix():
    """Patches socket.getaddrinfo to use Google DNS for specific hosts."""
    socket.getaddrinfo = _custom_getaddrinfo
    print("Applied DNS fix for Binance API connectivity.")
