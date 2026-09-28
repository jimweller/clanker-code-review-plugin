"""export.py: the scrubbed, one-commit copy of the reviewed commit that every arm clones."""
import os
import subprocess
import sys

from common import JUDGE_EXCLUDE

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPT = os.path.join(REPO_ROOT, "skills", "review-deep", "scripts", "export.py")


def export(repo, extra_env=None):
    env = {**os.environ, **(extra_env or {})}
    p = subprocess.run([sys.executable, SCRIPT, str(repo["run"])], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    line = [l for l in p.stdout.splitlines() if l.startswith("EXPORT=")]
    assert len(line) == 1, p.stdout
    return line[0].removeprefix("EXPORT=")


def git(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, check=True).stdout


def test_export_holds_the_commit_without_instruction_files_or_review_state(repo):
    e = export(repo)
    assert os.path.realpath(e) == e
    assert not e.startswith(os.path.realpath(repo["repo"]))
    assert os.path.isfile(os.path.join(e, "src", "a.ts"))
    for gone in ("CLAUDE.md", "pkg/CLAUDE.md", ".claude", ".llmtmp"):
        assert not os.path.exists(os.path.join(e, gone)), gone


def test_export_is_its_own_one_commit_repository(repo):
    e = export(repo)
    assert git(e, "rev-parse", "--show-toplevel").strip() == e
    assert len(git(e, "log", "--oneline").splitlines()) == 1
    assert git(e, "status", "--porcelain") == ""


def test_export_ignores_the_operators_git_config(repo, tmp_path):
    hostile = tmp_path / "gitconfig"
    hostile.write_text("[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = false\n[core]\n\thooksPath = /nonexistent\n")
    e = export(repo, {"GIT_CONFIG_GLOBAL": str(hostile)})
    assert len(git(e, "log", "--oneline").splitlines()) == 1


def test_scrub_list_names_every_agent_instruction_and_config_file():
    for name in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "GEMINI.md", ".claude", ".agents", ".opencode",
                 "opencode.json", "opencode.jsonc", ".mcp.json", ".serena", ".gemini", ".codex", ".cursor", ".cursorrules",
                 ".windsurfrules", ".clinerules", ".github/copilot-instructions.md", ".llmtmp", ".llmdocs"):
        assert name in JUDGE_EXCLUDE, name
