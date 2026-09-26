"""partition.py: directory-aware component splitting, moved out of the review-deep SKILL.md heredoc."""
import partition


def test_25_or_fewer_files_give_one_component():
    paths = [f"a/{i}.ts" for i in range(1, 11)] + [f"b/{i}.ts" for i in range(1, 9)]
    comps = partition.split_paths(paths, size=25)
    assert len(comps) == 1
    assert sorted(comps[0]) == sorted(paths)


def test_directory_aware_split_recurses_only_when_a_directory_exceeds_size():
    paths = [f"a/{i}.ts" for i in range(1, 31)] + [f"b/{i}.ts" for i in range(1, 3)]
    comps = partition.split_paths(paths, size=25)
    assert [len(c) for c in comps] == [25, 7]
    assert sum(len(c) for c in comps) == len(paths)
    assert {p for c in comps for p in c} == set(paths)


def test_split_is_deterministic():
    paths = [f"pkg/{n}/{i}.ts" for n in ("a", "b", "c") for i in range(1, 12)]
    first = partition.split_paths(paths, size=25)
    for _ in range(5):
        assert partition.split_paths(paths, size=25) == first


def test_main_writes_components_and_prints_count(tmp_path, capsys):
    state = tmp_path / "state"
    state.mkdir()
    paths = [f"src/{i}.ts" for i in range(1, 6)]
    (state / "ledger.txt").write_text("\n".join(paths) + "\n")
    n = partition.main(str(state))
    assert n == 1
    written = sorted((state / "components").iterdir())
    assert [p.name for p in written] == ["c01.txt"]
    assert written[0].read_text().splitlines() == paths
    assert capsys.readouterr().out.strip() == "COMPONENTS=1"
