import json
import os
import stat
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PREFLIGHT = os.path.join(REPO_ROOT, "skills", "review-deep", "scripts", "preflight.py")

BINARIES = ["python3", "git", "claude", "uv", "jq", "ocr", "opencode", "serena", "npx"]

AREAS = ["architecture", "correctness", "data", "ops", "performance", "quality", "security", "solid", "testing"]


def write_stub(bin_dir, name, body="exit 0\n"):
    p = os.path.join(bin_dir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n" + body)
    st = os.stat(p)
    os.chmod(p, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


@pytest.fixture
def stub_bin(tmp_path):
    """A PATH directory with #!/bin/sh stubs for every binary preflight looks for."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in BINARIES:
        if name == "python3":
            write_stub(str(bin_dir), name, 'echo "Python 3.11.0"\n')
        elif name == "opencode":
            write_stub(str(bin_dir), name,
                       'if [ "$1" = "models" ]; then\n'
                       '  printf "%s\\n" "openai/gpt-6-sol" "google/gemini-3.8-flash" "az-anthropic/claude-opus-5-5"\n'
                       "fi\n")
        else:
            write_stub(str(bin_dir), name)
    return str(bin_dir)


def opencode_json(whitelist_override=None):
    def provider(models, whitelist, api_key_var):
        return {"options": {"apiKey": f"{{env:{api_key_var}}}"}, "models": {m: {} for m in models}, "whitelist": whitelist}

    wl = dict(whitelist_override or {})
    return {
        "provider": {
            "openai": provider(["gpt-6-sol"], wl.get("openai", ["gpt-6-sol"]), "OPENAI_KEY"),
            "google": provider(["gemini-3.8-flash"], wl.get("google", ["gemini-3.8-flash"]), "GEMINI_API_KEY"),
            "az-anthropic": provider(["claude-opus-5-5"], wl.get("az-anthropic", ["claude-opus-5-5"]), "ANTHROPIC_FOUNDRY_API_KEY"),
        },
        "enabled_providers": ["openai", "google", "az-anthropic"],
        "mcp": {"serena": {"enabled": True}, "researcher": {"enabled": False}, "repomix": {"enabled": True}},
    }


@pytest.fixture
def home(tmp_path):
    """A temp HOME with every deep-tier config file preflight expects, all valid."""
    h = tmp_path / "home"
    (h / ".config" / "opencode" / "agents").mkdir(parents=True)
    (h / ".serena-reviewer").mkdir(parents=True)
    (h / ".opencodereview").mkdir(parents=True)

    (h / ".config" / "opencode" / "opencode.json").write_text(json.dumps(opencode_json()))
    (h / ".config" / "opencode" / "reviewer.json").write_text(json.dumps({
        "instructions": ["~/.serena-reviewer/system-prompt.md"],
        "mcp": {"serena": {"command": ["serena", "start-mcp-server"], "environment": {"SERENA_HOME": "{env:HOME}/.serena-reviewer"}}},
    }))
    for f in ("serena_config.yml", "reviewer-context.yml", "system-prompt.md"):
        (h / ".serena-reviewer" / f).write_text("placeholder\n")
    for area in AREAS:
        (h / ".config" / "opencode" / "agents" / f"reviewer-{area}.md").write_text("---\nmode: primary\n---\nbody\n")
    (h / ".opencodereview" / "config.json").write_text(json.dumps({
        "provider": "az-anthropic",
        "custom_providers": {"az-anthropic": {"api_key_cmd": "printenv ANTHROPIC_FOUNDRY_API_KEY"}},
    }))
    return str(h)


def run_preflight(tier, home, bin_dir, tmp_path, extra_args=(), extra_env=None, keys=("OPENAI_KEY", "GEMINI_API_KEY", "ANTHROPIC_FOUNDRY_API_KEY")):
    env = {"HOME": home, "PATH": bin_dir, "XDG_CACHE_HOME": str(tmp_path / "cache")}
    for k in keys:
        env[k] = "dummy-secret-value"
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, PREFLIGHT, "--tier", tier, *extra_args], capture_output=True, text=True, env=env,
                          cwd=str(tmp_path))
