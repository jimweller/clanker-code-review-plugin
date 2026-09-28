import os
import sys

import pytest

EVALS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, EVALS_DIR)
import live_eval_go  # noqa: E402


@pytest.fixture
def state(tmp_path):
    """A repo root with two small Go files and the empty parts/coverage/opencode-db
    directories a review-deep STATE_DIR carries before any arm writes to them."""
    repo = tmp_path / "goeval"
    (repo / "warehouse").mkdir(parents=True)
    (repo / "shipping").mkdir(parents=True)
    (repo / "warehouse" / "api.go").write_text(
        "package warehouse\n\nfunc Authenticate() bool {\n\tif true {\n\t\treturn true\n\t}\n\treturn false\n}\n")
    (repo / "shipping" / "rate.go").write_text(
        "package shipping\n\nfunc ShippingCost(weight float64) float64 {\n\treturn weight * 0.004\n}\n")
    state_dir = repo / ".llmtmp" / "review-deep"
    for d in ("parts", "coverage", "opencode-db"):
        (state_dir / d).mkdir(parents=True)
    return {"repo": repo, "state": state_dir}
