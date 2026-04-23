"""Regression tests for memory provider selection during AIAgent init."""

from types import SimpleNamespace
from unittest.mock import patch


def test_blank_memory_provider_does_not_auto_enable_honcho():
    """Blank memory.provider should remain opt-out even if Honcho fallback looks configured."""
    cfg = {"memory": {"provider": ""}, "agent": {}}
    honcho_cfg = SimpleNamespace(enabled=True, api_key="stale-key", base_url=None)

    with (
        patch("hermes_agent.cli.config.load_config", return_value=cfg),
        patch("hermes_agent.cli.config.save_config") as save_config,
        patch(
            "hermes_agent.plugins.memory.honcho.client.HonchoClientConfig.from_global_config",
            return_value=honcho_cfg,
        ) as from_global_config,
        patch("hermes_agent.plugins.memory.load_memory_provider") as load_memory_provider,
        patch("hermes_agent.providers.metadata.get_model_context_length", return_value=204_800),
        patch("hermes_agent.agent.loop.get_tool_definitions", return_value=[]),
        patch("hermes_agent.agent.loop.check_toolset_requirements", return_value={}),
        patch("hermes_agent.agent.loop.OpenAI"),
    ):
        from hermes_agent.agent.loop import AIAgent

        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=False,
        )

    assert agent._memory_manager is None
    from_global_config.assert_not_called()
    load_memory_provider.assert_not_called()
    save_config.assert_not_called()

