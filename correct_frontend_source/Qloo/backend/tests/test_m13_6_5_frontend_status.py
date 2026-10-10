"""Frontend contract checks: source mode must remain explicit."""
from types import SimpleNamespace

import pytest

from app.api.routes import _build_result


@pytest.mark.parametrize("status", ["measured", "fixture"])
def test_result_contract_forwards_source_mode(status):
    state = SimpleNamespace(
        data_status=status,
        programme=[],
        resolved_items=[],
        taste_tags=[],
        taste_call_id=None,
        ranked=[],
        rejected=[],
        calls_made=0,
        trace_rows=[],
        stop_reason="insufficient_evidence",
        stop_message="No adequate source evidence",
    )
    result = _build_result(state, city="London, UK")
    assert result["data_status"] == status
