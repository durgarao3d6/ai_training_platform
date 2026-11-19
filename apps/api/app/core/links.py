"""Link reachability checks for submitted links, guarded against SSRF (FR-SUB, task 4.2).

Interns choose these URLs, so the API must not be usable to probe internal services:
- only http and https, no credentials in the URL, standard ports only;
- every address the host resolves to must be public (no loopback, private, link-local,
  multicast, reserved or unspecified ranges, IPv4 or IPv6);
- redirects are followed manually (at most 3) and each hop is checked again;
- short timeouts; the response body is never read.

Residual risk: DNS can change between our check and the connection (rebinding). For the
prototype this is accepted; the planned hardening is to route link checks through the sandbox
egress proxy (Architecture 12.1).
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_REDIRECTS = 3
ALLOWED_PORTS = {None, 80, 443}


@dataclass(frozen=True)
class LinkCheck:
    ok: bool
    reason: str  # plain-language explanation shown to the intern when not ok
    status: int | None = None


def _public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(
        ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses
    )


def _url_problem(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        return "The link must start with http:// or https://."
    if parts.username or parts.password:
        return "The link must not contain a user name or password."
    if not parts.hostname:
        return "The link has no address."
    try:
        port = parts.port
    except ValueError:
        return "The link has an invalid port."
    if port not in ALLOWED_PORTS:
        return "The link must use the standard web ports."
    if not _public_host(parts.hostname):
        return "The link does not point to a public website."
    return None


def check_link(url: str, timeout: float) -> LinkCheck:
    current = url.strip()
    with httpx.Client(follow_redirects=False, timeout=timeout) as client:
        for _ in range(MAX_REDIRECTS + 1):
            problem = _url_problem(current)
            if problem:
                return LinkCheck(False, problem)
            try:
                response = client.head(current)
                if response.status_code in {
                    405,
                    501,
                }:  # HEAD not supported: GET without reading the body
                    with client.stream("GET", current) as streamed:
                        response = streamed
            except httpx.HTTPError:
                return LinkCheck(
                    False, "We could not reach this link. Check that it is correct and public."
                )
            if response.is_redirect and "location" in response.headers:
                current = urljoin(current, response.headers["location"])
                continue
            if response.status_code in {401, 403}:
                return LinkCheck(
                    False,
                    "The link needs a sign-in. Share it with view access.",
                    response.status_code,
                )
            if response.status_code >= 400:
                return LinkCheck(
                    False,
                    f"The link returned an error ({response.status_code}).",
                    response.status_code,
                )
            return LinkCheck(True, "Reachable", response.status_code)
    return LinkCheck(False, "The link redirects too many times.")
