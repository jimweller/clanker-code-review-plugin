"""opencode_env.py: the generated, minimal opencode config every review-deep arm runs under."""
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPT = os.path.join(REPO_ROOT, "skills", "review-deep", "scripts", "opencode_env.py")
AREAS = ["architecture", "correctness", "data", "ops", "performance", "quality", "security", "solid", "testing"]
SERENA_WRITES = ["serena_insert_*", "serena_replace_*", "serena_rename_*", "serena_safe_delete_*"]

USER_CONFIG = {
    "provider": {"google": {"options": {"apiKey": "{env:GEMINI_API_KEY}"}, "models": {"gemini-3.8-flash": {}}}},
    "enabled_providers": ["google"],
    "mcp": {"context7": {"type": "remote", "url": "https://example.invalid", "enabled": True},
            "serena": {"type": "local", "command": ["serena"], "enabled": True}},
    "plugin": ["some-plugin"],
    "instructions": ["~/personal-rules.md"],
    "agent": {"build": {"mode": "primary"}},
}


def generate(tmp_path, state_inside=True):
    project = tmp_path / "project"
    project.mkdir()
    state = project / ".llmtmp" / "review-deep" if state_inside else tmp_path / "state"
    state.mkdir(parents=True)
    user = tmp_path / "user-opencode.json"
    user.write_text(json.dumps(USER_CONFIG))
    p = subprocess.run([sys.executable, SCRIPT, str(project), str(state), "--user-config", str(user),
                        "--serena-home", str(tmp_path / "serena-home")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    xdg = state / "opencode-config"
    cfg = json.loads((xdg / "opencode" / "opencode.json").read_text())
    return p, cfg, xdg, state


def test_prints_the_xdg_config_home_arm_sh_exports(tmp_path):
    p, _, xdg, _ = generate(tmp_path)
    assert f"OPENCODE_XDG={xdg}" in p.stdout.splitlines()


def test_keeps_the_users_providers_and_nothing_else_personal(tmp_path):
    _, cfg, _, _ = generate(tmp_path)
    assert cfg["provider"] == USER_CONFIG["provider"]
    assert cfg["enabled_providers"] == ["google"]
    assert list(cfg["mcp"]) == ["serena"]
    assert "plugin" not in cfg
    assert set(cfg["agent"]) == {f"reviewer-{a}" for a in AREAS}
    assert all("personal-rules" not in i for i in cfg["instructions"])


def test_serena_runs_the_plugin_context_under_the_given_home(tmp_path):
    _, cfg, _, _ = generate(tmp_path)
    serena = cfg["mcp"]["serena"]
    ctx = serena["command"][serena["command"].index("--context") + 1]
    assert os.path.isfile(ctx) and ctx.startswith(REPO_ROOT)
    assert "--project-from-cwd" in serena["command"]
    assert serena["environment"]["SERENA_HOME"] == str(tmp_path / "serena-home")
    assert all(os.path.isfile(i) and i.startswith(REPO_ROOT) for i in cfg["instructions"])


@pytest.mark.parametrize("area", AREAS)
def test_agent_prompt_is_the_plugin_agent_body_without_frontmatter(tmp_path, area):
    _, cfg, _, _ = generate(tmp_path)
    agent = cfg["agent"][f"reviewer-{area}"]
    assert agent["mode"] == "primary"
    path = agent["prompt"].removeprefix("{file:").removesuffix("}")
    body = open(path, encoding="utf-8").read()
    source = open(os.path.join(REPO_ROOT, "agents", f"reviewer-{area}.md"), encoding="utf-8").read()
    assert not body.startswith("---")
    assert source.endswith(body)
    assert "Your area is" in body


def test_agents_get_read_search_serena_and_write_only(tmp_path):
    _, cfg, _, _ = generate(tmp_path)
    tools = cfg["agent"]["reviewer-security"]["tools"]
    assert list(tools)[0] == "*" and tools["*"] is False, "deny-all must come first; later entries win"
    for t in ("read", "grep", "glob", "edit", "write", "apply_patch", "serena_*"):
        assert tools[t] is True, t
    for t in SERENA_WRITES + ["skill", "task", "bash", "webfetch"]:
        assert tools.get(t, False) is False, t
    perm = cfg["agent"]["reviewer-security"]["permission"]
    assert perm["skill"] == {"*": "deny"} and perm["task"] == {"*": "deny"}


def test_writes_are_limited_to_parts_and_coverage_relative_to_the_project(tmp_path):
    _, cfg, _, _ = generate(tmp_path)
    perm = cfg["agent"]["reviewer-security"]["permission"]
    assert list(perm["edit"].items()) == [("*", "deny"), (".llmtmp/review-deep/parts/*", "allow"),
                                          (".llmtmp/review-deep/coverage/*", "allow")]
    assert perm["external_directory"] == {"*": "deny"}


def test_state_dir_outside_the_project_gets_relative_edit_and_absolute_external_rules(tmp_path):
    _, cfg, _, state = generate(tmp_path, state_inside=False)
    perm = cfg["agent"]["reviewer-security"]["permission"]
    real = os.path.realpath(state)
    assert perm["edit"]["../state/parts/*"] == "allow"
    assert perm["external_directory"][f"{real}/parts/*"] == "allow"
    assert perm["external_directory"][f"{real}/coverage/*"] == "allow"
    assert list(perm["external_directory"].items())[0] == ("*", "deny")


def test_missing_user_config_fails_loudly(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    p = subprocess.run([sys.executable, SCRIPT, str(project), str(project), "--user-config", str(tmp_path / "nope.json")],
                       capture_output=True, text=True)
    assert p.returncode != 0
    assert "nope.json" in p.stderr
