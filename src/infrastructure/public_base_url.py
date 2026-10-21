"""Resolve the public base URL of this deployment at run or install time.

Nothing in the repository may name a host: the service has to move to other
hardware. Order of resolution:

1. ``BLENDER_MCP_PUBLIC_BASE_URL`` (explicit operator choice, e.g. a non-Tailscale proxy).
2. ``tailscale status --self --json`` -> ``.Self.DNSName`` -> ``https://<fqdn>/blender``.
3. ``ValueError`` whose message names the env var.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from urllib.parse import urlparse

ENV_VAR = "BLENDER_MCP_PUBLIC_BASE_URL"
MOUNT_PATH = "/blender"
_TAILSCALE_TIMEOUT_S = 10.0  # `tailscale status` answers from the local daemon; 10 s is generous


def _tailscale_status() -> str:
    """Run the real CLI; any failure becomes OSError for the caller to translate."""
    try:
        done = subprocess.run(
            ["tailscale", "status", "--self", "--json"],
            capture_output=True,
            text=True,
            timeout=_TAILSCALE_TIMEOUT_S,
            check=True,
        )
    except subprocess.SubprocessError as exc:
        raise OSError(f"tailscale status failed: {exc}") from exc
    return done.stdout


def _hint(reason: str) -> ValueError:
    return ValueError(
        f"cannot determine the public base URL ({reason}); "
        f"set {ENV_VAR}=https://<host>{MOUNT_PATH} or make `tailscale status --self --json` work"
    )


def public_base_url(
    env: Mapping[str, str] | None = None,
    *,
    tailscale_status: Callable[[], str] | None = None,
) -> str:
    """Return the public base URL (with the ``/blender`` prefix, no trailing slash)."""
    environment = os.environ if env is None else env
    configured = environment.get(ENV_VAR, "").strip().rstrip("/")
    if configured:
        return configured
    runner = tailscale_status or _tailscale_status
    try:
        payload = json.loads(runner())
    except (OSError, ValueError) as exc:
        raise _hint(f"tailscale unavailable: {exc}") from exc
    node = payload.get("Self") if isinstance(payload, dict) else None  # narrow-ok: json top level
    dns_name = node.get("DNSName") if isinstance(node, dict) else None  # narrow-ok: json object
    fqdn = dns_name.strip().rstrip(".") if isinstance(dns_name, str) else ""
    if not fqdn:
        raise _hint("tailscale reported no Self.DNSName")
    return f"https://{fqdn}{MOUNT_PATH}"


def public_origin(
    env: Mapping[str, str] | None = None,
    *,
    tailscale_status: Callable[[], str] | None = None,
) -> str:
    """Return only ``scheme://host[:port]`` of the public base URL (what CORS needs)."""
    parsed = urlparse(public_base_url(env, tailscale_status=tailscale_status))
    return f"{parsed.scheme}://{parsed.netloc}"


def public_host(
    env: Mapping[str, str] | None = None,
    *,
    tailscale_status: Callable[[], str] | None = None,
) -> str:
    """Return the bare hostname of the public base URL."""
    host = urlparse(public_base_url(env, tailscale_status=tailscale_status)).hostname
    if not host:
        raise _hint("the configured URL has no host")
    return host
