"""Cross-repo invariants: identical shared modules, resolvable script references, plugin hygiene."""
import filecmp
import glob
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SKILL_MD = sorted(glob.glob(os.path.join(REPO_ROOT, "skills", "*", "SKILL.md")))
AGENTS = sorted(glob.glob(os.path.join(REPO_ROOT, "agents", "*.md")))
SCRIPT_REF = re.compile(r'\$(?:\{)?([A-Za-z_][A-Za-z0-9_]*)(?:\})?/([A-Za-z0-9_./-]+\.py)')
ASSIGN = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)="?\$\{CLAUDE_SKILL_DIR\}(/\.\./review-deep)?/scripts"?', re.M)
NAME_FRONTMATTER = re.compile(r'^name:\s*(\S+)\s*$', re.M)


def test_pool_and_evidence_are_byte_identical_across_the_two_skills():
    deep = os.path.join(REPO_ROOT, "skills", "review-deep", "scripts")
    tickets = os.path.join(REPO_ROOT, "skills", "review-tickets", "scripts")
    for name in ("pool.py", "evidence.py"):
        a, b = os.path.join(deep, name), os.path.join(tickets, name)
        assert os.path.exists(a) and os.path.exists(b), f"{name} missing from one of the two copies"
        assert filecmp.cmp(a, b, shallow=False), f"{name} differs between review-deep and review-tickets"


def resolve_vars(skill_md_path, text):
    """Every scripts-path variable a SKILL.md assigns, mapped to the directory it resolves to."""
    own_scripts = os.path.join(os.path.dirname(skill_md_path), "scripts")
    deep_scripts = os.path.join(REPO_ROOT, "skills", "review-deep", "scripts")
    resolved = {}
    for name, sibling in ASSIGN.findall(text):
        resolved[name] = deep_scripts if sibling else own_scripts
    if "<this skill's directory>/scripts" in text:
        resolved.setdefault("S", own_scripts)
    return resolved


def test_every_script_path_variable_reference_in_a_skill_md_exists():
    checked = 0
    for skill_md in SKILL_MD:
        text = open(skill_md, encoding="utf-8").read()
        refs = SCRIPT_REF.findall(text)
        if not refs:
            continue
        by_var = resolve_vars(skill_md, text)
        for var, rel in refs:
            resolved = by_var.get(var)
            assert resolved, f"{skill_md} references ${var}/{rel} but never assigns {var} to a resolvable directory"
            checked += 1
            path = os.path.join(resolved, rel)
            assert os.path.exists(path), f"{skill_md} references ${var}/{rel}, not found at {path}"
    assert checked > 0, "no $VAR/*.py references found across any SKILL.md; the resolver or the glob is broken"


def test_prompts_directories_hold_only_txt_files():
    prompt_files = glob.glob(os.path.join(REPO_ROOT, "skills", "*", "prompts", "*"))
    assert prompt_files, "no prompt files found; the glob is broken"
    non_txt = [p for p in prompt_files if not p.endswith(".txt")]
    assert non_txt == [], f"non-.txt files under a prompts/ directory: {non_txt}"


def test_every_agent_name_equals_its_file_stem():
    assert AGENTS, "no agent files found under agents/; the glob is broken"
    mismatches = []
    for path in AGENTS:
        stem = os.path.splitext(os.path.basename(path))[0]
        m = NAME_FRONTMATTER.search(open(path, encoding="utf-8").read())
        name = m.group(1) if m else None
        if name != stem:
            mismatches.append((path, name))
    assert mismatches == [], f"agent name != file stem: {mismatches}"


def test_no_skill_md_names_dotfiles_specific_paths():
    violations = []
    for skill_md in SKILL_MD:
        for lineno, line in enumerate(open(skill_md, encoding="utf-8"), 1):
            if "configs/opencode" in line or ".config/dotfiles" in line:
                violations.append(f"{skill_md}:{lineno}: {line.strip()}")
    assert violations == [], "SKILL.md names a dotfiles-specific path:\n" + "\n".join(violations)


def test_every_reviewer_can_rate_critical_with_the_verifiers_definition():
    verify = open(os.path.join(REPO_ROOT, "skills", "review-deep", "prompts", "verify.txt"), encoding="utf-8").read()
    definition = "an exploitable security flaw, or data loss or corruption in normal use"
    assert definition in verify
    for path in AGENTS:
        text = open(path, encoding="utf-8").read()
        assert "Severity is `Critical`, `High`, `Medium`, or `Low`" in text, path
        assert definition in text, path
