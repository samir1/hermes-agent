#!/usr/bin/env python3
"""Rewrite all imports and string-based module references for the hermes_agent restructure.

This script handles Steps 1-3 of the import rewrite:
  1. Build the IMPORT_MAP (old module path -> new module path)
  2. Rewrite all import statements (import X, from X import Y)
  3. Rewrite string-based module references (patch(), sys.modules[], importlib.import_module())

Usage:
    python scripts/restructure_import_rewriter.py [--dry-run]
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Step 1: The import rewrite map
# ---------------------------------------------------------------------------

IMPORT_MAP: dict[str, str] = {
    # Top-level modules
    "hermes_agent.agent.loop": "hermes_agent.agent.loop",
    "cli": "cli",
    "hermes_agent.tools.dispatch": "hermes_agent.tools.dispatch",
    "hermes_agent.tools.toolsets": "hermes_agent.tools.toolsets",
    "hermes_agent.tools.distributions": "hermes_agent.tools.distributions",
    "hermes_agent.tools.mcp.serve": "hermes_agent.tools.mcp.serve",
    "utils": "utils",
    "hermes_constants": "hermes_constants",
    "hermes_state": "hermes_state",
    "hermes_logging": "hermes_logging",
    "hermes_time": "hermes_time",

    # agent/ -> hermes_agent/agent/
    "hermes_agent.agent.prompt_builder": "hermes_agent.agent.prompt_builder",
    "hermes_agent.agent.context.engine": "hermes_agent.agent.context.engine",
    "hermes_agent.agent.context.compressor": "hermes_agent.agent.context.compressor",
    "hermes_agent.agent.context.references": "hermes_agent.agent.context.references",
    "hermes_agent.agent.memory.manager": "hermes_agent.agent.memory.manager",
    "hermes_agent.agent.memory.provider": "hermes_agent.agent.memory.provider",
    "hermes_agent.agent.image_gen.provider": "hermes_agent.agent.image_gen.provider",
    "hermes_agent.agent.image_gen.registry": "hermes_agent.agent.image_gen.registry",
    "hermes_agent.agent.display": "hermes_agent.agent.display",
    "hermes_agent.agent.redact": "hermes_agent.agent.redact",
    "hermes_agent.agent.trajectory": "hermes_agent.agent.trajectory",
    "hermes_agent.agent.insights": "hermes_agent.agent.insights",
    "hermes_agent.agent.title_generator": "hermes_agent.agent.title_generator",
    "hermes_agent.agent.skill_commands": "hermes_agent.agent.skill_commands",
    "hermes_agent.agent.skill_utils": "hermes_agent.agent.skill_utils",
    "hermes_agent.agent.shell_hooks": "hermes_agent.agent.shell_hooks",
    "hermes_agent.agent.file_safety": "hermes_agent.agent.file_safety",
    "hermes_agent.agent.subdirectory_hints": "hermes_agent.agent.subdirectory_hints",
    "hermes_agent.agent.manual_compression_feedback": "hermes_agent.agent.manual_compression_feedback",
    "hermes_agent.agent.copilot_acp_client": "hermes_agent.agent.copilot_acp_client",

    # agent/ -> hermes_agent/providers/
    "hermes_agent.providers.base": "hermes_agent.providers.base",
    "hermes_agent.providers.types": "hermes_agent.providers.types",
    "hermes_agent.providers.anthropic_transport": "hermes_agent.providers.anthropic_transport",
    "hermes_agent.providers.bedrock_transport": "hermes_agent.providers.bedrock_transport",
    "hermes_agent.providers.openai_transport": "hermes_agent.providers.openai_transport",
    "hermes_agent.providers.codex_transport": "hermes_agent.providers.codex_transport",
    "hermes_agent.providers": "hermes_agent.providers",
    "hermes_agent.providers.anthropic_adapter": "hermes_agent.providers.anthropic_adapter",
    "hermes_agent.providers.bedrock_adapter": "hermes_agent.providers.bedrock_adapter",
    "hermes_agent.providers.codex_adapter": "hermes_agent.providers.codex_adapter",
    "hermes_agent.providers.gemini_adapter": "hermes_agent.providers.gemini_adapter",
    "hermes_agent.providers.gemini_cloudcode_adapter": "hermes_agent.providers.gemini_cloudcode_adapter",
    "hermes_agent.providers.gemini_schema": "hermes_agent.providers.gemini_schema",
    "hermes_agent.providers.google_oauth": "hermes_agent.providers.google_oauth",
    "hermes_agent.providers.auxiliary": "hermes_agent.providers.auxiliary",
    "hermes_agent.providers.metadata": "hermes_agent.providers.metadata",
    "hermes_agent.providers.metadata_dev": "hermes_agent.providers.metadata_dev",
    "hermes_agent.providers.pricing": "hermes_agent.providers.pricing",
    "hermes_agent.providers.account_usage": "hermes_agent.providers.account_usage",
    "hermes_agent.providers.caching": "hermes_agent.providers.caching",
    "hermes_agent.providers.credential_pool": "hermes_agent.providers.credential_pool",
    "hermes_agent.providers.credential_sources": "hermes_agent.providers.credential_sources",
    "hermes_agent.providers.rate_limiting": "hermes_agent.providers.rate_limiting",
    "hermes_agent.providers.nous_rate_guard": "hermes_agent.providers.nous_rate_guard",
    "hermes_agent.providers.retry": "hermes_agent.providers.retry",
    "hermes_agent.providers.errors": "hermes_agent.providers.errors",

    # Catch-all for agent (must be AFTER all agent.X entries)
    "agent": "agent",

    # tools/ -> hermes_agent/tools/
    "hermes_agent.tools.registry": "hermes_agent.tools.registry",
    "hermes_agent.tools.terminal": "hermes_agent.tools.terminal",
    "hermes_agent.tools.web": "hermes_agent.tools.web",
    "hermes_agent.tools.vision": "hermes_agent.tools.vision",
    "hermes_agent.tools.code_execution": "hermes_agent.tools.code_execution",
    "hermes_agent.tools.delegate": "hermes_agent.tools.delegate",
    "hermes_agent.tools.memory": "hermes_agent.tools.memory",
    "hermes_agent.tools.todo": "hermes_agent.tools.todo",
    "hermes_agent.tools.clarify": "hermes_agent.tools.clarify",
    "hermes_agent.tools.cronjob": "hermes_agent.tools.cronjob",
    "hermes_agent.tools.send_message": "hermes_agent.tools.send_message",
    "hermes_agent.tools.discord": "hermes_agent.tools.discord",
    "hermes_agent.tools.homeassistant": "hermes_agent.tools.homeassistant",
    "hermes_agent.tools.rl_training": "hermes_agent.tools.rl_training",
    "hermes_agent.tools.mixture_of_agents": "hermes_agent.tools.mixture_of_agents",
    "hermes_agent.tools.session_search": "hermes_agent.tools.session_search",
    "hermes_agent.tools.managed_gateway": "hermes_agent.tools.managed_gateway",
    "hermes_agent.tools.checkpoint": "hermes_agent.tools.checkpoint",
    "hermes_agent.tools.openrouter": "hermes_agent.tools.openrouter",
    "hermes_agent.tools.feishu_doc": "hermes_agent.tools.feishu_doc",
    "hermes_agent.tools.feishu_drive": "hermes_agent.tools.feishu_drive",
    "hermes_agent.tools.budget_config": "hermes_agent.tools.budget_config",
    "hermes_agent.tools.process_registry": "hermes_agent.tools.process_registry",
    "hermes_agent.tools.result_storage": "hermes_agent.tools.result_storage",
    "hermes_agent.tools.backend_helpers": "hermes_agent.tools.backend_helpers",
    "hermes_agent.tools.debug_helpers": "hermes_agent.tools.debug_helpers",
    "hermes_agent.tools.env_passthrough": "hermes_agent.tools.env_passthrough",
    "hermes_agent.tools.osv_check": "hermes_agent.tools.osv_check",
    "hermes_agent.tools.patch_parser": "hermes_agent.tools.patch_parser",
    "hermes_agent.tools.xai_http": "hermes_agent.tools.xai_http",
    "hermes_agent.tools.credential_files": "hermes_agent.tools.credential_files",
    "hermes_agent.tools.binary_extensions": "hermes_agent.tools.binary_extensions",
    "hermes_agent.tools.ansi_strip": "hermes_agent.tools.ansi_strip",
    "hermes_agent.tools.fuzzy_match": "hermes_agent.tools.fuzzy_match",
    "hermes_agent.tools.interrupt": "hermes_agent.tools.interrupt",
    "hermes_agent.tools.website_policy": "hermes_agent.tools.website_policy",

    # tools/ subgroups - browser
    "hermes_agent.tools.browser.tool": "hermes_agent.tools.browser.tool",
    "hermes_agent.tools.browser.cdp": "hermes_agent.tools.browser.cdp",
    "hermes_agent.tools.browser.camofox": "hermes_agent.tools.browser.camofox",
    "hermes_agent.tools.browser.providers": "hermes_agent.tools.browser.providers",
    "hermes_agent.tools.browser.providers.base": "hermes_agent.tools.browser.providers.base",
    "hermes_agent.tools.browser.providers.browser_use": "hermes_agent.tools.browser.providers.browser_use",
    "hermes_agent.tools.browser.providers.browserbase": "hermes_agent.tools.browser.providers.browserbase",
    "hermes_agent.tools.browser.providers.firecrawl": "hermes_agent.tools.browser.providers.firecrawl",
    "hermes_agent.tools.browser.camofox_state": "hermes_agent.tools.browser.camofox_state",

    # tools/ subgroups - mcp
    "hermes_agent.tools.mcp.tool": "hermes_agent.tools.mcp.tool",
    "hermes_agent.tools.mcp.oauth": "hermes_agent.tools.mcp.oauth",
    "hermes_agent.tools.mcp.oauth_manager": "hermes_agent.tools.mcp.oauth_manager",

    # tools/ subgroups - skills
    "hermes_agent.tools.skills.manager": "hermes_agent.tools.skills.manager",
    "hermes_agent.tools.skills.tool": "hermes_agent.tools.skills.tool",
    "hermes_agent.tools.skills.hub": "hermes_agent.tools.skills.hub",
    "hermes_agent.tools.skills.guard": "hermes_agent.tools.skills.guard",
    "hermes_agent.tools.skills.sync": "hermes_agent.tools.skills.sync",

    # tools/ subgroups - media
    "hermes_agent.tools.media.voice": "hermes_agent.tools.media.voice",
    "hermes_agent.tools.media.tts": "hermes_agent.tools.media.tts",
    "hermes_agent.tools.media.transcription": "hermes_agent.tools.media.transcription",
    "hermes_agent.tools.media.neutts": "hermes_agent.tools.media.neutts",
    "hermes_agent.tools.media.image_gen": "hermes_agent.tools.media.image_gen",

    # tools/ subgroups - security
    "hermes_agent.tools.security.paths": "hermes_agent.tools.security.paths",
    "hermes_agent.tools.security.urls": "hermes_agent.tools.security.urls",
    "hermes_agent.tools.security.tirith": "hermes_agent.tools.security.tirith",
    "hermes_agent.tools.security.approval": "hermes_agent.tools.security.approval",

    # tools/ subgroups - files
    "hermes_agent.tools.files.tools": "hermes_agent.tools.files.tools",
    "hermes_agent.tools.files.operations": "hermes_agent.tools.files.operations",
    "hermes_agent.tools.files.state": "hermes_agent.tools.files.state",

    # tools/environments/ -> hermes_agent/backends/
    "hermes_agent.backends": "hermes_agent.backends",
    "hermes_agent.backends.base": "hermes_agent.backends.base",
    "hermes_agent.backends.local": "hermes_agent.backends.local",
    "hermes_agent.backends.docker": "hermes_agent.backends.docker",
    "hermes_agent.backends.ssh": "hermes_agent.backends.ssh",
    "hermes_agent.backends.modal": "hermes_agent.backends.modal",
    "hermes_agent.backends.managed_modal": "hermes_agent.backends.managed_modal",
    "hermes_agent.backends.modal_utils": "hermes_agent.backends.modal_utils",
    "hermes_agent.backends.daytona": "hermes_agent.backends.daytona",
    "hermes_agent.backends.singularity": "hermes_agent.backends.singularity",
    "hermes_agent.backends.file_sync": "hermes_agent.backends.file_sync",

    # Catch-all for tools (must be AFTER all tools.X entries)
    "tools": "tools",

    # hermes_cli/ -> hermes_agent/cli/
    "hermes_agent.cli.main": "hermes_agent.cli.main",
    "hermes_agent.cli.commands": "hermes_agent.cli.commands",
    "hermes_agent.cli.config": "hermes_agent.cli.config",
    "hermes_agent.cli.auth.auth": "hermes_agent.cli.auth.auth",
    "hermes_agent.cli.auth.commands": "hermes_agent.cli.auth.commands",
    "hermes_agent.cli.auth.copilot": "hermes_agent.cli.auth.copilot",
    "hermes_agent.cli.auth.dingtalk": "hermes_agent.cli.auth.dingtalk",
    "hermes_agent.cli.providers": "hermes_agent.cli.providers",
    "hermes_agent.cli.runtime_provider": "hermes_agent.cli.runtime_provider",
    "hermes_agent.cli.models.models": "hermes_agent.cli.models.models",
    "hermes_agent.cli.models.normalize": "hermes_agent.cli.models.normalize",
    "hermes_agent.cli.models.switch": "hermes_agent.cli.models.switch",
    "hermes_agent.cli.models.codex": "hermes_agent.cli.models.codex",
    "hermes_agent.cli.plugins": "hermes_agent.cli.plugins",
    "hermes_agent.cli.plugins_cmd": "hermes_agent.cli.plugins_cmd",
    "hermes_agent.cli.skills_config": "hermes_agent.cli.skills_config",
    "hermes_agent.cli.skills_hub": "hermes_agent.cli.skills_hub",
    "hermes_agent.cli.tools_config": "hermes_agent.cli.tools_config",
    "hermes_agent.cli.profiles": "hermes_agent.cli.profiles",
    "hermes_agent.cli.cron": "hermes_agent.cli.cron",
    "hermes_agent.cli.gateway": "hermes_agent.cli.gateway",
    "hermes_agent.cli.mcp_config": "hermes_agent.cli.mcp_config",
    "hermes_agent.cli.memory_setup": "hermes_agent.cli.memory_setup",
    "hermes_agent.cli.env_loader": "hermes_agent.cli.env_loader",
    "hermes_agent.cli.nous_subscription": "hermes_agent.cli.nous_subscription",
    "hermes_agent.cli.ui.banner": "hermes_agent.cli.ui.banner",
    "hermes_agent.cli.ui.callbacks": "hermes_agent.cli.ui.callbacks",
    "hermes_agent.cli.ui.output": "hermes_agent.cli.ui.output",
    "hermes_agent.cli.ui.colors": "hermes_agent.cli.ui.colors",
    "hermes_agent.cli.ui.skin_engine": "hermes_agent.cli.ui.skin_engine",
    "hermes_agent.cli.ui.curses": "hermes_agent.cli.ui.curses",
    "hermes_agent.cli.ui.tips": "hermes_agent.cli.ui.tips",
    "hermes_agent.cli.ui.status": "hermes_agent.cli.ui.status",
    "hermes_agent.cli.ui.completion": "hermes_agent.cli.ui.completion",
    "hermes_agent.cli.backup": "hermes_agent.cli.backup",
    "hermes_agent.cli.clipboard": "hermes_agent.cli.clipboard",
    "hermes_agent.cli.debug": "hermes_agent.cli.debug",
    "hermes_agent.cli.doctor": "hermes_agent.cli.doctor",
    "hermes_agent.cli.dump": "hermes_agent.cli.dump",
    "hermes_agent.cli.hooks": "hermes_agent.cli.hooks",
    "hermes_agent.cli.logs": "hermes_agent.cli.logs",
    "hermes_agent.cli.pairing": "hermes_agent.cli.pairing",
    "hermes_agent.cli.platforms": "hermes_agent.cli.platforms",
    "hermes_agent.cli.setup_wizard": "hermes_agent.cli.setup_wizard",
    "hermes_agent.cli.timeouts": "hermes_agent.cli.timeouts",
    "hermes_agent.cli.uninstall": "hermes_agent.cli.uninstall",
    "hermes_agent.cli.web_server": "hermes_agent.cli.web_server",
    "hermes_agent.cli.webhook": "hermes_agent.cli.webhook",
    "hermes_agent.cli.default_soul": "hermes_agent.cli.default_soul",
    "hermes_agent.cli.claw": "hermes_agent.cli.claw",

    # Catch-all for hermes_cli (must be AFTER all hermes_cli.X entries)
    "hermes_agent.cli": "hermes_agent.cli",

    # gateway/ -> hermes_agent/gateway/
    "hermes_agent.gateway.builtin_hooks.boot_md": "hermes_agent.gateway.builtin_hooks.boot_md",
    "hermes_agent.gateway.builtin_hooks": "hermes_agent.gateway.builtin_hooks",
    "hermes_agent.gateway.platforms.qqbot.adapter": "hermes_agent.gateway.platforms.qqbot.adapter",
    "hermes_agent.gateway.platforms.qqbot.constants": "hermes_agent.gateway.platforms.qqbot.constants",
    "hermes_agent.gateway.platforms.qqbot.crypto": "hermes_agent.gateway.platforms.qqbot.crypto",
    "hermes_agent.gateway.platforms.qqbot.onboard": "hermes_agent.gateway.platforms.qqbot.onboard",
    "hermes_agent.gateway.platforms.qqbot.utils": "hermes_agent.gateway.platforms.qqbot.utils",
    "hermes_agent.gateway.platforms.qqbot": "hermes_agent.gateway.platforms.qqbot",
    "hermes_agent.gateway.platforms.slack": "hermes_agent.gateway.platforms.slack",
    "hermes_agent.gateway.platforms.discord": "hermes_agent.gateway.platforms.discord",
    "hermes_agent.gateway.platforms.telegram": "hermes_agent.gateway.platforms.telegram",
    "hermes_agent.gateway.platforms.telegram_network": "hermes_agent.gateway.platforms.telegram_network",
    "hermes_agent.gateway.platforms.whatsapp": "hermes_agent.gateway.platforms.whatsapp",
    "hermes_agent.gateway.platforms.base": "hermes_agent.gateway.platforms.base",
    "hermes_agent.gateway.platforms.api_server": "hermes_agent.gateway.platforms.api_server",
    "hermes_agent.gateway.platforms.bluebubbles": "hermes_agent.gateway.platforms.bluebubbles",
    "hermes_agent.gateway.platforms.dingtalk": "hermes_agent.gateway.platforms.dingtalk",
    "hermes_agent.gateway.platforms.email": "hermes_agent.gateway.platforms.email",
    "hermes_agent.gateway.platforms.feishu": "hermes_agent.gateway.platforms.feishu",
    "hermes_agent.gateway.platforms.feishu_comment": "hermes_agent.gateway.platforms.feishu_comment",
    "hermes_agent.gateway.platforms.feishu_comment_rules": "hermes_agent.gateway.platforms.feishu_comment_rules",
    "hermes_agent.gateway.platforms.helpers": "hermes_agent.gateway.platforms.helpers",
    "hermes_agent.gateway.platforms.homeassistant": "hermes_agent.gateway.platforms.homeassistant",
    "hermes_agent.gateway.platforms.matrix": "hermes_agent.gateway.platforms.matrix",
    "hermes_agent.gateway.platforms.mattermost": "hermes_agent.gateway.platforms.mattermost",
    "hermes_agent.gateway.platforms.signal": "hermes_agent.gateway.platforms.signal",
    "hermes_agent.gateway.platforms.sms": "hermes_agent.gateway.platforms.sms",
    "hermes_agent.gateway.platforms.webhook": "hermes_agent.gateway.platforms.webhook",
    "hermes_agent.gateway.platforms.wecom": "hermes_agent.gateway.platforms.wecom",
    "hermes_agent.gateway.platforms.wecom_callback": "hermes_agent.gateway.platforms.wecom_callback",
    "hermes_agent.gateway.platforms.wecom_crypto": "hermes_agent.gateway.platforms.wecom_crypto",
    "hermes_agent.gateway.platforms.weixin": "hermes_agent.gateway.platforms.weixin",
    "hermes_agent.gateway.platforms": "hermes_agent.gateway.platforms",
    "hermes_agent.gateway.channel_directory": "hermes_agent.gateway.channel_directory",
    "hermes_agent.gateway.config": "hermes_agent.gateway.config",
    "hermes_agent.gateway.delivery": "hermes_agent.gateway.delivery",
    "hermes_agent.gateway.display_config": "hermes_agent.gateway.display_config",
    "hermes_agent.gateway.hooks": "hermes_agent.gateway.hooks",
    "hermes_agent.gateway.mirror": "hermes_agent.gateway.mirror",
    "hermes_agent.gateway.pairing": "hermes_agent.gateway.pairing",
    "hermes_agent.gateway.restart": "hermes_agent.gateway.restart",
    "hermes_agent.gateway.run": "hermes_agent.gateway.run",
    "hermes_agent.gateway.session_context": "hermes_agent.gateway.session_context",
    "hermes_agent.gateway.session": "hermes_agent.gateway.session",
    "hermes_agent.gateway.status": "hermes_agent.gateway.status",
    "hermes_agent.gateway.sticker_cache": "hermes_agent.gateway.sticker_cache",
    "hermes_agent.gateway.stream_consumer": "hermes_agent.gateway.stream_consumer",
    "gateway": "gateway",

    # acp_adapter/ -> hermes_agent/acp/
    "hermes_agent.acp.__main__": "hermes_agent.acp.__main__",
    "hermes_agent.acp.auth": "hermes_agent.acp.auth",
    "hermes_agent.acp.entry": "hermes_agent.acp.entry",
    "hermes_agent.acp.events": "hermes_agent.acp.events",
    "hermes_agent.acp.permissions": "hermes_agent.acp.permissions",
    "hermes_agent.acp.server": "hermes_agent.acp.server",
    "hermes_agent.acp.session": "hermes_agent.acp.session",
    "hermes_agent.acp.tools": "hermes_agent.acp.tools",
    "hermes_agent.acp": "hermes_agent.acp",

    # cron/ -> hermes_agent/cron/
    "hermes_agent.cron.jobs": "hermes_agent.cron.jobs",
    "hermes_agent.cron.scheduler": "hermes_agent.cron.scheduler",
    "cron": "cron",

    # plugins/ -> hermes_agent/plugins/
    "hermes_agent.plugins.memory": "hermes_agent.plugins.memory",
    "hermes_agent.plugins.context_engine": "hermes_agent.plugins.context_engine",
    "plugins": "plugins",
}

# Sort by key length descending for longest-prefix matching
_SORTED_KEYS = sorted(IMPORT_MAP.keys(), key=len, reverse=True)


def _map_module(old_module: str) -> str | None:
    """Map an old module path to its new path using longest-prefix matching.

    Returns the new module path, or None if no mapping applies.
    """
    for key in _SORTED_KEYS:
        if old_module == key:
            return IMPORT_MAP[key]
        if old_module.startswith(key + "."):
            suffix = old_module[len(key):]
            return IMPORT_MAP[key] + suffix
    return None


# ---------------------------------------------------------------------------
# Step 2: Rewrite import statements
# ---------------------------------------------------------------------------

# Match: from X import Y   or   from X import (Y, Z)
_FROM_IMPORT_RE = re.compile(
    r'^(\s*)(from\s+)(\S+)(\s+import\s+.*)$'
)

# Match: import X   or   import X as Y   or   import X, Y
_IMPORT_RE = re.compile(
    r'^(\s*)(import\s+)(.+)$'
)


def _rewrite_from_import(line: str) -> str:
    """Rewrite 'from X import Y' lines."""
    m = _FROM_IMPORT_RE.match(line)
    if not m:
        return line

    indent = m.group(1)
    from_kw = m.group(2)
    module_path = m.group(3)
    import_rest = m.group(4)

    new_path = _map_module(module_path)
    if new_path is not None:
        return f"{indent}{from_kw}{new_path}{import_rest}"
    return line


def _rewrite_import(line: str) -> str:
    """Rewrite 'import X' and 'import X as Y' lines."""
    m = _IMPORT_RE.match(line)
    if not m:
        return line

    indent = m.group(1)
    import_kw = m.group(2)
    rest = m.group(3)

    # Handle: import X, Y, Z (multiple imports on one line)
    # Handle: import X as Y
    parts = rest.split(",")
    changed = False
    new_parts = []
    for part in parts:
        part = part.strip()
        # Split "X as Y"
        as_match = re.match(r'^(\S+)(\s+as\s+\S+)?(.*)$', part)
        if as_match:
            mod = as_match.group(1)
            as_clause = as_match.group(2) or ""
            trailing = as_match.group(3) or ""
            new_mod = _map_module(mod)
            if new_mod is not None:
                new_parts.append(f"{new_mod}{as_clause}{trailing}")
                changed = True
            else:
                new_parts.append(part)
        else:
            new_parts.append(part)

    if changed:
        return f"{indent}{import_kw}{', '.join(new_parts)}"
    return line


# ---------------------------------------------------------------------------
# Step 3: Rewrite string-based module references
# ---------------------------------------------------------------------------

# Patterns for string-based module references:
# - patch("module.path.attr")
# - patch("module.path.attr", ...)
# - monkeypatch.setattr("module.path", ...)
# - sys.modules["module.path"]
# - importlib.import_module("module.path")
# - import_module("module.path")

# Match quoted strings that look like old module paths
_OLD_PREFIXES = (
    "agent.", "tools.", "hermes_cli.", "gateway.", "cron.", "acp_adapter.",
    "run_agent.", "hermes_agent.agent.loop", "model_tools.", "hermes_agent.tools.dispatch", "toolsets.",
    "hermes_agent.tools.toolsets", "toolset_distributions.", "hermes_agent.tools.distributions",
    "mcp_serve.", "hermes_agent.tools.mcp.serve", "hermes_constants.", "hermes_constants",
    "hermes_state.", "hermes_state", "hermes_logging.", "hermes_logging",
    "hermes_time.", "hermes_time", "utils.", "utils", "cli.", "cli",
    "plugins.", "plugins", "hermes_agent.tools.browser.camofox_state",
)

def _looks_like_old_module_path(s: str) -> bool:
    """Check if a string looks like an old-style module path."""
    for prefix in _OLD_PREFIXES:
        if s == prefix or s.startswith(prefix):
            return True
    return False


def _rewrite_string_module_ref(s: str) -> str | None:
    """Try to map an old module path string to its new form.

    Returns the new string, or None if no mapping applies.
    For dotted paths like "hermes_agent.agent.loop.some_function", we map the module
    part and keep the attribute.
    """
    # Try exact match first, then longest prefix
    result = _map_module(s)
    if result is not None:
        return result
    return None


# Pattern for string literals in relevant contexts
# Matches both single and double quoted strings
_STRING_REF_RE = re.compile(
    r'''(["'])((?:agent|tools|hermes_cli|gateway|cron|acp_adapter|run_agent|model_tools|toolsets|toolset_distributions|mcp_serve|hermes_constants|hermes_state|hermes_logging|hermes_time|utils|cli|plugins|browser_camofox_state)(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\1'''
)


def _rewrite_string_refs_in_line(line: str) -> str:
    """Rewrite module path strings in a line.

    Handles patch(), monkeypatch.setattr(), sys.modules[], importlib.import_module().
    """
    # Skip lines that are just comments
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return line

    def _replace_match(m: re.Match) -> str:
        quote = m.group(1)
        old_path = m.group(2)
        new_path = _rewrite_string_module_ref(old_path)
        if new_path is not None:
            return f"{quote}{new_path}{quote}"
        return m.group(0)

    return _STRING_REF_RE.sub(_replace_match, line)


# ---------------------------------------------------------------------------
# Main file processor
# ---------------------------------------------------------------------------

def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """Process a single Python file, rewriting imports and string refs.

    Returns True if the file was modified.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return False

    lines = content.split("\n")
    new_lines = []
    changed = False

    for line in lines:
        original = line

        # Step 2: Rewrite import statements
        if re.match(r'\s*from\s+', line):
            line = _rewrite_from_import(line)
        elif re.match(r'\s*import\s+', line):
            # Avoid matching lines like `import_module(...)` which start with "import"
            # but aren't import statements
            if re.match(r'\s*import\s+[a-zA-Z_]', line):
                line = _rewrite_import(line)

        # Step 3: Rewrite string-based module references
        # Only in lines that contain relevant patterns
        if any(kw in line for kw in ('patch(', 'setattr(', 'sys.modules[', 'import_module(',
                                      'sys.modules.pop(', 'sys.modules.get(',
                                      'MODULE_SPEC', 'spec.name')):
            line = _rewrite_string_refs_in_line(line)
        # Also catch sys.modules["X"] = ... assignment patterns
        elif 'sys.modules[' in line:
            line = _rewrite_string_refs_in_line(line)
        # Also rewrite string refs that look like patch decorators
        elif '@patch(' in line or "@patch.object(" in line:
            line = _rewrite_string_refs_in_line(line)
        # Also catch "del sys.modules[...]"
        elif "del sys.modules[" in line:
            line = _rewrite_string_refs_in_line(line)

        if line != original:
            changed = True
        new_lines.append(line)

    if changed and not dry_run:
        filepath.write_text("\n".join(new_lines), encoding="utf-8")

    return changed


def find_python_files(repo_root: Path) -> list[Path]:
    """Find all Python files to process."""
    dirs = [
        repo_root / "hermes_agent",
        repo_root / "tests",
        repo_root / "tui_gateway",
        repo_root / "environments",
        repo_root / "scripts",
    ]

    files = []
    for d in dirs:
        if d.exists():
            files.extend(sorted(d.rglob("*.py")))
    return files


def main():
    dry_run = "--dry-run" in sys.argv

    # Find repo root (the directory containing this script's parent)
    repo_root = Path(__file__).resolve().parent.parent

    if not (repo_root / "hermes_agent").exists():
        print(f"ERROR: hermes_agent/ not found at {repo_root}", file=sys.stderr)
        sys.exit(1)

    py_files = find_python_files(repo_root)
    print(f"Found {len(py_files)} Python files to process")

    modified_count = 0
    for filepath in py_files:
        if process_file(filepath, dry_run=dry_run):
            modified_count += 1
            if dry_run:
                print(f"  [WOULD MODIFY] {filepath.relative_to(repo_root)}")
            else:
                print(f"  [MODIFIED] {filepath.relative_to(repo_root)}")

    action = "Would modify" if dry_run else "Modified"
    print(f"\n{action} {modified_count}/{len(py_files)} files")

    if dry_run:
        print("\nThis was a dry run. No files were changed.")


if __name__ == "__main__":
    main()
