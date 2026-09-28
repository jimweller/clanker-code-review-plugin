#!/usr/bin/env python3
"""Generate the minimal opencode config every review-deep arm runs under. No model calls.

    python3 opencode_env.py STATE_DIR [--user-config PATH] [--serena-home DIR]

Writes STATE_DIR/opencode-config/opencode/opencode.json and one prompt file per area, and prints
OPENCODE_XDG. arm.sh exports that as XDG_CONFIG_HOME, so opencode reads this file as its whole
global config and never reads the operator's: no personal agents, skills, rules, plugins, or MCP
servers. Credentials live under XDG_DATA_HOME or in environment variables, so they still resolve.

Kept from the operator's config: provider and enabled_providers. Added: Serena as the only MCP
server, run with this plugin's reviewer context and manual, and nine primary agents whose prompts
are the bodies of this plugin's agents/reviewer-<area>.md, the same text the Claude reviewers use.

An agent's tools map starts with "*": false and allows reading, searching, Serena's read tools,
and writing. opencode evaluates the last matching rule, so the deny-all goes first. Each arm runs
in its own copy of the export, so one shared rule isolates all of them: external_directory denies
every path outside the copy, and edit allows only .review-arm/, where arm.sh puts the arm's ledger
and collects its findings. opencode matches edit rules against the path relative to the project's
git root. Serena is a separate process these rules do not reach.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
SERENA_DIR = os.path.join(SKILL_ROOT, "opencode", "serena")
AREAS = ["architecture", "correctness", "data", "ops", "performance", "quality", "security", "solid", "testing"]
TOOLS = {"*": False, "read": True, "grep": True, "glob": True, "edit": True, "write": True, "apply_patch": True,
         "serena_*": True, "serena_insert_*": False, "serena_replace_*": False, "serena_rename_*": False,
         "serena_safe_delete_*": False}


def body(path):
    text = open(path, encoding="utf-8").read()
    if text.startswith("---\n"):
        text = text[text.index("\n---\n", 4) + 5:]
    return text


def build(user, serena_home, prompts_dir):
    agents = {}
    for area in AREAS:
        prompt = os.path.join(prompts_dir, f"reviewer-{area}.md")
        with open(prompt, "w", encoding="utf-8") as f:
            f.write(body(os.path.join(PLUGIN_ROOT, "agents", f"reviewer-{area}.md")))
        agents[f"reviewer-{area}"] = {
            "description": f"{area} review perspective, dispatched by review-deep",
            "mode": "primary",
            "prompt": f"{{file:{prompt}}}",
            "tools": dict(TOOLS),
            "permission": {"task": {"*": "deny"}, "skill": {"*": "deny"}, "edit": {"*": "deny", ".review-arm/*": "allow"},
                           "external_directory": {"*": "deny"}},
        }
    cfg = {"$schema": "https://opencode.ai/config.json", "autoupdate": False, "provider": user.get("provider", {})}
    if "enabled_providers" in user:
        cfg["enabled_providers"] = user["enabled_providers"]
    cfg["instructions"] = [os.path.join(SERENA_DIR, "system-prompt.md")]
    cfg["mcp"] = {"serena": {
        "type": "local",
        "command": ["serena", "start-mcp-server", "--context", os.path.join(SERENA_DIR, "reviewer-context.yml"),
                    "--mode", "planning", "--mode", "one-shot", "--project-from-cwd"],
        "environment": {"SERENA_HOME": serena_home},
        "enabled": True,
    }}
    cfg["agent"] = agents
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("state")
    ap.add_argument("--user-config", default=os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                                                          "opencode", "opencode.json"))
    ap.add_argument("--serena-home", default=os.path.expanduser("~/.serena-reviewer"))
    a = ap.parse_args()
    try:
        user = json.load(open(a.user_config, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"cannot read the operator's opencode config {a.user_config}: {e}")
    xdg = os.path.join(os.path.abspath(a.state), "opencode-config")
    prompts = os.path.join(xdg, "prompts")
    os.makedirs(os.path.join(xdg, "opencode"), exist_ok=True)
    os.makedirs(prompts, exist_ok=True)
    cfg = build(user, a.serena_home, prompts)
    json.dump(cfg, open(os.path.join(xdg, "opencode", "opencode.json"), "w", encoding="utf-8"), indent=1)
    print(f"OPENCODE_XDG={xdg}")


if __name__ == "__main__":
    main()
