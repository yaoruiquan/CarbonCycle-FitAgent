import pytest

from app.api import harness as harness_api


@pytest.mark.asyncio
async def test_get_harness_cases_returns_cases():
    result = await harness_api.get_harness_cases()

    assert "cases" in result
    assert len(result["cases"]) >= 5


@pytest.mark.asyncio
async def test_replay_harness_run_translates_not_found(monkeypatch):
    async def fake_replay_agent_run(**kwargs):
        return {"status": "not_found", "message": "Agent run not found"}

    monkeypatch.setattr(harness_api, "replay_agent_run", fake_replay_agent_run)

    with pytest.raises(harness_api.HTTPException) as exc:
        await harness_api.replay_harness_run("missing", db=None)

    assert exc.value.status_code == 404
