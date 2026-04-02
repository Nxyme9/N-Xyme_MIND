"""
VPN Rotation System for ProtonVPN
Provides IP rotation across 8 free tier countries
"""
import os
import subprocess
import time
import logging
from typing import Optional, List
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Country:
    NL = "nl"
    JP = "jp"
    US = "us"
    CA = "ca"
    PL = "pl"
    RO = "ro"
    NO = "no"
    SE = "se"
    
    def __init__(self, code: str, name: str):
        self.code = code
        self.name = name
    
    @classmethod
    def from_code(cls, code: str) -> 'Country':
        code = code.lower()
        for c in cls.COUNTRIES:
            if c.code == code:
                return c
        raise ValueError(f"Unknown country code: {code}")
    
    @property
    def display_name(self) -> str:
        return self.name
    
    def __str__(self):
        return f"{self.code.upper()} ({self.name})"
    
    def __repr__(self):
        return f"Country.{self.code.upper()}"


Country.NL = Country("nl", "Netherlands")
Country.JP = Country("jp", "Japan")
Country.US = Country("us", "United States")
Country.CA = Country("ca", "Canada")
Country.PL = Country("pl", "Poland")
Country.RO = Country("ro", "Romania")
Country.NO = Country("no", "Norway")
Country.SE = Country("se", "Sweden")

Country.COUNTRIES = [Country.NL, Country.JP, Country.US, Country.CA,
                     Country.PL, Country.RO, Country.NO, Country.SE]


class VPNStatus:
    def __init__(self, connected: bool, country: Optional[Country],
                 ip_address: Optional[str], connection_name: str):
        self.connected = connected
        self.country = country
        self.ip_address = ip_address
        self.connection_name = connection_name
    
    def __repr__(self):
        return (f"VPNStatus(connected={self.connected}, "
                f"country={self.country}, ip={self.ip_address})")


def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"All {max_retries} attempts failed")
            raise last_exception
        return wrapper
    return decorator


class VPNRotator:
    """Manages ProtonVPN connections for IP rotation."""
    
    COUNTRIES = Country.COUNTRIES
    
    def __init__(self, data_dir: str = "~/.vpn-configs"):
        self.data_dir = os.path.expanduser(data_dir)
        self.current_index = 0
        self._ip_cache: Optional[str] = None
        self._last_check = 0
    
    @retry_with_backoff(max_retries=2, initial_delay=0.5)
    def _run_nmcli(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run nmcli command with error handling"""
        cmd = ["nmcli", "-t"] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0 and result.stderr:
                logger.error(f"nmcli error: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"nmcli timed out after {timeout}s")
    
    def list_connections(self) -> List[str]:
        """List all VPN connections"""
        result = self._run_nmcli("connection", "show")
        connections = []
        for line in result.stdout.strip().split('\n')[1:]:
            if 'vpn' in line.lower():
                name = line.split(':')[0]
                if name.startswith('ProtonVPN') or name.startswith('pvpn'):
                    connections.append(name)
        return connections
    
    def status(self) -> VPNStatus:
        """Get current VPN connection status."""
        result = self._run_nmcli("connection", "show")
        connected_name = None
        connected_device = None
        
        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.split(':')
            if len(parts) >= 3 and 'vpn' in line.lower():
                name = parts[0]
                if name.startswith('ProtonVPN'):
                    connected_name = name
                    device = parts[2]
                    if device and device != '--':
                        connected_device = device
                    break
        
        country = self._extract_country(connected_name) if connected_name else None
        
        if connected_device:
            ip_address = self.check_ip()
        else:
            ip_address = None
        
        return VPNStatus(
            connected=bool(connected_device),
            country=country,
            ip_address=ip_address,
            connection_name=connected_name or ""
        )
    
    def _extract_country(self, connection_name: str) -> Optional[Country]:
        """Extract country from connection name"""
        if not connection_name:
            return None
        for country in Country.COUNTRIES:
            if country.code.upper() in connection_name.upper():
                return country
        return None
    
    def check_ip(self, use_cache: bool = True, cache_ttl: int = 30) -> Optional[str]:
        """Check current IP address."""
        now = time.time()
        if use_cache and self._ip_cache and (now - self._last_check) < cache_ttl:
            return self._ip_cache
        
        services = [
            ("https://api.ipify.org?format=json", True),
            ("https://ifconfig.me/ip", False),
            ("https://icanhazip.com/", False),
        ]
        
        for service, is_json in services:
            try:
                import requests
                resp = requests.get(service, timeout=5)
                if is_json:
                    import json
                    self._ip_cache = json.loads(resp.text).get('ip')
                else:
                    self._ip_cache = resp.text.strip()
                self._last_check = now
                logger.info(f"Current IP: {self._ip_cache}")
                return self._ip_cache
            except Exception:
                continue
        
        logger.error("Failed to get IP from all services")
        return None
    
    def connect(self, country: Country, timeout: int = 30) -> bool:
        """Connect to a specific country."""
        existing = self.list_connections()
        connection_name = None
        matching = [c for c in existing if country.code.upper() in c.upper()]
        
        if matching:
            connection_name = matching[0]
            logger.info(f"Using existing connection: {connection_name}")
        else:
            logger.warning(f"No connection found for {country.name}")
            return False
        
        try:
            self._run_nmcli("connection", "down", connection_name)
        except RuntimeError:
            pass
        
        result = self._run_nmcli("connection", "up", connection_name)
        
        if result.returncode != 0:
            logger.error(f"Failed to connect: {result.stderr}")
            return False
        
        for _ in range(timeout):
            time.sleep(1)
            status = self.status()
            if status.connected:
                logger.info(f"Connected to {country.name}")
                return True
        
        logger.error(f"Connection timeout after {timeout}s")
        return False
    
    def rotate(self, target: Optional[Country] = None) -> bool:
        """Rotate to next country in sequence."""
        status = self.status()
        
        if target is None:
            if status.country in self.COUNTRIES:
                idx = self.COUNTRIES.index(status.country)
                self.current_index = (idx + 1) % len(self.COUNTRIES)
            target = self.COUNTRIES[self.current_index]
        
        logger.info(f"Rotating to {target.name}...")
        
        if status.connected and status.connection_name:
            self._run_nmcli("connection", "down", status.connection_name)
            time.sleep(2)
        
        result = self.connect(target)
        return result
    
    def disconnect(self) -> bool:
        """Disconnect current VPN."""
        status = self.status()
        if status.connected and status.connection_name:
            result = self._run_nmcli("connection", "down", status.connection_name)
            return result.returncode == 0
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VPN Rotator CLI")
    parser.add_argument("action", choices=["status", "rotate", "connect", "disconnect", "ip"],
                        help="Action to perform")
    parser.add_argument("--country", "-c", help="Country code (nl, jp, us, etc.)")
    
    args = parser.parse_args()
    rotator = VPNRotator()
    
    if args.action == "status":
        status = rotator.status()
        print(f"VPN Status:")
        print(f"  Connected: {status.connected}")
        print(f"  Country: {status.country.name if status.country else 'None'}")
        print(f"  IP: {status.ip_address or 'Unknown'}")
        print(f"  Connection: {status.connection_name}")
    
    elif args.action == "ip":
        ip = rotator.check_ip()
        print(f"Current IP: {ip}")
    
    elif args.action == "rotate":
        success = rotator.rotate()
        print(f"Rotation {'successful' if success else 'failed'}")
    
    elif args.action == "connect":
        if not args.country:
            print("--country required")
            exit(1)
        try:
            country = Country.from_code(args.country)
            success = rotator.connect(country)
            print(f"Connect {'successful' if success else 'failed'}")
        except ValueError as e:
            print(e)
            exit(1)
    
    elif args.action == "disconnect":
        success = rotator.disconnect()
        print(f"Disconnect {'successful' if success else 'failed'}")


if __name__ == "__main__":
    main()
