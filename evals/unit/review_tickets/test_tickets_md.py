"""assemble.tickets_md: tickets.md, the tickets as plain markdown with a perspective by severity table."""
import json

import apply as apply_stage
import assemble
from test_stages import editor, unit


def build(repo, units, decisions=None):
    run = json.loads((repo["run"] / "run.json").read_text())
    edits = {u["id"]: apply_stage.edit_record(u, {"editor": editor(severity=u["severity"])}, run) for u in units}
    md = {}
    manifest = assemble.assemble(run, units, edits, {}, {}, decisions or {}, str(repo["run"] / "final"), markdown=md)
    tickets = [json.loads((repo["run"] / "final" / f"{m['id']}.json").read_text()) for m in manifest if "summary_source" in m]
    return assemble.tickets_md(run, tickets, md)


def test_table_has_perspectives_as_rows_and_severities_as_columns(repo):
    sec = dict(unit("I2", severity="High"), areas=["security", "bug"])
    text = build(repo, [unit("I1", severity="Medium"), sec])
    lines = text.splitlines()
    header = next(i for i, l in enumerate(lines) if l.startswith("| Perspective"))
    assert lines[header] == "| Perspective | Critical | High | Medium | Low | Total |"
    rows = {l.split("|")[1].strip(): [c.strip() for c in l.split("|")[2:7]] for l in lines[header + 2:] if l.startswith("|")}
    assert rows["correctness"] == ["0", "1", "1", "0", "2"]
    assert rows["security"] == ["0", "1", "0", "0", "1"]
    assert rows["Distinct tickets"] == ["0", "1", "1", "0", "2"]
    assert text.index("| Perspective") < text.index("## ")


def test_sections_are_plain_markdown_with_exact_code(repo):
    text = build(repo, [unit("I1")])
    section = text[text.index("## I1"):]
    assert "{{" not in section and "{code" not in section and "{panel" not in section
    assert "- `src/api.ts:3` `fetchUserList` It hangs." in section
    assert '    const res = await fetch("/api/admin/users");' in section
    assert "```" in section and f"`{repo['sha']}`" in section
    assert "Priority: High" in section and "Labels: correctness" in section


def test_highest_priority_first_and_deferred_marked(repo):
    text = build(repo, [unit("I1", severity="Low"), unit("I2", severity="High")], decisions={"defer_priorities": ["Low"]})
    assert text.index("## I2") < text.index("## I1")
    assert "Deferred" in text[text.index("## I1"):]
    assert "Deferred" not in text[text.index("## I2"):text.index("## I1")]
