"""Shared synthetic-state helpers for the fixture_go unit tests. Named away from
common.py and test_stages.py, both already used by sibling evals/unit/* directories,
since pytest's rootless import collects same-named modules across directories as one."""
import sqlite3


def make_db(path, blobs):
    """Build a minimal opencode-db SQLite file: just enough of the real `part` table
    schema (id, message_id, session_id, time_created, time_updated, data) for
    live_eval_go's json_extract queries against the data column to work."""
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE part (id text PRIMARY KEY, message_id text, session_id text, "
                "time_created integer, time_updated integer, data text)")
    for i, blob in enumerate(blobs):
        con.execute("INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
                     "VALUES (?, 'm', 's', 0, 0, ?)", (f"p{i}", blob))
    con.commit()
    con.close()
