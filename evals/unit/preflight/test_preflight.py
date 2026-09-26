"""preflight.py: PASS/FAIL checks per tier, run as a subprocess against a temp HOME and PATH."""
import json
import os
import shutil

import pytest

from conftest import AREAS, BINARIES, run_preflight

MISSABLE = [b for b in BINARIES if b != "npx"]


def test_all_present_passes_deep_tier(home, stub_bin, tmp_path):
    p = run_preflight("deep", home, stub_bin, tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "FAIL" not in p.stdout


@pytest.mark.parametrize("missing", MISSABLE)
def test_each_missing_binary_fails(missing, home, stub_bin, tmp_path):
    bin_dir = tmp_path / "bin-missing"
    bin_dir.mkdir()
    for name in BINARIES:
        if name != missing:
            shutil.copy(os.path.join(stub_bin, name), bin_dir / name)
            os.chmod(bin_dir / name, 0o755)
    p = run_preflight("deep", home, str(bin_dir), tmp_path)
    assert p.returncode == 1
    assert any(missing in line and line.startswith("FAIL") for line in p.stdout.splitlines()), p.stdout


def test_model_missing_from_whitelist_fails(home, stub_bin, tmp_path):
    data = json.loads(open(os.path.join(home, ".config/opencode/opencode.json")).read())
    data["provider"]["google"]["whitelist"] = []
    open(os.path.join(home, ".config/opencode/opencode.json"), "w").write(json.dumps(data))
    p = run_preflight("deep", home, stub_bin, tmp_path)
    assert p.returncode == 1
    assert any("missing from whitelist" in line and "gemini" in line for line in p.stdout.splitlines()), p.stdout


def test_empty_key_fails_and_secret_is_absent_from_output(home, stub_bin, tmp_path):
    secret = "SECRET-VALUE-DO-NOT-LEAK"
    p = run_preflight("deep", home, stub_bin, tmp_path,
                       extra_env={"OPENAI_KEY": "", "GEMINI_API_KEY": secret, "ANTHROPIC_FOUNDRY_API_KEY": secret})
    assert p.returncode == 1
    lines = p.stdout.splitlines()
    assert any(line.startswith("FAIL") and "openai" in line and "api key" in line for line in lines), p.stdout
    assert secret not in p.stdout and secret not in p.stderr


def test_missing_plugin_agents_fails_full_tier(home, stub_bin, tmp_path):
    plugin_root = tmp_path / "plugin"
    (plugin_root / "agents").mkdir(parents=True)
    for area in AREAS[:-1]:
        (plugin_root / "agents" / f"reviewer-{area}.md").write_text("body\n")
    p = run_preflight("full", home, stub_bin, tmp_path, extra_args=["--harness", "claude", "--plugin-root", str(plugin_root)])
    assert p.returncode == 1
    assert any("nine claude reviewer agents present" in line and line.startswith("FAIL") for line in p.stdout.splitlines()), p.stdout
    assert AREAS[-1] in p.stdout


def test_hermes_on_full_fails(home, stub_bin, tmp_path):
    p = run_preflight("full", home, stub_bin, tmp_path, extra_args=["--harness", "hermes"])
    assert p.returncode == 1
    assert "no subagent-dispatchable reviewer agents" in p.stdout


def test_pruned_commit_fails_tickets_tier(tmp_path):
    import subprocess
    import sys

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("one\n")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "one"], check=True, env=env)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps({"repo": str(repo), "commit": "0" * 40}))
    from conftest import PREFLIGHT
    p = subprocess.run([sys.executable, PREFLIGHT, "--tier", "tickets", "--run", str(run_dir)], capture_output=True, text=True)
    assert p.returncode == 1
    assert any("reviewed commit is still an object" in line and line.startswith("FAIL") for line in p.stdout.splitlines()), p.stdout


def test_canary_absent_passes_as_not_needed(home, stub_bin, tmp_path):
    p = run_preflight("deep", home, stub_bin, tmp_path)
    assert any(line == "PASS mcg-sensitive-canary scanner: not needed" for line in p.stdout.splitlines()), p.stdout


def test_canary_present_but_not_executable_fails(home, stub_bin, tmp_path):
    bin_dir = tmp_path / "bin-canary"
    bin_dir.mkdir()
    for name in os.listdir(stub_bin):
        shutil.copy(os.path.join(stub_bin, name), bin_dir / name)
        os.chmod(bin_dir / name, 0o755)
    canary = bin_dir / "mcg-sensitive-canary"
    canary.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(canary, 0o644)
    p = run_preflight("deep", home, str(bin_dir), tmp_path)
    assert p.returncode == 1
    assert any("mcg-sensitive-canary scanner executable" in line and line.startswith("FAIL") for line in p.stdout.splitlines()), p.stdout


def test_full_tier_prints_label_and_agent_prefix_for_claude_harness(home, stub_bin, tmp_path):
    plugin_root = tmp_path / "plugin"
    (plugin_root / "agents").mkdir(parents=True)
    for area in AREAS:
        (plugin_root / "agents" / f"reviewer-{area}.md").write_text("body\n")
    p = run_preflight("full", home, stub_bin, tmp_path, extra_args=["--harness", "claude", "--plugin-root", str(plugin_root)])
    lines = p.stdout.splitlines()
    assert "LABEL=claude" in lines
    assert "AGENT_PREFIX=clanker-code-review:" in lines


def test_full_tier_prints_empty_agent_prefix_for_codex_harness(home, stub_bin, tmp_path):
    codex_agents = os.path.join(home, ".codex", "agents")
    os.makedirs(codex_agents, exist_ok=True)
    for area in AREAS:
        open(os.path.join(codex_agents, f"reviewer-{area}.toml"), "w").write("body\n")
    p = run_preflight("full", home, stub_bin, tmp_path, extra_args=["--harness", "codex"])
    lines = p.stdout.splitlines()
    assert "LABEL=codex" in lines
    assert "AGENT_PREFIX=" in lines
