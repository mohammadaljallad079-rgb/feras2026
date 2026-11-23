"""The reverse-proxy contract that a deployment must not break.

Nginx cannot be executed in the test environment, so these checks read the
configuration and the compose file instead of starting a proxy. They lock the
routing decisions that make the single-origin deployment work: `/api` reaching
FastAPI, everything else reaching Next.js, and the probes answered directly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deploy" / "nginx.conf"
COMPOSE = ROOT / "docker-compose.yml"


@pytest.fixture(scope="module")
def nginx_conf() -> str:
    return NGINX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def compose() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def _location_block(conf: str, pattern: str) -> str:
    """Return the body of the first `location <pattern>` block."""
    match = re.search(rf"location\s+{re.escape(pattern)}\s*\{{(.*?)\n    \}}", conf, re.S)
    assert match, f"no `location {pattern}` block in deploy/nginx.conf"
    return match.group(1)


def test_the_api_prefix_is_proxied_to_the_backend(nginx_conf: str) -> None:
    block = _location_block(nginx_conf, "/api/")
    assert "proxy_pass http://safir_backend" in block
    # The prefix is passed through unchanged: FastAPI owns the `/api/v1` paths.
    assert not block.rstrip().endswith("/")


def test_everything_else_is_proxied_to_the_frontend(nginx_conf: str) -> None:
    block = _location_block(nginx_conf, "/")
    assert "proxy_pass http://safir_frontend" in block


def test_the_probes_are_answered_by_the_backend(nginx_conf: str) -> None:
    for probe in ("/health", "/ready"):
        block = _location_block(nginx_conf, f"= {probe}")
        assert f"proxy_pass http://safir_backend{probe}" in block


def test_forwarded_headers_are_set_on_both_proxies(nginx_conf: str) -> None:
    for pattern in ("/api/", "/"):
        block = _location_block(nginx_conf, pattern)
        for header in ("X-Real-IP", "X-Forwarded-For", "X-Forwarded-Proto"):
            assert f"proxy_set_header {header}" in block, f"{header} missing on {pattern}"


def test_the_security_headers_are_sent_always(nginx_conf: str) -> None:
    for header in (
        "X-Content-Type-Options nosniff",
        "X-Frame-Options DENY",
        "Referrer-Policy same-origin",
    ):
        assert f"add_header {header} always" in nginx_conf


def test_the_upload_ceiling_is_bounded(nginx_conf: str) -> None:
    match = re.search(r"client_max_body_size\s+(\d+)([mMgG]);", nginx_conf)
    assert match, "client_max_body_size must be set explicitly"
    size, unit = int(match.group(1)), match.group(2).lower()
    assert size <= 64, "the upload ceiling must stay bounded"
    assert unit == "m"


def test_the_upstreams_name_the_compose_services(nginx_conf: str, compose: str) -> None:
    for upstream, service in (("safir_frontend", "frontend"), ("safir_backend", "backend")):
        assert re.search(rf"upstream {upstream}\s*\{{[^}}]*{service}:", nginx_conf, re.S)
        assert re.search(rf"^  {service}:", compose, re.M), f"{service} service missing"


def test_compose_mounts_the_same_config_it_tests(compose: str) -> None:
    assert "./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro" in compose


def test_the_frontend_and_backend_are_not_published_directly(compose: str) -> None:
    """Only Nginx may be reachable from outside; the others use `expose`."""
    for service in ("frontend", "backend"):
        block = re.search(rf"^  {service}:\n(.*?)(?=^  \w|\Z)", compose, re.S | re.M)
        assert block, f"{service} service missing"
        assert "ports:" not in block.group(1), f"{service} must not publish a host port"
        assert "expose:" in block.group(1)