"""checks.check: label matches the run's ticket_label, including a snapshot commit_sentence."""
import json

import checks
from evidence import lines_at


def make_ticket(sentence, label):
    return {
        "id": "I1", "summary": "Timeout missing on the admin fetch",
        "description": "\n".join([
            "{panel:bgColor=#deebff}", "h3. Context",
            "* {{src/api.ts:3}} the fetch call has no timeout", "{panel}", "",
            "h3. Details", sentence, "",
            "{code:none}", "// src/api.ts:3-3",
            '    const res = await fetch("/api/admin/users");', "{code}",
        ]) + "\n",
        "locations": ["src/api.ts:3"], "labels": [label, "correctness"], "priority": "High", "type": "Bug",
    }


def test_label_matching_the_run_passes(repo):
    run = json.loads((repo["run"] / "run.json").read_text())
    ticket = make_ticket(run["commit_sentence"], "review-full")
    source = lambda p: lines_at(str(repo["repo"]), run["commit"], p)  # noqa: E731
    assert checks.check(ticket, source, "review-full") == []


def test_label_mismatch_is_flagged(repo):
    run = json.loads((repo["run"] / "run.json").read_text())
    ticket = make_ticket(run["commit_sentence"], "review-full")
    source = lambda p: lines_at(str(repo["repo"]), run["commit"], p)  # noqa: E731
    problems = checks.check(ticket, source, "review-diff")
    assert any("labels" in p for p in problems)


def test_snapshot_commit_sentence_passes_the_wiki_checks(repo):
    run = json.loads((repo["run"] / "run.json").read_text())
    sentence = f"Paths and line numbers refer to commit {{{{{run['commit']}}}}} on main, a snapshot of HEAD {{{{{run['commit']}}}}}."
    ticket = make_ticket(sentence, "review-diff")
    source = lambda p: lines_at(str(repo["repo"]), run["commit"], p)  # noqa: E731
    assert checks.check(ticket, source, "review-diff") == []


def test_monospace_code_and_panel_words_are_not_counted_as_markup(repo):
    run = json.loads((repo["run"] / "run.json").read_text())
    ticket = make_ticket(run["commit_sentence"], "review-deep")
    ticket["description"] = ticket["description"].replace(
        "the fetch call has no timeout", "the {{code}} field and the {{code}} key and the {{panel}} name have no timeout")
    source = lambda p: lines_at(str(repo["repo"]), run["commit"], p)  # noqa: E731
    assert checks.check(ticket, source, "review-deep") == []
