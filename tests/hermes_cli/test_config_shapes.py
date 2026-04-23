"""Runtime smoke tests for `_CamofoxConfig` / `_BrowserConfig` TypedDict shapes."""

from __future__ import annotations


def test_camofox_config_is_partial_typeddict():
    from hermes_agent.cli.config import _CamofoxConfig

    cfg_empty: _CamofoxConfig = {}
    cfg_with_field: _CamofoxConfig = {"managed_persistence": True}

    assert cfg_empty == {}
    assert cfg_with_field.get("managed_persistence") is True


def test_camofox_config_nested_in_browser_config():
    from hermes_agent.cli.config import _BrowserConfig

    browser: _BrowserConfig = {
        "inactivity_timeout": 60,
        "command_timeout": 10,
        "record_sessions": False,
        "allow_private_urls": False,
        "cdp_url": "http://localhost:9222",
        "camofox": {"managed_persistence": False},
    }

    assert browser["camofox"].get("managed_persistence") is False
