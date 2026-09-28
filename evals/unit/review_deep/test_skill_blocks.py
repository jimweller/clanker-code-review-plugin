"""The bash in the review-deep SKILL.md: arm.sh, Step 2b, and the Step 3 extract-and-merge block, run against a stub opencode."""
import os
import re
import shutil
import subprocess
import time
import types

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TEXT = open(os.path.join(REPO_ROOT, "skills", "review-deep", "SKILL.md"), encoding="utf-8").read()

pytestmark = pytest.mark.skipif(not (shutil.which("bash") and shutil.which("jq")), reason="needs bash and jq")

STUB_OPENCODE = r'''#!/bin/bash
n=$(( $(cat "$STUB_DIR/calls" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$STUB_DIR/calls"
env | grep -E '^(XDG_CONFIG_HOME|OPENCODE_[A-Z_]+)=' | sort > "$STUB_DIR/env"
printf '%s\n' "$@" > "$STUB_DIR/args"
out=$(printf '%s\n' "${@: -1}" | sed -n 's/^OUTPUT_PATH: //p')
cov=$(printf '%s\n' "${@: -1}" | sed -n 's/^COVERAGE_PATH: //p')
dir=$(printf '%s\n' "$@" | sed -n '/^--dir$/{n;p;}')
echo "$dir" > "$STUB_DIR/dir"
ls -A "$dir" > "$STUB_DIR/listing"
cp "$dir/.review-arm/ledger.txt" "$STUB_DIR/ledger" 2>/dev/null
cp "$dir/.review-arm/listed-findings.md" "$STUB_DIR/listed" 2>/dev/null
case "$(sed -n "${n}p" "$STUB_DIR/plan")" in
  file) printf '## Security\n\n- **High** `%s/a.ts:1` `f` Bad.\n' "$dir" > "$out"
        [ -n "$cov" ] && printf '%s/a.ts reviewed ok\n' "$dir" > "$cov"
        echo '{"type":"step_finish","part":{"reason":"stop","tokens":{"output":90}}}' ;;
  text) echo '{"type":"text","part":{"text":"## Security\n\n- **High** `a.ts:1` `f` Bad."}}' ;;
  sqlite) echo '{"type":"error","error":{"name":"UnknownError","data":{"message":"Failed to execute statement"}}}' ;;
  *) echo '{"type":"step_finish","part":{"reason":"stop","tokens":{"output":0}}}' ;;
esac
'''

EMPTY_STOP = '{"type":"step_finish","part":{"reason":"stop","tokens":{"output":0}}}\n'
FINDING = "- **High** `a.ts:1` `f` Component finding.\n"
SWEEP = "- **Medium** `a.ts:9` `g` Sweep finding.\n"


def arm_script():
    m = re.search(r"<<'ARM'\n(.*?)\nARM\n", TEXT, re.S)
    assert m, "arm.sh heredoc not found in SKILL.md"
    return m.group(1) + "\n"


def bash_block(marker):
    hits = [b for b in re.findall(r"```bash\n(.*?)```", TEXT, re.S) if marker in b]
    assert len(hits) == 1, f"expected one bash block containing {marker!r}, found {len(hits)}"
    return hits[0]


def run_block(marker, state):
    home = state.parent / "home"
    (home / ".Trash").mkdir(parents=True, exist_ok=True)  # a safe-rm shim on PATH moves files to $HOME/.Trash
    return subprocess.run(["bash", "-c", bash_block(marker)],
                          env={"PATH": os.environ["PATH"], "HOME": str(home), "STATE_DIR": str(state)},
                          capture_output=True, text=True)


@pytest.fixture
def arm(tmp_path):
    state = tmp_path / "state"
    (state / "parts").mkdir(parents=True)
    target = tmp_path / "target"
    target.mkdir()
    export = tmp_path / "export"
    export.mkdir()
    (export / "a.ts").write_text("x\n")
    (state / "components").mkdir()
    (state / "components" / "c01.txt").write_text("a.ts\n")
    (state / "ledger.txt").write_text("a.ts\n")
    (state / "coverage").mkdir()
    (state / "gemini-security.md").write_text("## Security\n\n- **High** `a.ts:1` `f` Listed.\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("opencode", STUB_OPENCODE), ("sleep", "#!/bin/sh\nexit 0\n")):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(0o755)
    (state / "arm.sh").write_text(arm_script())
    stub = tmp_path / "stub"
    stub.mkdir()

    def run(plan, exported=True, comp="c01", export_dir=export):
        (stub / "plan").write_text("".join(f"{step}\n" for step in plan))
        env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(tmp_path), "STUB_DIR": str(stub),
               "TMPDIR": str(tmp_path / "tmp")}
        (tmp_path / "tmp").mkdir(exist_ok=True)
        if exported:
            env.update(STATE_DIR=str(state), TARGET_PATH=str(target), PROJECT_ROOT=str(target), EXPORT=str(export_dir))
        p = subprocess.run(["bash", str(state / "arm.sh"), "gemini", "google/x", "security", comp],
                           env=env, capture_output=True, text=True)
        calls = int((stub / "calls").read_text()) if (stub / "calls").exists() else 0
        return p, calls

    return types.SimpleNamespace(run=run, state=state, stub=stub, target=target, export=export, tmp=tmp_path / "tmp")


@pytest.fixture
def state(tmp_path):
    s = tmp_path / "state"
    (s / "parts").mkdir(parents=True)
    (s / "components").mkdir()
    (s / "components" / "c01.txt").write_text("a.ts\n")
    (s / "components" / "c02.txt").write_text("b.ts\n")
    return s


def test_arm_stops_the_batch_when_state_dir_is_not_exported(arm):
    p, calls = arm.run(["file"], exported=False)
    assert p.returncode == 255, "xargs stops launching arms only on exit 255"
    assert calls == 0
    assert "STATE_DIR" in p.stderr


def test_arm_that_writes_its_file_runs_once(arm):
    p, calls = arm.run(["file"])
    assert (p.returncode, calls) == (0, 1)


def test_arm_runs_opencode_isolated_under_the_generated_config(arm):
    arm.run(["file"])
    env = dict(line.split("=", 1) for line in (arm.stub / "env").read_text().splitlines())
    assert env["XDG_CONFIG_HOME"] == str(arm.state / "opencode-config")
    for flag in ("OPENCODE_PURE", "OPENCODE_DISABLE_EXTERNAL_SKILLS", "OPENCODE_DISABLE_CLAUDE_CODE",
                 "OPENCODE_DISABLE_PROJECT_CONFIG", "OPENCODE_DISABLE_AUTOUPDATE"):
        assert env.get(flag) == "1", flag
    assert "OPENCODE_CONFIG" not in env, "the operator's reviewer.json layer is gone"
    assert env["OPENCODE_DB"] == str(arm.state / "opencode-db" / "gemini-security-c01.db")
    args = (arm.stub / "args").read_text().splitlines()
    assert args[args.index("--agent") + 1] == "reviewer-security"


def test_arm_reviews_a_private_copy_of_the_export_and_deletes_it(arm):
    p, _ = arm.run(["file"])
    assert p.returncode == 0, p.stderr
    d = (arm.stub / "dir").read_text().strip()
    assert d not in (str(arm.target), str(arm.export))
    assert "a.ts" in (arm.stub / "listing").read_text().split()
    assert (arm.stub / "ledger").read_text() == "a.ts\n"
    assert not os.path.exists(d), "the copy must be deleted"
    assert not list(arm.tmp.iterdir()), "nothing left behind in TMPDIR"


def test_arm_brings_back_findings_and_coverage_with_repo_relative_paths(arm):
    arm.run(["file"])
    d = (arm.stub / "dir").read_text().strip()
    part = (arm.state / "parts" / "gemini-security-c01.md").read_text()
    cov = (arm.state / "coverage" / "gemini-security-c01.txt").read_text()
    assert "`a.ts:1`" in part and d not in part
    assert cov == "a.ts reviewed ok\n"


def test_sweep_copy_gets_the_ledger_and_the_areas_findings(arm):
    p, _ = arm.run(["file"], comp="sweep")
    assert p.returncode == 0, p.stderr
    assert (arm.stub / "ledger").read_text() == "a.ts\n"
    assert "Listed." in (arm.stub / "listed").read_text()
    assert (arm.state / "parts" / "gemini-security-sweep.md").exists()


def test_arm_stops_the_batch_when_the_export_is_missing(arm):
    p, calls = arm.run(["file"], export_dir=arm.tmp / "nope")
    assert (p.returncode, calls) == (255, 0)
    assert "EXPORT" in p.stderr


def test_extraction_strips_the_copy_prefix_from_findings_returned_as_text(state):
    text = "## Security\n\n- **High** `/tmp/review-deep-arm.Ab12Cd/repo/src/a.ts:4` `f` Bad."
    (state / "parts" / "raw-gemini-security-c01.ndjson").write_text(
        '{"type":"text","part":{"text":' + __import__("json").dumps(text) + "}}\n")
    run_block("grep -h -m1 '^## '", state)
    assert "`src/a.ts:4`" in (state / "parts" / "gemini-security-c01.md").read_text()


def test_arm_that_returns_findings_as_text_runs_once(arm):
    p, calls = arm.run(["text"])
    assert (p.returncode, calls) == (0, 1)


def test_arm_that_ends_without_output_is_retried(arm):
    p, calls = arm.run(["empty", "file"])
    assert (p.returncode, calls) == (0, 2)
    assert (arm.state / "parts" / "attempts" / "raw-gemini-security-c01.attempt1.ndjson").exists()
    assert not list((arm.state / "parts").glob("raw-*.attempt*.ndjson")), "a superseded attempt must stay out of Step 3's raw-*.ndjson glob"


def test_arm_still_retries_a_sqlite_write_failure(arm):
    p, calls = arm.run(["sqlite", "file"])
    assert (p.returncode, calls) == (0, 2)


def test_arm_that_never_writes_fails_after_three_attempts(arm):
    p, calls = arm.run(["empty", "empty", "empty"])
    assert calls == 3
    assert p.returncode == 1
    assert "gemini-security-c01" in p.stderr


def test_merge_keeps_sweep_findings_when_rerun(state):
    (state / "parts" / "gemini-security-c01.md").write_text("## Security\n\n" + FINDING)
    (state / "parts" / "gemini-security-sweep.md").write_text("## Security\n\n" + SWEEP)
    run_block("grep -h -m1 '^## '", state)
    run_block("grep -h -m1 '^## '", state)
    text = (state / "gemini-security.md").read_text()
    assert (text.count("Component finding"), text.count("Sweep finding")) == (1, 1)


def test_extraction_leaves_no_empty_part_for_an_arm_that_wrote_nothing(state):
    (state / "parts" / "gemini-security-c02.md").write_text("## Security\n\n" + FINDING)
    (state / "parts" / "raw-gemini-security-c01.ndjson").write_text(EMPTY_STOP)
    p = run_block("grep -h -m1 '^## '", state)
    assert not (state / "parts" / "gemini-security-c01.md").exists()
    assert "MISSING gemini security c01" in p.stdout


def test_step_2b_ignores_superseded_attempts(state):
    (state / "parts" / "attempts").mkdir()
    old = time.time() - 300
    for f in (state / "parts" / "raw-gemini-security-c01.ndjson", state / "parts" / "attempts" / "raw-gemini-data-c01.attempt1.ndjson"):
        f.write_text("")
        os.utime(f, (old, old))
    p = run_block("NO SESSION", state)
    assert p.stdout.splitlines() == ["NO SESSION gemini-security-c01"]


def test_counts_block_cites_a_critical_finding(state):
    (state / "gemini-security.md").write_text("## Security\n\n- **Critical** `a.ts:3` `f` Auth bypass.\n")
    p = run_block("unconf=$(grep -c 'line unconfirmed'", state)
    assert "security ok findings=1 cited=1 unconfirmed=0" in p.stdout, p.stdout


def test_arm_records_its_copy_as_its_allowed_root(arm):
    arm.run(["file"])
    d = (arm.stub / "dir").read_text().strip()
    assert (arm.state / "arms" / "gemini-security-c01.root").read_text().strip() == d
