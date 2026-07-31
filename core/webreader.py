"""
Web Page Reader — fetch a public page and extract its readable text.

This is the "make an inaccessible webpage accessible" path: the user gives a
URL, AccessWeave fetches it server-side, strips the navigation/scripts/ads, and
hands the readable text to the Accessibility Compiler like any other source.

Security notes (this endpoint takes a user-supplied URL, so it is guarded):
  * only http/https schemes;
  * DNS is resolved and private/loopback/link-local ranges are refused, which
    blocks SSRF against localhost and cloud metadata endpoints;
  * a short timeout and a hard byte cap;
  * redirects are followed manually so every hop is re-validated;
  * the fetched HTML is never rendered — only text is extracted, so page
    scripts never execute. Extracted text is treated as DATA, not instructions.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 1_500_000
TIMEOUT = 8
MAX_REDIRECTS = 3
USER_AGENT = "AccessWeave/1.0 (accessibility reader)"


class FetchError(Exception):
    """Raised with a plain-language message safe to show the user."""


# Ranges that `ipaddress`'s own flags do not mark, but which should never be
# reachable from a user-supplied URL.
_EXTRA_BLOCKED = [
    ipaddress.ip_network("100.64.0.0/10"),    # RFC 6598 carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),    # RFC 2544 benchmarking
    ipaddress.ip_network("192.0.0.0/24"),     # IETF protocol assignments
]


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    # Unwrap IPv4-mapped IPv6 (::ffff:127.0.0.1) so the v4 flags apply.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
        return True
    return any(ip in net for net in _EXTRA_BLOCKED if net.version == ip.version)


def _validate(url: str) -> str:
    """Refuse anything that resolves somewhere it shouldn't.

    NOTE ON DNS REBINDING: the name is resolved here and resolved again by the
    connection itself, so a hostile DNS server could in principle return a public
    address to this check and a private one to the connection. Closing that fully
    requires pinning the socket to the validated IP. This is a known, documented
    residual risk (see docs/PRIVACY.md); the checks below stop every
    straightforward attempt, including redirects, which are re-validated per hop.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("Please use a web address starting with http:// or https://")
    if not parts.hostname:
        raise FetchError("That doesn't look like a complete web address.")
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror:
        raise FetchError("I couldn't find that website. Please check the address.")
    if not infos:
        raise FetchError("I couldn't find that website. Please check the address.")
    for info in infos:
        if _ip_is_blocked(ipaddress.ip_address(info[4][0])):
            raise FetchError("For safety, I can only open public websites.")
    return url


def fetch(url: str) -> tuple[str, str]:
    """Return (page_title, readable_text). Raises FetchError with a kind message."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    seen = 0
    while True:
        _validate(url)
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        })
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            resp = opener.open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and seen < MAX_REDIRECTS:
                loc = exc.headers.get("Location")
                if not loc:
                    raise FetchError("That website redirected somewhere I can't follow.")
                url = urllib.parse.urljoin(url, loc)
                seen += 1
                continue
            raise FetchError(f"The website returned an error ({exc.code}).")
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError):
            raise FetchError("I couldn't reach that website. Please check the address "
                             "or your connection.")
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" not in ctype and "text" not in ctype:
            raise FetchError("That link isn't a web page I can read as text.")
        raw = resp.read(MAX_BYTES)
        charset = resp.headers.get_content_charset() or "utf-8"
        try:
            markup = raw.decode(charset, errors="replace")
        except LookupError:
            markup = raw.decode("utf-8", errors="replace")
        return extract(markup)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface redirects as errors so each hop can be re-validated."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_DROP = re.compile(
    r"<(script|style|noscript|svg|iframe|nav|header|footer|form|aside|template)"
    r"\b[^>]*>.*?</\1>", re.I | re.S)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_MAIN = re.compile(r"<(?:main|article)\b[^>]*>(.*?)</(?:main|article)>", re.I | re.S)
_BLOCK = re.compile(r"</?(p|div|section|li|tr|h[1-6]|br)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")


def extract(markup: str) -> tuple[str, str]:
    """Strip a page down to a readable title + body text."""
    title_m = _TITLE.search(markup)
    title = html.unescape(_TAG.sub("", title_m.group(1))).strip() if title_m else ""

    body = _DROP.sub(" ", markup)
    main = _MAIN.search(body)
    if main:
        body = main.group(1)

    body = _BLOCK.sub("\n", body)
    body = _TAG.sub(" ", body)
    body = html.unescape(body)
    lines = []
    for line in body.splitlines():
        line = re.sub(r"[ \t\xa0]+", " ", line).strip()
        # keep substantive lines; drop menu-ish fragments
        if len(line) > 2:
            lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise FetchError("I couldn't find readable text on that page. It may need "
                         "JavaScript, or it may be mostly images.")
    return title[:200], text[:12000]
