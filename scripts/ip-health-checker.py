#!/usr/bin/env python3
"""
IP Health Checker - Comprehensive network diagnostics.
Checks public IP, reputation, geolocation, and connectivity.
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import requests

# --- Config ---
TIMEOUT = 10  # seconds per request
CONNECTIVITY_TARGETS = [
    ("Google DNS", "https://dns.google/resolve?name=google.com"),
    ("Cloudflare", "https://1.1.1.1/cdn-cgi/trace"),
    ("GitHub", "https://api.github.com"),
    ("Wikipedia", "https://en.wikipedia.org"),
]


@dataclass
class CheckResult:
    name: str
    status: str  # "ok", "warn", "fail"
    detail: str
    data: dict = field(default_factory=dict)


def get_public_ip() -> CheckResult:
    """Get current public IP from multiple sources (fallback chain)."""
    sources = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    for url in sources:
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            text = resp.text.strip()
            # Some sources return plain text, some JSON
            if text.startswith("{"):
                ip = json.loads(text).get("ip", text)
            else:
                ip = text
            return CheckResult("Public IP", "ok", ip, {"ip": ip})
        except (requests.RequestException, json.JSONDecodeError):
            continue
    return CheckResult("Public IP", "fail", "Could not determine public IP")


def check_ip_reputation(ip: str) -> CheckResult:
    """Check IP reputation via AbuseIPDB (free tier, no key needed for basic check)."""
    # Use ip-api.com abuse check as lightweight alternative
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,message,proxy,hosting",
            timeout=TIMEOUT,
        )
        data = resp.json()
        if data.get("status") != "success":
            return CheckResult("IP Reputation", "warn", "Could not check reputation")

        flags = []
        if data.get("proxy"):
            flags.append("Proxy/VPN detected")
        if data.get("hosting"):
            flags.append("Hosting/datacenter IP")

        if flags:
            return CheckResult("IP Reputation", "warn", "; ".join(flags), data)
        return CheckResult("IP Reputation", "ok", "Clean - residential IP", data)
    except Exception as e:
        return CheckResult("IP Reputation", "warn", f"Check failed: {e}")


def get_ip_location(ip: str) -> CheckResult:
    """Get IP geolocation via ip-api.com (free, no key)."""
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,timezone,lat,lon",
            timeout=TIMEOUT,
        )
        data = resp.json()
        if data.get("status") != "success":
            return CheckResult("Geolocation", "fail", data.get("message", "Unknown error"))

        loc = f"{data.get('city', '?')}, {data.get('regionName', '?')}, {data.get('country', '?')}"
        detail = (
            f"{loc} | ISP: {data.get('isp', '?')} | "
            f"AS: {data.get('as', '?')} | TZ: {data.get('timezone', '?')}"
        )
        return CheckResult("Geolocation", "ok", detail, data)
    except Exception as e:
        return CheckResult("Geolocation", "fail", f"Lookup failed: {e}")


def test_connectivity() -> list[CheckResult]:
    """Test connectivity to key services in parallel."""
    results = []

    def check(name: str, url: str) -> CheckResult:
        try:
            start = time.monotonic()
            resp = requests.get(url, timeout=TIMEOUT)
            elapsed = time.monotonic() - start
            if resp.status_code < 400:
                return CheckResult(name, "ok", f"{resp.status_code} ({elapsed:.2f}s)")
            return CheckResult(name, "warn", f"HTTP {resp.status_code} ({elapsed:.2f}s)")
        except requests.ConnectionError:
            return CheckResult(name, "fail", "Connection refused")
        except requests.Timeout:
            return CheckResult(name, "fail", f"Timeout (>{TIMEOUT}s)")
        except Exception as e:
            return CheckResult(name, "fail", str(e))

    with ThreadPoolExecutor(max_workers=len(CONNECTIVITY_TARGETS)) as pool:
        futures = {pool.submit(check, name, url): name for name, url in CONNECTIVITY_TARGETS}
        for future in as_completed(futures):
            results.append(future.result())

    return sorted(results, key=lambda r: r.name)


def check_dns() -> CheckResult:
    """Quick DNS resolution test."""
    try:
        resp = requests.get(
            "https://dns.google/resolve?name=example.com&type=A",
            timeout=TIMEOUT,
        )
        data = resp.json()
        if data.get("Status") == 0:
            answers = [a["data"] for a in data.get("Answer", [])]
            return CheckResult("DNS Resolution", "ok", f"Resolved: {', '.join(answers[:3])}")
        return CheckResult("DNS Resolution", "fail", f"Status {data.get('Status')}")
    except Exception as e:
        return CheckResult("DNS Resolution", "fail", str(e))


def check_ipv6() -> CheckResult:
    """Check IPv6 connectivity."""
    try:
        resp = requests.get("https://api64.ipify.org?format=json", timeout=TIMEOUT)
        ipv6 = resp.json().get("ip", "")
        if ":" in ipv6:
            return CheckResult("IPv6", "ok", ipv6)
        return CheckResult("IPv6", "warn", f"Not available (got {ipv6})")
    except requests.RequestException:
        return CheckResult("IPv6", "warn", "Not reachable")


# --- Display ---

STATUS_ICONS = {"ok": "[OK]", "warn": "[!!]", "fail": "[XX]"}


def print_result(r: CheckResult):
    icon = STATUS_ICONS.get(r.status, "[??]")
    print(f"  {icon} {r.name:<22} {r.detail}")


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def run_all_checks():
    print_header("IP HEALTH CHECKER")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Public IP
    print_header("1. Public IP")
    ip_result = get_public_ip()
    print_result(ip_result)
    if ip_result.status == "fail":
        print("\n  Cannot proceed without public IP. Check your connection.")
        sys.exit(1)

    ip = ip_result.data.get("ip", "")

    # 2. Geolocation
    print_header("2. Geolocation")
    print_result(get_ip_location(ip))

    # 3. Reputation
    print_header("3. IP Reputation")
    print_result(check_ip_reputation(ip))

    # 4. DNS
    print_header("4. DNS Resolution")
    print_result(check_dns())

    # 5. IPv6
    print_header("5. IPv6 Connectivity")
    print_result(check_ipv6())

    # 6. Connectivity
    print_header("6. Service Connectivity")
    for r in test_connectivity():
        print_result(r)

    # Summary
    print_header("SUMMARY")
    print(f"  IP: {ip}")
    print(f"  All checks complete.\n")


if __name__ == "__main__":
    run_all_checks()
