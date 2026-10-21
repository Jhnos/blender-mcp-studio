"""public_base_url: env first, then tailscale self DNSName, else a hinted ValueError."""

from __future__ import annotations

import json

import pytest

from src.infrastructure.public_base_url import ENV_VAR, public_base_url, public_origin


def _status(dns_name: str) -> str:
    return json.dumps({"Self": {"DNSName": dns_name}})


def _boom() -> str:
    raise FileNotFoundError("tailscale")


def test_env_wins_over_tailscale() -> None:
    def fail() -> str:
        raise AssertionError("tailscale must not be consulted when the env is set")

    env = {ENV_VAR: "https://studio.example.net/blender/"}
    assert public_base_url(env, tailscale_status=fail) == "https://studio.example.net/blender"


def test_tailscale_dns_name_is_parsed_and_trailing_dot_stripped() -> None:
    url = public_base_url({}, tailscale_status=lambda: _status("host-a.tailnet-x.ts.net."))
    assert url == "https://host-a.tailnet-x.ts.net/blender"


def test_origin_has_no_path() -> None:
    env = {ENV_VAR: "https://studio.example.net/blender"}
    assert public_origin(env) == "https://studio.example.net"


def test_tailscale_missing_raises_with_env_hint() -> None:
    with pytest.raises(ValueError, match=ENV_VAR):
        public_base_url({}, tailscale_status=_boom)


def test_tailscale_garbage_or_empty_dns_raises() -> None:
    with pytest.raises(ValueError, match=ENV_VAR):
        public_base_url({}, tailscale_status=lambda: "not json")
    with pytest.raises(ValueError, match=ENV_VAR):
        public_base_url({}, tailscale_status=lambda: _status(""))
    with pytest.raises(ValueError, match=ENV_VAR):
        public_base_url({}, tailscale_status=lambda: "{}")
