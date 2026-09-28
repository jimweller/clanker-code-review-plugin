#!/usr/bin/env python3
"""Preflight checks before a review-deep, review-full, review-diff, or review-tickets run.

    python3 preflight.py --tier deep|full|diff|tickets
                          [--harness claude|codex|opencode|hermes] [--run RUN] [--plugin-root DIR]

Prints one PASS or FAIL line per check, in the order run, and exits 1 when any check fails. Never
prints a secret value, only whether the environment variable a config references is set and
non-empty.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
AREAS = ["architecture", "correctness", "data", "ops", "performance", "quality", "security", "solid", "testing"]
CORE_SCRIPTS = ["common.py", "init_run.py", "checkout.py", "normalize.py", "collate.py", "windows.py", "merge.py",
                "rank.py", "verify.py", "report.py", "ledger.py", "partition.py", "check_reviews.py", "evidence.py", "pool.py",
                "opencode_env.py"]
ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def check(name, passed, detail=""):
    return {"name": name, "ok": bool(passed), "detail": detail}


def read_json(path):
    if not os.path.exists(path):
        return None, f"{path} not found"
    try:
        return json.load(open(path, encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"{path}: invalid json ({e})"


def env_var_ref(value):
    m = ENV_REF.search(str(value or ""))
    return m.group(1) if m else None


# ---- checks common to every tier ----

def check_python3():
    exe = shutil.which("python3")
    if not exe:
        return check("python3 on PATH", False, "not found")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()
    m = re.search(r"(\d+)\.(\d+)", out)
    version_ok = bool(m) and (int(m.group(1)), int(m.group(2))) >= (3, 9)
    return check("python3 >= 3.9", version_ok, out or "version not parsed")


def check_binary(name):
    path = shutil.which(name)
    return check(f"{name} on PATH", bool(path), path or "not found")


def check_scripts_and_prompts():
    missing = [f for f in CORE_SCRIPTS if not os.path.exists(os.path.join(HERE, f))]
    prompts = os.path.join(SKILL_ROOT, "prompts")
    if not os.path.isdir(prompts):
        missing.append("prompts/")
    return check("review-deep scripts and prompts present", not missing, f"missing {missing}" if missing else "")


def check_cache_writable():
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    try:
        os.makedirs(cache, exist_ok=True)
        probe = os.path.join(cache, ".preflight-write-test")
        open(probe, "w", encoding="utf-8").write("x")
        os.remove(probe)
        return check("cache dir writable", True, cache)
    except OSError as e:
        return check("cache dir writable", False, str(e))


def all_tier_checks():
    return [check_python3(), check_binary("git"), check_binary("claude"), check_binary("uv"),
            check_scripts_and_prompts(), check_cache_writable()]


# ---- deep tier ----

def parse_models_line():
    text = open(os.path.join(SKILL_ROOT, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r'^MODELS="([^"]+)"', text, re.M)
    if not m:
        return {}
    pairs = {}
    for tok in m.group(1).split():
        label, _, spec = tok.partition(":")
        pairs[label] = spec
    return pairs


def check_opencode_json():
    path = os.path.expanduser("~/.config/opencode/opencode.json")
    data, err = read_json(path)
    if data is None:
        return [check("opencode.json readable", False, err)]
    results = []
    enabled_providers = set(data.get("enabled_providers", []))
    providers = data.get("provider", {})
    for label, spec in parse_models_line().items():
        prov, _, model = spec.partition("/")
        p = providers.get(prov, {})
        problems = []
        if model not in p.get("models", {}):
            problems.append("missing from provider models")
        if model not in p.get("whitelist", []):
            problems.append("missing from whitelist")
        if prov not in enabled_providers:
            problems.append(f"provider {prov} not in enabled_providers")
        results.append(check(f"opencode.json has {label} ({spec})", not problems, "; ".join(problems)))
        var = env_var_ref(p.get("options", {}).get("apiKey"))
        results.append(check(f"{prov} provider api key env var set",
                             bool(var) and bool(os.environ.get(var)),
                             "no apiKey env reference" if not var else (f"{var} not set" if not os.environ.get(var) else var)))
    return results


def check_serena_home():
    path = os.path.expanduser("~/.serena-reviewer/serena_config.yml")
    return check("~/.serena-reviewer/serena_config.yml present", os.path.exists(path), "" if os.path.exists(path) else f"{path} not found")


def check_arm_agent_sources():
    missing = [f"agents/reviewer-{a}.md" for a in AREAS if not os.path.exists(os.path.join(PLUGIN_ROOT, "agents", f"reviewer-{a}.md"))]
    missing += [f"opencode/serena/{f}" for f in ("reviewer-context.yml", "system-prompt.md")
                if not os.path.exists(os.path.join(SKILL_ROOT, "opencode", "serena", f))]
    return check("plugin reviewer agents and serena reviewer files present", not missing, f"missing {missing}" if missing else "")


def check_opencodereview_config():
    path = os.path.expanduser("~/.opencodereview/config.json")
    data, err = read_json(path)
    if data is None:
        return check("~/.opencodereview/config.json has an active provider with a key", False, err)
    active = data.get("provider")
    entry = data.get("providers", {}).get(active) or data.get("custom_providers", {}).get(active)
    if not active or not entry:
        return check("~/.opencodereview/config.json has an active provider with a key", False,
                     f"active provider {active!r} not defined")
    m = re.search(r"printenv\s+(\S+)", entry.get("api_key_cmd", ""))
    var = m.group(1) if m else None
    ok = bool(var) and bool(os.environ.get(var))
    detail = "no api_key_cmd" if not var else ("not set" if not os.environ.get(var) else "set")
    return check(f"~/.opencodereview/config.json active provider {active} has a key", ok, detail)


def check_opencode_models_lists(models):
    exe = shutil.which("opencode")
    if not exe:
        return check("opencode models lists every reviewer model", False, "opencode not on PATH")
    p = subprocess.run([exe, "models"], capture_output=True, text=True)
    listed = set(p.stdout.split())
    missing = [spec for spec in models.values() if spec not in listed]
    return check("opencode models lists every reviewer model", not missing, f"missing {missing}" if missing else "")


def deep_tier_checks():
    results = list(all_tier_checks())
    for name in ("jq", "ocr", "opencode", "serena"):
        results.append(check_binary(name))
    results += check_opencode_json()
    results.append(check_serena_home())
    results.append(check_arm_agent_sources())
    results.append(check_opencodereview_config())
    results.append(check_opencode_models_lists(parse_models_line()))
    return results


# ---- full / diff tiers ----

def check_sibling_engine():
    ok = all(os.path.exists(os.path.join(HERE, f)) for f in ("init_run.py", "ledger.py", "partition.py", "check_reviews.py"))
    return check("sibling review-deep engine present", ok, HERE)


def check_reviewer_agents_for_harness(harness, plugin_root):
    if harness == "claude":
        if not plugin_root:
            return check("nine claude reviewer agents present", False, "--plugin-root required for harness claude")
        missing = [a for a in AREAS if not os.path.exists(os.path.join(plugin_root, "agents", f"reviewer-{a}.md"))]
        return check("nine claude reviewer agents present", not missing, f"missing {missing}" if missing else "")
    if harness == "codex":
        missing = [a for a in AREAS if not os.path.exists(os.path.expanduser(f"~/.codex/agents/reviewer-{a}.toml"))]
        return check("nine codex reviewer agents present", not missing, f"missing {missing}" if missing else "")
    return check("subagent-dispatchable reviewer agents", False, "no subagent-dispatchable reviewer agents")


def check_npx():
    return check_binary("npx")


def check_repomix_mcp(harness):
    if harness == "opencode":
        data, err = read_json(os.path.expanduser("~/.config/opencode/opencode.json"))
        ok = bool(data) and data.get("mcp", {}).get("repomix", {}).get("enabled") is True
        return check("repomix mcp server configured", ok, err or "")
    if harness == "claude":
        data, err = read_json(os.path.expanduser("~/.claude.json"))
        ok = bool(data) and "repomix" in (data.get("mcpServers") or {})
        return check("repomix mcp server configured", ok, err or ("not in ~/.claude.json mcpServers" if not ok else ""))
    if harness == "codex":
        path = os.path.expanduser("~/.codex/config.toml")
        ok = os.path.exists(path) and "repomix" in open(path, encoding="utf-8").read()
        return check("repomix mcp server configured", ok, "" if ok else f"repomix not found in {path}")
    return check("repomix mcp server configured", False, f"unknown harness {harness}")


def check_diff_base_resolves():
    for ref in ("origin/main", "main"):
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], capture_output=True, text=True)
        if r.returncode == 0:
            return check("origin/main or main resolves", True, ref)
    return check("origin/main or main resolves", False, "neither resolves")


def full_tier_checks(harness, plugin_root):
    results = list(all_tier_checks())
    results.append(check_sibling_engine())
    results.append(check_reviewer_agents_for_harness(harness, plugin_root))
    results.append(check_npx())
    results.append(check_repomix_mcp(harness))
    return results


def diff_tier_checks(harness, plugin_root):
    results = list(all_tier_checks())
    results.append(check_sibling_engine())
    results.append(check_reviewer_agents_for_harness(harness, plugin_root))
    results.append(check_diff_base_resolves())
    return results


AGENT_PREFIX = {"claude": "clanker-code-review:", "codex": ""}


def harness_constants(harness):
    """LABEL names the reviewer source (the $LABEL-<area>.md prefix normalize.py expects).
    AGENT_PREFIX namespaces the subagent type a full or diff run dispatches; codex agents carry
    no such prefix."""
    return harness, AGENT_PREFIX.get(harness, "")


# ---- tickets tier ----

def tickets_tier_checks(run):
    results = list(all_tier_checks())
    if not run:
        return results + [check("--run is required for --tier tickets", False)]
    run_json = os.path.join(run, "run.json")
    if not os.path.exists(run_json):
        return results + [check("run.json exists", False, run_json)]
    data = json.load(open(run_json, encoding="utf-8"))
    results.append(check("run.json exists", True, run_json))
    repo = data.get("repo", "")
    results.append(check("repo exists", os.path.isdir(repo), repo))
    commit = data.get("commit", "")
    obj_ok = bool(repo) and bool(commit) and subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode == 0
    results.append(check("reviewed commit is still an object", obj_ok,
                         "" if obj_ok else f"{commit} not found in {repo} (pruned?)"))
    for rel in ("checkout", "issues.jsonl", "verify/results.jsonl"):
        p = os.path.join(run, rel)
        results.append(check(f"{rel} exists", os.path.exists(p), p))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["deep", "full", "diff", "tickets"])
    ap.add_argument("--harness", choices=["claude", "codex", "opencode", "hermes"])
    ap.add_argument("--run")
    ap.add_argument("--plugin-root")
    a = ap.parse_args()

    if a.tier == "deep":
        results = deep_tier_checks()
    elif a.tier == "full":
        results = full_tier_checks(a.harness, a.plugin_root)
    elif a.tier == "diff":
        results = diff_tier_checks(a.harness, a.plugin_root)
    else:
        results = tickets_tier_checks(a.run)

    for r in results:
        print(f"{'PASS' if r['ok'] else 'FAIL'} {r['name']}" + (f": {r['detail']}" if r["detail"] else ""))
    if a.tier in ("full", "diff") and a.harness in ("claude", "codex"):
        label, agent_prefix = harness_constants(a.harness)
        print(f"LABEL={label}")
        print(f"AGENT_PREFIX={agent_prefix}")
    if any(not r["ok"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
