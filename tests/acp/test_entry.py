"""Tests for acp_adapter.entry startup wiring."""

import acp

from hermes_agent.acp import entry


def test_main_enables_unstable_protocol(monkeypatch):
    calls = {}

    async def fake_run_agent(agent, **kwargs):
        calls["kwargs"] = kwargs

    monkeypatch.setattr(entry, "_setup_logging", lambda: None)
    monkeypatch.setattr(entry, "_load_env", lambda: None)
    monkeypatch.setattr(acp, "hermes_agent.agent.loop", fake_run_agent)

    entry.main()

    assert calls["kwargs"]["use_unstable_protocol"] is True
