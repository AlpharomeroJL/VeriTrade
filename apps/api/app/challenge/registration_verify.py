"""Truthful checks for registration JSON hosting vs configured ERC-8004 bindings (no CA/B HTTPS claims)."""

from __future__ import annotations

import hashlib
import json
import socket
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.challenge.registration import (
    agent_registration_static_url,
    agent_uri_effective,
    build_agent_registration,
)
from app.config import Settings


def _fetch_json(url: str, timeout_sec: float = 3.0) -> tuple[bool, str, dict[str, Any] | None]:
    try:
        req = Request(url, headers={"User-Agent": "VeriTrade-registration-verify/1"})
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
        return True, "", json.loads(raw)
    except HTTPError as e:
        return False, f"http_{e.code}", None
    except URLError as e:
        return False, f"url_error:{e.reason!s}", None
    except json.JSONDecodeError as e:
        return False, f"json_error:{e}", None
    except Exception as e:
        return False, f"error:{e!s}", None


def _host(url: str) -> str | None:
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return None
        return p.netloc.lower()
    except Exception:
        return None


def observe_tls_for_https_url(url: str, timeout_sec: float = 4.0) -> dict[str, Any] | None:
    """
    When `url` is https, opens a TLS socket and returns negotiated version + peer cert digest.

    **Not** CA/B trust path proof, pinning, or DNSSEC — only what the local runtime observed.
    """
    p = urlparse(url)
    if (p.scheme or "").lower() != "https":
        return None
    host = p.hostname
    if not host:
        return {"ok": False, "error": "no_host", "url": url}
    port = int(p.port or 443)
    ctx = ssl.create_default_context()
    try:
        raw = socket.create_connection((host, port), timeout=timeout_sec)
    except Exception as e:
        return {"ok": False, "error": f"connect_failed:{e!s}", "host": host, "port": port}
    try:
        with ctx.wrap_socket(raw, server_hostname=host) as ssock:
            cert_der = ssock.getpeercert(binary_form=True) or b""
            ver = ssock.version()
            cipher = ssock.cipher()
    except Exception as e:
        try:
            raw.close()
        except Exception:
            pass
        return {"ok": False, "error": f"tls_failed:{e!s}", "host": host, "port": port}
    return {
        "ok": True,
        "host": host,
        "port": port,
        "tls_version_negotiated": ver,
        "cipher_suite": cipher[0] if cipher else None,
        "peer_certificate_sha256_hex": hashlib.sha256(cert_der).hexdigest() if cert_der else None,
        "note": "Runtime TLS observation only; does not prove domain control or CA policy.",
    }


def build_agent_registration_verification_report(settings: Settings) -> dict[str, Any]:
    """
    Best-effort, **honest** verification report.

    - Never claims CA-trusted HTTPS or DNSSEC.
    - `well_known_reachable` means the static file returned parseable JSON — not that it matches the API payload unless compared.
    """
    web_base = settings.veritrade_web_base_url.rstrip("/")
    api_base = settings.veritrade_api_base_url.rstrip("/")
    static_url = agent_registration_static_url(settings)
    api_url = f"{api_base}/challenge/agent-registration"

    ok_static, err_static, doc_static = _fetch_json(static_url)
    ok_api, err_api, doc_api = _fetch_json(api_url)

    expected_regs: list[dict[str, Any]] = []
    rid = (settings.erc8004_identity_registry_address or "").strip()
    aid = (settings.erc8004_onchain_agent_id or "").strip()
    if rid and aid:
        entry: dict[str, Any] = {"agentRegistry": rid, "agentId": aid}
        u = agent_uri_effective(settings)
        if u:
            entry["agentURI"] = u
        expected_regs = [entry]

    regs_match = None
    if doc_api is not None and expected_regs:
        regs_match = doc_api.get("registrations") == expected_regs

    same_host_static_vs_web = None
    h_web = _host(web_base)
    h_static = _host(static_url)
    if h_web and h_static:
        same_host_static_vs_web = h_web == h_static

    same_host_api_vs_web = None
    h_api = _host(api_base)
    if h_web and h_api:
        same_host_api_vs_web = h_web == h_api

    static_matches_api = None
    if doc_static is not None and doc_api is not None:
        static_matches_api = doc_static == doc_api

    # Effective registration the app would serve dynamically
    built = build_agent_registration(settings)

    registrations_agent_uri: dict[str, Any] | None = None
    regs_api = (doc_api or {}).get("registrations") if isinstance(doc_api, dict) else None
    if isinstance(regs_api, list) and regs_api and isinstance(regs_api[0], dict):
        uri = (regs_api[0].get("agentURI") or "").strip()
        if uri:
            ok_uri, err_uri, doc_uri = _fetch_json(uri)
            registrations_agent_uri = {
                "agent_uri": uri,
                "fetch_ok": ok_uri,
                "fetch_error": err_uri or None,
                "parsed_json": doc_uri is not None,
            }

    summary_bits: list[str] = []
    if ok_static:
        summary_bits.append("static_json_ok")
    else:
        summary_bits.append(f"static_json_fail:{err_static}")
    if ok_api:
        summary_bits.append("api_json_ok")
    else:
        summary_bits.append(f"api_json_fail:{err_api}")
    if same_host_static_vs_web is True:
        summary_bits.append("well_known_same_host_as_web_base")
    if static_matches_api is True:
        summary_bits.append("static_file_matches_api_payload")
    if regs_match is True:
        summary_bits.append("api_registrations_match_env_binding")

    label = "unverified"
    if ok_static and same_host_static_vs_web is True:
        label = "self_hosted_static_reachable_same_origin_as_web"
    if static_matches_api is True and regs_match is True:
        label = "static_and_api_aligned_with_env_registry_binding"

    return {
        "verification_label": label,
        "notes": [
            "HTTP-only localhost checks do not prove production domain control.",
            "Compare `GET /challenge/agent-registration` with `/.well-known/agent-registration.json` when both are reachable.",
            "When `ERC8004_IDENTITY_REGISTRY_ADDRESS` and `ERC8004_ONCHAIN_AGENT_ID` are set, `registrations_match_env` reflects API JSON only.",
        ],
        "urls": {
            "agent_registration_static": static_url,
            "agent_registration_api": api_url,
        },
        "fetch": {
            "static_ok": ok_static,
            "static_error": err_static or None,
            "api_ok": ok_api,
            "api_error": err_api or None,
        },
        "origin_checks": {
            "web_base_host": h_web,
            "static_registration_host": h_static,
            "api_base_host": h_api,
            "well_known_same_host_as_web_base": same_host_static_vs_web,
            "api_same_host_as_web_base": same_host_api_vs_web,
            "static_json_matches_api_json": static_matches_api,
        },
        "env_binding": {
            "expected_registrations_from_env": expected_regs or None,
            "api_registrations_match_env": regs_match,
        },
        "built_from_settings_without_fetch": built,
        "transport_observation": {
            "agent_registration_static": observe_tls_for_https_url(static_url),
            "agent_registration_api": observe_tls_for_https_url(api_url),
        },
        "registrations_agent_uri": registrations_agent_uri,
    }
