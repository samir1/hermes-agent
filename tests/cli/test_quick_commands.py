"""Tests for user-defined quick commands that bypass the agent loop."""
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from rich.text import Text
import pytest


# ── CLI tests ──────────────────────────────────────────────────────────────

class TestCLIQuickCommands:
    """Test quick command dispatch in HermesCLI.process_command."""

    @staticmethod
    def _printed_plain(call_arg):
        if isinstance(call_arg, Text):
            return call_arg.plain
        return str(call_arg)

    def _make_cli(self, quick_commands):
        from cli import HermesCLI
        cli = HermesCLI.__new__(HermesCLI)
        cli.config = {"quick_commands": quick_commands}
        cli.console = MagicMock()
        cli.agent = None
        cli.conversation_history = []
        # session_id is accessed by the fallback skill/fuzzy-match path in
        # process_command; without it, tests that exercise `/alias args`
        # can trip an AttributeError when cross-test state leaks a skill
        # command matching the alias target.
        cli.session_id = "test-session"
        return cli

    def test_exec_command_runs_and_prints_output(self):
        cli = self._make_cli({"dn": {"type": "exec", "command": "echo daily-note"}})
        result = cli.process_command("/dn")
        assert result is True
        cli.console.print.assert_called_once()
        printed = self._printed_plain(cli.console.print.call_args[0][0])
        assert printed == "daily-note"

    def test_exec_command_uses_chat_console_when_tui_is_live(self):
        cli = self._make_cli({"dn": {"type": "exec", "command": "echo daily-note"}})
        cli._app = object()
        live_console = MagicMock()

        with patch("cli.ChatConsole", return_value=live_console):
            result = cli.process_command("/dn")

        assert result is True
        live_console.print.assert_called_once()
        printed = self._printed_plain(live_console.print.call_args[0][0])
        assert printed == "daily-note"
        cli.console.print.assert_not_called()

    def test_exec_command_stderr_shown_on_no_stdout(self):
        cli = self._make_cli({"err": {"type": "exec", "command": "echo error >&2"}})
        result = cli.process_command("/err")
        assert result is True
        # stderr fallback — should print something
        cli.console.print.assert_called_once()

    def test_exec_command_no_output_shows_fallback(self):
        cli = self._make_cli({"empty": {"type": "exec", "command": "true"}})
        cli.process_command("/empty")
        cli.console.print.assert_called_once()
        args = cli.console.print.call_args[0][0]
        assert "no output" in args.lower()

    def test_alias_command_routes_to_target(self):
        """Alias quick commands rewrite to the target command."""
        cli = self._make_cli({"shortcut": {"type": "alias", "target": "/help"}})
        with patch.object(cli, "process_command", wraps=cli.process_command) as spy:
            cli.process_command("/shortcut")
            # Should recursively call process_command with /help
            spy.assert_any_call("/help")

    def test_alias_command_passes_args(self):
        """Alias quick commands forward user arguments to the target."""
        cli = self._make_cli({"sc": {"type": "alias", "target": "/context"}})
        with patch.object(cli, "process_command", wraps=cli.process_command) as spy:
            cli.process_command("/sc some args")
            spy.assert_any_call("/context some args")

    def test_alias_no_target_shows_error(self):
        cli = self._make_cli({"broken": {"type": "alias", "target": ""}})
        cli.process_command("/broken")
        cli.console.print.assert_called_once()
        args = cli.console.print.call_args[0][0]
        assert "no target defined" in args.lower()

    def test_unsupported_type_shows_error(self):
        cli = self._make_cli({"bad": {"type": "prompt", "command": "echo hi"}})
        cli.process_command("/bad")
        cli.console.print.assert_called_once()
        args = cli.console.print.call_args[0][0]
        assert "unsupported type" in args.lower()

    def test_missing_command_field_shows_error(self):
        cli = self._make_cli({"oops": {"type": "exec"}})
        cli.process_command("/oops")
        cli.console.print.assert_called_once()
        args = cli.console.print.call_args[0][0]
        assert "no command defined" in args.lower()

    def test_quick_command_takes_priority_over_skill_commands(self):
        """Quick commands must be checked before skill slash commands."""
        cli = self._make_cli({"mygif": {"type": "exec", "command": "echo overridden"}})
        with patch("cli._skill_commands", {"/mygif": {"name": "gif-search"}}):
            cli.process_command("/mygif")
        cli.console.print.assert_called_once()
        printed = self._printed_plain(cli.console.print.call_args[0][0])
        assert printed == "overridden"

    def test_unknown_command_still_shows_error(self):
        cli = self._make_cli({})
        with patch("cli._cprint") as mock_cprint:
            cli.process_command("/nonexistent")
            mock_cprint.assert_called()
            printed = " ".join(str(c) for c in mock_cprint.call_args_list)
            assert "unknown command" in printed.lower()

    def test_timeout_shows_error(self):
        cli = self._make_cli({"slow": {"type": "exec", "command": "sleep 100"}})
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 30)):
            cli.process_command("/slow")
        cli.console.print.assert_called_once()
        args = cli.console.print.call_args[0][0]
        assert "timed out" in args.lower()


# ── Gateway tests ──────────────────────────────────────────────────────────

class TestGatewayQuickCommands:
    """Test quick command dispatch in GatewayRunner._handle_message."""

    def _make_event(self, command, args=""):
        event = MagicMock()
        event.get_command.return_value = command
        event.get_command_args.return_value = args
        event.text = f"/{command} {args}".strip()
        event.source = MagicMock()
        event.source.user_id = "test_user"
        event.source.user_name = "Test User"
        event.source.platform.value = "telegram"
        event.source.chat_type = "dm"
        event.source.chat_id = "123"
        return event

    @pytest.mark.asyncio
    async def test_exec_command_returns_output(self):
        from gateway.run import GatewayRunner
        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {"quick_commands": {"limits": {"type": "exec", "command": "echo ok"}}}
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("limits")
        result = await runner._handle_message(event)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_unsupported_type_returns_error(self):
        from gateway.run import GatewayRunner
        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {"quick_commands": {"bad": {"type": "prompt", "command": "echo hi"}}}
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("bad")
        result = await runner._handle_message(event)
        assert result is not None
        assert "unsupported type" in result.lower()

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        from gateway.run import GatewayRunner
        import asyncio
        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {"quick_commands": {"slow": {"type": "exec", "command": "sleep 100"}}}
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("slow")
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await runner._handle_message(event)
        assert result is not None
        assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_gateway_config_object_supports_quick_commands(self):
        from gateway.config import GatewayConfig
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig(
            quick_commands={"limits": {"type": "exec", "command": "echo ok"}}
        )
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("limits")
        result = await runner._handle_message(event)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_plain_text_inbox_cleanup_bypasses_main_agent_session(self):
        """Exact plain-text `inbox cleanup` must route before session history or compression."""
        from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
        from gateway.platforms.base import MessageEvent, MessageType
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        runner.config.platforms[Platform.TELEGRAM] = PlatformConfig()
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM,
            chat_id="123",
            name="Home",
        )
        runner._running_agents = {}
        runner._running_agents_ts = {}
        runner._pending_messages = {}
        runner._update_prompt_pending = {}
        runner._draining = False
        runner._busy_input_mode = "queue"
        runner._background_tasks = set()
        runner._is_user_authorized = MagicMock(return_value=True)
        runner._handle_inbox_cleanup_fast_path = AsyncMock(return_value="inbox cleanup started")
        runner._handle_message_with_agent = AsyncMock(return_value="main agent should not run")

        event = MessageEvent(
            text="inbox cleanup",
            message_type=MessageType.TEXT,
            source=SessionSource(
                platform=Platform.TELEGRAM,
                chat_id="123",
                chat_type="dm",
                user_id="u1",
                user_name="Samir",
            ),
        )

        result = await runner._handle_message(event)

        assert result == "inbox cleanup started"
        runner._handle_inbox_cleanup_fast_path.assert_awaited_once()
        runner._handle_message_with_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_plain_text_inbox_cleanup_accepts_normalized_spacing_and_case(self):
        from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
        from gateway.platforms.base import MessageEvent, MessageType
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        runner.config.platforms[Platform.TELEGRAM] = PlatformConfig()
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM,
            chat_id="123",
            name="Home",
        )
        runner._running_agents = {}
        runner._running_agents_ts = {}
        runner._pending_messages = {}
        runner._update_prompt_pending = {}
        runner._draining = False
        runner._busy_input_mode = "queue"
        runner._background_tasks = set()
        runner._is_user_authorized = MagicMock(return_value=True)
        runner._handle_inbox_cleanup_fast_path = AsyncMock(return_value="inbox cleanup started")
        runner._handle_message_with_agent = AsyncMock(return_value="main agent should not run")

        event = MessageEvent(
            text="  Inbox   Cleanup  ",
            message_type=MessageType.TEXT,
            source=SessionSource(
                platform=Platform.TELEGRAM,
                chat_id="123",
                chat_type="dm",
                user_id="u1",
                user_name="Samir",
            ),
        )

        result = await runner._handle_message(event)

        assert result == "inbox cleanup started"
        runner._handle_inbox_cleanup_fast_path.assert_awaited_once()
        runner._handle_message_with_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_plain_text_inbox_cleanup_bypasses_even_when_session_running(self):
        from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
        from gateway.platforms.base import MessageEvent, MessageType
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        runner.config.platforms[Platform.TELEGRAM] = PlatformConfig()
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM,
            chat_id="123",
            name="Home",
        )
        runner._running_agents = {}
        runner._running_agents_ts = {}
        runner._pending_messages = {}
        runner._update_prompt_pending = {}
        runner._draining = False
        runner._busy_input_mode = "queue"
        runner._background_tasks = set()
        runner._is_user_authorized = MagicMock(return_value=True)
        runner._handle_inbox_cleanup_fast_path = AsyncMock(return_value="inbox cleanup started")
        runner._handle_message_with_agent = AsyncMock(return_value="main agent should not run")

        source = SessionSource(
            platform=Platform.TELEGRAM,
            chat_id="123",
            chat_type="dm",
            user_id="u1",
            user_name="Samir",
        )
        runner._running_agents[runner._session_key_for_source(source)] = object()

        event = MessageEvent(
            text="inbox cleanup",
            message_type=MessageType.TEXT,
            source=source,
        )

        result = await runner._handle_message(event)

        assert result == "inbox cleanup started"
        runner._handle_inbox_cleanup_fast_path.assert_awaited_once()
        runner._handle_message_with_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_inbox_cleanup_fast_path_returns_started_scanning_message(self):
        """The fast path should acknowledge that the skill actually started."""
        from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
        from gateway.platforms.base import MessageEvent, MessageType
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        runner.config.platforms[Platform.TELEGRAM] = PlatformConfig()
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM,
            chat_id="123",
            name="Home",
        )
        runner._background_tasks = set()
        runner._run_inbox_cleanup_fast_path_direct = AsyncMock(return_value=None)

        event = MessageEvent(
            text="inbox cleanup",
            message_type=MessageType.TEXT,
            source=SessionSource(
                platform=Platform.TELEGRAM,
                chat_id="123",
                chat_type="dm",
                user_id="u1",
                user_name="Samir",
            ),
        )

        result = await runner._handle_inbox_cleanup_fast_path(event)

        assert "I’m scanning all 4 inboxes now" in result
        assert "read-only" in result
        assert "direct fast path" in result
        runner._run_inbox_cleanup_fast_path_direct.assert_called_once()

    @pytest.mark.asyncio
    async def test_plain_text_inbox_cleanup_restricted_to_telegram_home_dm(self):
        from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
        from gateway.platforms.base import MessageEvent, MessageType
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        runner.config.platforms[Platform.TELEGRAM] = PlatformConfig()
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM,
            chat_id="123",
            name="Home",
        )
        runner._running_agents = {}
        runner._running_agents_ts = {}
        runner._pending_messages = {}
        runner._update_prompt_pending = {}
        runner._draining = False
        runner._busy_input_mode = "queue"
        runner._background_tasks = set()
        runner._is_user_authorized = MagicMock(return_value=True)
        runner._handle_inbox_cleanup_fast_path = AsyncMock(return_value="inbox cleanup started")
        runner._handle_message_with_agent = AsyncMock(return_value="main agent should not run")

        event = MessageEvent(
            text="inbox cleanup",
            message_type=MessageType.TEXT,
            source=SessionSource(
                platform=Platform.TELEGRAM,
                chat_id="999",
                chat_type="dm",
                user_id="u2",
                user_name="Other",
            ),
        )

        result = await runner._handle_message(event)

        assert result == "Inbox cleanup can only be run from the Telegram home DM."
        runner._handle_inbox_cleanup_fast_path.assert_not_awaited()
        runner._handle_message_with_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_direct_inbox_cleanup_task_sends_runner_messages_without_agent(self):
        from gateway.config import GatewayConfig
        from gateway.platforms.base import Platform
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        adapter = AsyncMock()
        runner.adapters = {Platform.TELEGRAM: adapter}
        runner._run_in_executor_with_context = AsyncMock(return_value={"messages": ["report 1", "report 2"]})
        runner._load_lightweight_inbox_cleanup_runner = MagicMock()
        runner._background_tasks = set()

        source = SessionSource(
            platform=Platform.TELEGRAM,
            chat_id="123",
            chat_type="dm",
            user_id="u1",
            user_name="Samir",
        )

        await runner._run_inbox_cleanup_fast_path_direct(source, "task-1")

        assert adapter.send.await_count == 2
        sent = [call.kwargs["content"] for call in adapter.send.await_args_list]
        assert sent[0].startswith("report 1")
        assert sent[1].startswith("report 2")
        runner._run_in_executor_with_context.assert_awaited_once()
        runner._load_lightweight_inbox_cleanup_runner.assert_not_called()

    @pytest.mark.asyncio
    async def test_direct_inbox_cleanup_task_redacts_runner_message_details(self):
        from gateway.config import GatewayConfig
        from gateway.platforms.base import Platform
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        adapter = AsyncMock()
        runner.adapters = {Platform.TELEGRAM: adapter}
        runner._run_in_executor_with_context = AsyncMock(
            return_value={
                "messages": [
                    "⛔ Blockers\n- all: failed at /Users/samir/My Documents/private.py\n- env GOG_KEYRING_PASSWORD=\"super secret\"; Bearer abcdefghijklmnop"
                ]
            }
        )
        runner._background_tasks = set()

        source = SessionSource(
            platform=Platform.TELEGRAM,
            chat_id="123",
            chat_type="dm",
            user_id="u1",
            user_name="Samir",
        )

        await runner._run_inbox_cleanup_fast_path_direct(source, "task-1")

        adapter.send.assert_awaited_once()
        content = adapter.send.await_args.kwargs["content"]
        assert "[redacted path]" in content
        assert "GOG_KEYRING_PASSWORD=[redacted]" in content
        assert "Bearer [redacted]" in content
        assert "/Users/samir" not in content
        assert "My Documents" not in content
        assert "super secret" not in content
        assert "abcdefghijklmnop" not in content

    @pytest.mark.asyncio
    async def test_direct_inbox_cleanup_task_hides_internal_error_details(self):
        from gateway.config import GatewayConfig
        from gateway.platforms.base import Platform
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig()
        adapter = AsyncMock()
        runner.adapters = {Platform.TELEGRAM: adapter}
        runner._run_in_executor_with_context = AsyncMock(
            side_effect=RuntimeError("/Users/samir/.hermes/skills/private/path leaked")
        )
        runner._background_tasks = set()

        source = SessionSource(
            platform=Platform.TELEGRAM,
            chat_id="123",
            chat_type="dm",
            user_id="u1",
            user_name="Samir",
        )

        await runner._run_inbox_cleanup_fast_path_direct(source, "task-1")

        adapter.send.assert_awaited_once()
        content = adapter.send.await_args.kwargs["content"]
        assert "failed before any email actions were taken" in content
        assert "/Users/samir" not in content
        assert "private/path" not in content
