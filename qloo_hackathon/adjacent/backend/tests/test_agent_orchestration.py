"""The agent control system: states, transitions, budget, and the two failures that
must never be confused.

What is asserted here is the *control flow*, with the Milestone-1 domain logic
stubbed where the test is about something else. The point of the state machine is
auditability and refusal, so most of these tests check the trace rather than the
result: which state followed which, what it was allowed to do, and what it said
when it stopped.

The stubs implement `agent.tools.PipelineRuntime`, which is exactly how a live
runtime will plug in later — so these tests double as the interface contract.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest
from app.agent import (
    AgentOrchestrator,
    Budget,
    BudgetExhausted,
    Phase,
    RunStatus,
    StopReason,
    build_evidence_report,
)
from app.agent.state import ACT_PHASES, AdjacentState, ProgrammeItem
from app.agent.stop import StopDecision, decide_stop
from app.agent.tools import (
    ExpandResult,
    RankResult,
    ResolveResult,
    TasteResult,
    default_tools,
)
from app.domain.cohorts import CandidateCohort
from app.evidence import (
    MSG_NO_ADJACENT_AUDIENCE,
    MSG_NO_TAGS,
    MSG_NOT_ENOUGH_RESOLVED,
    evaluate_cohort,
    evaluate_programme_resolution,
    evaluate_tags,
)
from app.qloo.errors import UpstreamError
from app.qloo.models import ScoredEntity, ScoredTag
from app.runner import _Budget, _resolve_programme
from app.runner import run_fixture as run_strong_fixture

STRONG = "portland_strong"
SPARSE = "insufficient_evidence"


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FixtureStub:
    """Minimal `Fixture` stand-in: the resolve step only reads `.programme`."""

    def __init__(self, programme: list[dict]) -> None:
        self.programme = programme
        self.name = "stub"


class StubRuntime:
    """A `PipelineRuntime` whose every behaviour can be dialled from a test.

    Defaults describe a healthy programme: 3 resolved titles, a strong taste
    profile, candidates in one domain, and one cohort that clears the gate.
    """

    name = "stub-runtime"
    data_status = "fixture"

    def __init__(
        self,
        *,
        resolve: ResolveResult | None = None,
        taste: TasteResult | None = None,
        expand: ExpandResult | None = None,
        rank: RankResult | None = None,
        raise_on: str | None = None,
        error: BaseException | None = None,
        calls_per_action: int = 1,
    ) -> None:
        self.resolve_result = resolve
        self.taste_result = taste
        self.expand_result = expand
        self.rank_result = rank
        self.raise_on = raise_on
        self.error = error or UpstreamError("Qloo returned 503", endpoint="/v2/insights", status=503)
        self.calls_per_action = calls_per_action
        self.actions: list[str] = []

    # -- helpers -----------------------------------------------------------
    def _maybe_fail(self, action: str) -> None:
        self.actions.append(action)
        if self.raise_on == action:
            raise self.error

    @staticmethod
    def _score(state: AdjacentState, ids: list[str], affinity: float, popularity: float) -> None:
        state.candidates_by_domain.setdefault("urn:entity:artist", [])
        state.candidates_by_domain["urn:entity:artist"] = [
            ScoredEntity(
                entity_id=i, name=i, type="urn:entity:artist", affinity=affinity, popularity=popularity
            )
            for i in ids
        ]

    # -- the four operations ----------------------------------------------
    async def resolve_programme(self, state: AdjacentState, budget: Budget) -> ResolveResult:
        self._maybe_fail("resolve")
        budget.ensure(self.calls_per_action)
        budget.take(self.calls_per_action)
        for index, item in enumerate(state.programme, start=1):
            item.resolved_entity_id = f"id-{index}"
            item.resolved_name = item.title
            item.entity_type = "urn:entity:movie"
        state.resolution_call_ids.append("stub-c001")
        state.resolution_verdict = evaluate_programme_resolution(len(state.resolved_items))
        if self.resolve_result is not None:
            return self.resolve_result
        return ResolveResult(
            tool="resolve_programme",
            action="resolve",
            detail=f"resolved {len(state.resolved_items)}",
            call_ids=("stub-c001",),
            resolved=len(state.resolved_items),
            verdict=state.resolution_verdict,
        )

    async def get_taste_profile(self, state: AdjacentState, budget: Budget) -> TasteResult:
        self._maybe_fail("analyse")
        budget.ensure(self.calls_per_action)
        budget.take(self.calls_per_action)
        state.taste_tags = [ScoredTag(tag_id="urn:tag:x", name="X", affinity=0.8, popularity=0.2)]
        state.taste_call_id = "stub-c002"
        state.taste_verdict = evaluate_tags(state.taste_tags)
        if self.taste_result is not None:
            return self.taste_result
        return TasteResult(
            tool="get_taste_profile",
            action="analyse",
            detail="1 tag",
            call_ids=("stub-c002",),
            call_id="stub-c002",
            tag_count=1,
            tags_above_high=1,
            verdict=state.taste_verdict,
        )

    async def expand_candidates(self, state: AdjacentState, budget: Budget) -> ExpandResult:
        self._maybe_fail("expand")
        budget.ensure(self.calls_per_action)
        budget.take(self.calls_per_action)
        self._score(state, ["a1", "a2", "a3"], 0.7, 0.3)
        state.expansion_call_ids["urn:entity:artist"] = "stub-c003"
        if self.expand_result is not None:
            return self.expand_result
        return ExpandResult(
            tool="expand_candidates",
            action="expand",
            detail="3 candidates in 1 domain",
            call_ids=("stub-c003",),
            candidates=3,
            domains=("urn:entity:artist",),
            per_domain={"urn:entity:artist": 3},
        )

    async def rank_cohorts(self, state: AdjacentState, budget: Budget) -> RankResult:
        self._maybe_fail("rank")
        budget.ensure(self.calls_per_action)
        budget.take(self.calls_per_action)
        if not state.cohorts:
            state.cohorts = [
                CandidateCohort(
                    cohort_id="urn:entity:artist:subtype:musician:1",
                    domain="urn:entity:artist",
                    kind="subtype_group",
                    member_ids=["a1", "a2"],
                    construction_reason="stub",
                )
            ]

        class _RankerRuntime:
            recorder = None

        # Use the real ranker against a client-like shim so the single-operation
        # discipline is exercised, not faked.
        state.ranking = await _stub_ranking(state)
        state.ranked = list(state.ranking.ranked)
        state.rejected = list(state.ranking.rejected)
        if self.rank_result is not None:
            return self.rank_result
        return RankResult(
            tool="rank_cohorts",
            action="rank",
            detail="ranked",
            call_ids=tuple(state.ranking.scoring_call_ids),
            operation_call_id=state.ranking.operation_call_id,
            contexts=len(state.ranking.contexts),
            cohorts_ranked=len(state.ranked),
            cohorts_rejected=len(state.rejected),
        )


async def _stub_ranking(state: AdjacentState):
    """Rank the state's cohorts with a client that returns fixed scored entities.

    Uses the REAL `CohortRanker`, so these tests inherit the single-normalisation
    guarantees instead of re-implementing them. Its rows go into the state's own
    ledger recorder, exactly as the fixture runtime's do.
    """
    from app.domain.ledger import ProvenanceLedger
    from app.domain.scoring import CohortRanker
    from app.qloo.mock import MockQlooClient
    from app.qloo.models import EntityAffinityResponse

    if state.ledger is None:
        state.ledger = ProvenanceLedger(
            recorder=MockQlooClient(fixture=STRONG).recorder, data_status="fixture"
        )
    affinities = {
        entity.entity_id: entity for entities in state.candidates_by_domain.values() for entity in entities
    }

    class _Client:
        def __init__(self, recorder) -> None:
            self.recorder = recorder

        async def insights(self, **kwargs):
            domain = str(kwargs["filter_type"])
            requested = list(kwargs.get("filter_results_entities") or [])
            results = [affinities[i] for i in requested if i in affinities]
            return EntityAffinityResponse(
                call_id=f"stub-score-{domain}",
                source="mock",
                data_status="fixture",
                endpoint="/v2/insights",
                results=results,
            )

    client = _Client(state.ledger.recorder)
    return await CohortRanker(client, programme_ids=["id-1"]).build_and_rank_cohorts(state.cohorts)


def _state(**overrides) -> AdjacentState:
    programme = overrides.pop(
        "programme",
        [
            ProgrammeItem(title=f"Film {i}", year=2024, imdb_id=f"tt{i}", declared_entity_id=f"id-{i}")
            for i in range(1, 4)
        ],
    )
    return AdjacentState(
        run_id="test-run",
        fixture_name="stub",
        scenario="stub",
        data_status="fixture",
        programme=programme,
        budget=overrides.pop("budget", Budget()),
        **overrides,
    )


def _run(state: AdjacentState, runtime: StubRuntime) -> AdjacentState:
    return asyncio.run(AgentOrchestrator(runtime).run(state))


def _phases(state: AdjacentState) -> list[str]:
    return [transition.to_state for transition in state.transitions]


# ---------------------------------------------------------------------------
# 1–3 · initial state, happy path, completion
# ---------------------------------------------------------------------------


def test_initial_state_is_init_and_nothing_has_run():
    state = _state()
    assert state.phase is Phase.INIT
    assert state.status is RunStatus.RUNNING
    assert state.transitions == []
    assert state.stop is None
    assert state.completed == set()
    assert state.budget.steps_used == 0
    assert state.budget.qloo_calls_used == 0
    assert state.budget.max_steps == 14
    assert state.budget.max_qloo_calls == 24


def test_happy_path_visits_every_state_in_order_and_never_jumps():
    state = _run(_state(), StubRuntime())
    visited = _phases(state)

    # INIT is entered first and PLAN is reached before any acting state.
    assert visited[0] == Phase.PLAN.value
    assert state.transitions[0].from_state == Phase.INIT.value

    for phase in ACT_PHASES:
        assert phase.value in visited, f"{phase.value} was never entered"
    assert visited.count(Phase.PLAN.value) >= len(ACT_PHASES)
    assert visited[-1] == Phase.STOP.value

    # No acting state is ever entered twice, and each one is followed by EVALUATE.
    for index, phase in enumerate(visited):
        if phase in {p.value for p in ACT_PHASES}:
            assert visited[index + 1] == Phase.EVALUATE.value
    for phase in {p.value for p in ACT_PHASES}:
        assert visited.count(phase) == 1, f"{phase} ran more than once"

    # The plan order is the plan order.
    order = [visited.index(p.value) for p in ACT_PHASES]
    assert order == sorted(order)


def test_happy_path_completes_with_ranked_cohorts():
    state = _run(_state(), StubRuntime())
    assert state.status is RunStatus.FINISHED
    assert state.stop is not None
    assert state.stop.reason is StopReason.COMPLETE
    assert state.stop.ok
    assert state.ranked
    assert state.phase is Phase.STOP
    assert state.evidence_report is not None
    assert state.evidence_report.ready


# ---------------------------------------------------------------------------
# 4 · insufficiency
# ---------------------------------------------------------------------------


def test_insufficiency_stop_when_nothing_resolves():
    """One lookup succeeds but returns nothing usable → thin evidence, not a fault."""
    runtime = StubRuntime()
    state = _state()

    async def _resolve_nothing(state: AdjacentState, budget: Budget) -> ResolveResult:
        budget.take(1)
        state.resolution_call_ids.append("stub-c001")
        state.resolution_verdict = evaluate_programme_resolution(0)
        verdict = state.resolution_verdict
        return ResolveResult(
            tool="resolve_programme",
            action="resolve",
            detail="resolved 0",
            call_ids=("stub-c001",),
            resolved=0,
            unresolved=len(state.programme),
            verdict=verdict,
        )

    runtime.resolve_programme = _resolve_nothing  # type: ignore[method-assign]
    state = asyncio.run(AgentOrchestrator(runtime).run(state))

    assert state.stop is not None
    assert state.stop.reason is StopReason.INSUFFICIENCY
    # Nothing resolved, so the resolution gate is the *cause* and names it in the
    # more specific words; the unsatisfied cohort gate is kept as a finding.
    assert state.stop.message == MSG_NOT_ENOUGH_RESOLVED.format(resolved=0)
    assert state.stop.detail_code == "insufficient_resolved_titles"
    assert "insufficient_cohorts" in {finding.code for finding in state.findings}
    assert state.ranked == []
    # No tool that needs a resolved id was reached: the agent's own record of what
    # ran is the authority here, not the stub's call log.
    assert state.completed == {"resolve"}
    assert state.taste_call_id is None
    assert state.candidates_by_domain == {}
    assert state.ranking is None
    assert state.evidence_report is not None
    assert state.evidence_report.progress_possible is False


def test_insufficiency_stop_when_no_cohort_clears_the_gate():
    runtime = StubRuntime()

    async def _weak_rank(state: AdjacentState, budget: Budget) -> RankResult:
        budget.take(1)
        state.cohorts = [
            CandidateCohort(
                cohort_id="urn:entity:artist:domain_group:1",
                domain="urn:entity:artist",
                kind="domain_group",
                member_ids=["a1", "a2"],
                construction_reason="stub",
            )
        ]
        state.candidates_by_domain = {
            "urn:entity:artist": [
                ScoredEntity(entity_id="a1", type="urn:entity:artist", affinity=0.41),
                ScoredEntity(entity_id="a2", type="urn:entity:artist", affinity=0.44),
            ]
        }
        state.ranking = await _stub_ranking(state)
        state.ranked = list(state.ranking.ranked)
        state.rejected = list(state.ranking.rejected)
        return RankResult(
            tool="rank_cohorts",
            action="rank",
            detail="0 cohorts cleared the gate",
            operation_call_id=state.ranking.operation_call_id,
            contexts=len(state.ranking.contexts),
            cohorts_ranked=0,
            cohorts_rejected=len(state.rejected),
        )

    runtime.rank_cohorts = _weak_rank  # type: ignore[method-assign]
    state = asyncio.run(AgentOrchestrator(runtime).run(_state()))

    assert state.stop is not None
    assert state.stop.reason is StopReason.INSUFFICIENCY
    assert state.stop.message == MSG_NO_ADJACENT_AUDIENCE
    assert state.ranked == []
    assert all(cohort.rejected for cohort in state.cohorts)


def test_the_refusal_sentence_is_the_product_sentence_everywhere():
    """One string, one module: the agent imports it rather than restating it."""
    from app import evidence
    from app.agent import stop

    assert stop.MSG_NO_ADJACENT_AUDIENCE == evidence.MSG_NO_ADJACENT_AUDIENCE
    assert MSG_NO_ADJACENT_AUDIENCE.endswith("name an adjacent audience for this programme.")
    assert MSG_NO_TAGS.startswith("Qloo found no tags")


# ---------------------------------------------------------------------------
# 5 · invalid input is not insufficient evidence
# ---------------------------------------------------------------------------


def test_empty_programme_stops_as_invalid_input():
    state = _run(_state(programme=[]), StubRuntime())
    assert state.stop is not None
    assert state.stop.reason is StopReason.INVALID_INPUT
    assert state.stop.detail_code == "empty_programme"
    assert state.stop.reason is not StopReason.INSUFFICIENCY
    assert state.budget.steps_used == 1  # INIT → PLAN → STOP, one step to stop
    assert state.phase is Phase.STOP


def test_programme_without_identifiers_stops_as_invalid_input():
    programme = [ProgrammeItem(title="Untitled Reel", year=None, imdb_id=None, declared_entity_id=None)]
    state = _run(_state(programme=programme), StubRuntime())
    assert state.stop is not None
    assert state.stop.reason is StopReason.INVALID_INPUT
    assert state.stop.detail_code == "no_identifiers"
    # Nothing was called: invalid input is caught before any tool runs.
    assert state.budget.qloo_calls_used == 0
    assert not state.trace_rows


def test_invalid_input_is_distinguishable_from_thin_evidence():
    """Same fixture family, two different verdicts, two different words."""
    thin = StubRuntime()

    async def _resolve_nothing(state, budget):
        budget.take(1)
        state.resolution_call_ids.append("stub-c001")
        state.resolution_verdict = evaluate_programme_resolution(0)
        return ResolveResult(
            tool="resolve_programme",
            action="resolve",
            detail="resolved 0",
            resolved=0,
            verdict=state.resolution_verdict,
        )

    thin.resolve_programme = _resolve_nothing  # type: ignore[method-assign]
    thin_state = asyncio.run(AgentOrchestrator(thin).run(_state()))
    invalid_state = _run(_state(programme=[]), StubRuntime())

    assert thin_state.stop.reason is StopReason.INSUFFICIENCY
    assert invalid_state.stop.reason is StopReason.INVALID_INPUT
    assert thin_state.stop.message != invalid_state.stop.message


# ---------------------------------------------------------------------------
# 6 · budget exhaustion
# ---------------------------------------------------------------------------


def test_step_budget_exhaustion_stops_with_budget_exhausted():
    state = _run(_state(budget=Budget(max_steps=3)), StubRuntime())
    assert state.stop is not None
    assert state.stop.reason is StopReason.BUDGET_EXHAUSTED
    assert state.stop.detail_code == "step_limit"
    assert state.budget.steps_used >= 3
    # The run stopped rather than producing a half-answer.
    assert not state.ranked
    assert state.phase is Phase.STOP


def test_call_budget_exhaustion_is_not_reported_as_insufficiency():
    runtime = StubRuntime()
    state = _run(_state(budget=Budget(max_qloo_calls=2)), runtime)
    assert state.stop is not None
    assert state.stop.reason is StopReason.BUDGET_EXHAUSTED
    assert state.stop.detail_code == "call_limit"
    assert state.stop.reason is not StopReason.INSUFFICIENCY
    assert state.budget.qloo_calls_used <= 2 + runtime.calls_per_action  # never over by more than one action
    assert "budget_exhausted" in {finding.code for finding in state.findings}


def test_budget_exhausted_never_starts_an_action_it_cannot_finish():
    """The guard fires before the tool runs, so no partial operation is recorded."""
    runtime = StubRuntime(calls_per_action=5)
    state = _run(_state(budget=Budget(max_qloo_calls=4)), runtime)
    assert state.stop is not None
    assert state.stop.reason is StopReason.BUDGET_EXHAUSTED
    assert state.stop.detail_code == "call_limit"
    assert runtime.actions == ["resolve"], "the tool that could not be afforded must not start"
    # The guard fired before any call was made or any artefact written.
    assert state.budget.qloo_calls_used == 0
    assert state.resolution_call_ids == []
    assert not state.resolved_items


def test_wall_clock_ceiling_stops_as_timeout():
    ticks = iter([0.0, 0.0, 0.0, 0.0, 200.0, 200.0, 200.0])
    budget = Budget(max_wall_clock_s=90.0, clock=lambda: next(ticks, 200.0))
    state = _run(_state(budget=budget), StubRuntime())
    assert state.stop is not None
    assert state.stop.reason is StopReason.TIMEOUT
    assert state.stop.detail_code == "wall_clock"
    assert state.stop.reason is not StopReason.BUDGET_EXHAUSTED


def test_budget_refuses_directly_and_reports_what_is_left():
    budget = Budget(max_qloo_calls=2)
    budget.take(2)
    with pytest.raises(BudgetExhausted) as excinfo:
        budget.ensure(1)
    assert excinfo.value.code == "budget_exhausted"
    assert excinfo.value.detail_code == "call_limit"
    snapshot = budget.snapshot()
    assert snapshot["remaining_calls"] == 0
    assert snapshot["exhausted"] is True
    # A refusal must not consume anything.
    assert budget.qloo_calls_used == 2


# ---------------------------------------------------------------------------
# 7 · tool failures are errors, not thin data
# ---------------------------------------------------------------------------


def test_tool_failure_stops_as_error_not_insufficiency():
    runtime = StubRuntime(raise_on="expand")
    state = _run(_state(), runtime)
    assert state.stop is not None
    assert state.stop.reason is StopReason.ERROR
    assert state.stop.reason is not StopReason.INSUFFICIENCY
    assert state.stop.detail_code == "qloo_error"
    assert state.phase is Phase.ERROR
    assert state.status is RunStatus.FINISHED
    assert "tool_failure" in {finding.code for finding in state.findings}
    assert state.stop.stats["error"]["status"] == 503


def test_a_failure_in_the_first_action_does_not_run_later_tools():
    runtime = StubRuntime(raise_on="resolve")
    state = _run(_state(), runtime)
    assert runtime.actions == ["resolve"]
    assert state.stop.reason is StopReason.ERROR


def test_every_expansion_call_failing_is_an_error_not_thin_evidence():
    runtime = StubRuntime(
        expand=ExpandResult(
            tool="expand_candidates",
            action="expand",
            detail="0 candidates; 1 domain failed",
            candidates=0,
            domains=("urn:entity:artist",),
            failed_domains=("urn:entity:artist",),
        )
    )

    async def _expand_all_fail(state: AdjacentState, budget: Budget) -> ExpandResult:
        budget.take(1)
        return runtime.expand_result

    runtime.expand_candidates = _expand_all_fail  # type: ignore[method-assign]
    state = asyncio.run(AgentOrchestrator(runtime).run(_state()))

    assert state.stop is not None
    assert state.stop.reason is StopReason.ERROR
    assert state.stop.reason is not StopReason.INSUFFICIENCY


def test_partial_expansion_failure_is_tolerated_and_still_can_complete():
    """Three domains fail, one returns: the run continues — a degraded run is not a fault."""
    runtime = StubRuntime(
        expand=ExpandResult(
            tool="expand_candidates",
            action="expand",
            detail="3 candidates in 1 of 4 domains",
            candidates=3,
            domains=("urn:entity:artist", "urn:entity:book", "urn:entity:brand", "urn:entity:movie"),
            failed_domains=("urn:entity:book", "urn:entity:brand", "urn:entity:movie"),
            per_domain={"urn:entity:artist": 3},
        )
    )
    state = _run(_state(), runtime)
    assert state.stop.reason is StopReason.COMPLETE


# ---------------------------------------------------------------------------
# 8–9 · the trace, and the terminal state
# ---------------------------------------------------------------------------


def test_every_transition_is_traced_with_the_required_fields():
    state = _run(_state(), StubRuntime())
    assert state.transitions, "a run with no transitions is a run with no control flow"

    orders = [t.order for t in state.transitions]
    assert orders == list(range(1, len(orders) + 1)), "transition order must be dense and ordered"

    for transition in state.transitions:
        assert transition.from_state in {p.value for p in Phase}
        assert transition.to_state in {p.value for p in Phase}
        assert transition.action, "every transition names the action"
        assert transition.reason, "every transition carries a reason"
        assert transition.at, "every transition is timestamped"
        assert transition.from_state != transition.to_state or transition.action == "stop"

    # The orchestration trace and the Qloo trace are different records and are not mixed.
    assert state.transitions[0].action == "plan"
    qloo_tools = {row["tool"] for row in state.trace_rows}
    assert "plan" not in qloo_tools
    assert "assess_evidence" not in qloo_tools


def test_no_state_can_execute_after_stop():
    state = _state()
    runtime = StubRuntime()
    orchestrator = AgentOrchestrator(runtime)
    state = asyncio.run(orchestrator.run(state))

    assert state.status is RunStatus.FINISHED
    transitions_after_stop = len(state.transitions)

    # Re-running is a no-op, not a second pass.
    state = asyncio.run(orchestrator.run(state))
    assert len(state.transitions) == transitions_after_stop
    assert state.budget.steps_used == transitions_after_stop or state.budget.steps_used > 0

    # And asking for an action directly is refused.
    with pytest.raises(Exception) as excinfo:
        asyncio.run(orchestrator.act(default_tools(runtime)["resolve_programme"], state))
    assert "stopped" in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        asyncio.run(orchestrator.evaluate(state, ResolveResult(tool="x", action="x", detail="x")))
    assert "stopped" in str(excinfo.value)


def test_stop_is_the_last_transition_and_phase():
    state = _run(_state(), StubRuntime())
    assert state.transitions[-1].to_state == Phase.STOP.value
    assert state.transitions[-1].action == "stop"
    assert state.phase is Phase.STOP


def test_error_runs_end_in_the_error_phase_but_still_terminate():
    state = _run(_state(), StubRuntime(raise_on="analyse"))
    assert state.phase is Phase.ERROR
    assert state.transitions[-1].to_state == Phase.ERROR.value
    assert state.status is RunStatus.FINISHED
    assert state.stop.reason is StopReason.ERROR


# ---------------------------------------------------------------------------
# 10–11 · the orchestrator reuses the real machinery
# ---------------------------------------------------------------------------


def test_orchestrator_uses_the_existing_cohort_ranker_and_one_operation():
    state = _run(_state(), StubRuntime())
    from app.domain.scoring import CohortRanker

    assert state.ranking is not None
    # The ranking came from the real ranker: one logical operation row, one call
    # per context, and every cohort scored inside its own context.
    operation_rows = state.trace_by_tool("build_and_rank_cohorts")
    assert len(operation_rows) == 1
    assert isinstance(CohortRanker, type)
    assert len(state.ranking.scoring_call_ids) == len(state.ranking.contexts)
    for cohort in state.cohorts:
        assert cohort.score.call_id in state.ranking.scoring_call_ids


def test_a_full_fixture_run_through_the_agent_keeps_milestone_1_results():
    state = run_strong_fixture(STRONG)
    assert state.stop.reason is StopReason.COMPLETE
    assert len(state.ranked) == 6
    assert len(state.rejected) == 2
    assert {c.domain for c in state.ranked} == {
        "urn:entity:artist",
        "urn:entity:book",
        "urn:entity:movie",
        "urn:entity:tv_show",
    }
    # The agent drove it: the acting phases appear in the trace exactly once each.
    visited = _phases(state)
    for phase in ACT_PHASES:
        assert visited.count(phase.value) == 1


def test_sparse_fixture_run_through_the_agent_still_refuses():
    from app.runner import run_fixture

    state = run_fixture(SPARSE)
    assert state.stop.reason is StopReason.INSUFFICIENCY
    assert state.stop.message == MSG_NO_ADJACENT_AUDIENCE
    assert state.ranked == []


# ---------------------------------------------------------------------------
# the report the EVALUATE phase reads
# ---------------------------------------------------------------------------


def test_evidence_report_is_pure_and_reads_the_three_milestone_1_gates():
    state = _state()
    report = build_evidence_report(state)
    assert report.gates == {
        "resolution": False,
        "taste_profile": False,
        "candidate_cohorts": False,
    }
    assert report.ready is False
    assert report.summary()

    state.resolution_verdict = evaluate_programme_resolution(4)
    state.taste_verdict = evaluate_tags([ScoredTag(tag_id="t", affinity=0.7)])
    report = build_evidence_report(state)
    assert report.gates["resolution"] is True
    assert report.gates["taste_profile"] is True
    assert report.gates["candidate_cohorts"] is False
    assert report.progress_possible is False  # nothing resolved in this synthetic state
    assert report.failing_verdict is not None


def test_decide_stop_follows_the_documented_gate_precedence():
    """Cohorts first, then resolution, then taste — Milestone 1's rule, kept."""
    state = _state()
    state.resolution_verdict = evaluate_programme_resolution(0)
    decision = decide_stop(state, build_evidence_report(state))
    assert isinstance(decision, StopDecision)
    assert decision.reason is StopReason.INSUFFICIENCY
    assert decision.refuses_recommendation
    # No cohorts exist, so the cohort gate is the one closest to the decision.
    assert decision.message == MSG_NO_ADJACENT_AUDIENCE
    assert decision.detail_code == "insufficient_cohorts"

    # When the cohort gate is satisfied but resolution is not, resolution decides.
    state.ranked = [
        CandidateCohort(
            cohort_id="c",
            domain="urn:entity:artist",
            kind="subtype_group",
            member_ids=["a1", "a2"],
            construction_reason="stub",
        )
    ]
    report = replace(
        build_evidence_report(state),
        cohort_verdict=evaluate_cohort(
            [
                ScoredEntity(entity_id="a1", affinity=0.9),
                ScoredEntity(entity_id="a2", affinity=0.7),
            ]
        ),
    )
    assert report.cohort_verdict.sufficient
    decision = decide_stop(state, report)
    assert decision.message == MSG_NOT_ENOUGH_RESOLVED.format(resolved=0)
    assert decision.detail_code == "insufficient_resolved_titles"


def test_domain_helper_names_are_still_available_for_milestone_1_call_sites():
    """`_Budget` and `_resolve_programme` keep working for direct callers."""
    from app.agent.budget import Budget as AgentBudget

    assert _Budget is AgentBudget
    run = AdjacentState(run_id="t", fixture_name="t", scenario="t", data_status="fixture")
    fixture = _FixtureStub([{"title": "A", "year": 2024, "imdb_id": "tt1", "entity_id": "id-1"}])

    class _Client:
        def __init__(self) -> None:
            from app.qloo.mock import MockQlooClient
            from app.qloo.models import EntitiesResponse, ScoredEntity

            self.recorder = MockQlooClient(fixture=STRONG).recorder
            self._response = EntitiesResponse(
                call_id="c1",
                source="mock",
                data_status="fixture",
                endpoint="/entities",
                results=[ScoredEntity(entity_id="id-1", name="A", type="urn:entity:movie")],
            )

        async def entities(self, **kwargs):
            return self._response

    asyncio.run(_resolve_programme(_Client(), fixture, run, _Budget()))
    assert run.resolved_ids == ["id-1"]
    assert len(run.programme) == 1


# ---------------------------------------------------------------------------
# the CLI and the three records a run leaves behind
# ---------------------------------------------------------------------------


def test_cli_show_agent_trace_prints_only_the_orchestration(capsys):
    from app.cli import main

    assert main(["run", "--fixture", "portland_strong", "--mock", "--show-agent-trace"]) == 0
    out = capsys.readouterr().out
    assert "ORCHESTRATION" in out
    assert "INIT" in out and "PLAN" in out and "STOP" in out
    # It is the agent's view only: no Qloo trace, no cohort tables.
    assert "EVIDENCE (Qloo trace)" not in out
    assert "RANKED COHORTS" not in out


def test_a_run_leaves_three_separate_records():
    """ORCHESTRATION trace + QLOO trace + PROVENANCE ledger, never mixed."""
    state = run_strong_fixture(STRONG)
    text = state.rendered_text

    assert "ORCHESTRATION (agent trace — separate from the Qloo trace below)" in text
    assert "EVIDENCE (Qloo trace)" in text
    assert "PROVENANCE" in text

    # The agent's trace comes before the Qloo trace it explains, and both come
    # before the STOP section; the provenance audit line sits inside STOP.
    positions = [
        text.index("ORCHESTRATION"),
        text.index("EVIDENCE (Qloo trace)"),
        text.index("\nSTOP\n"),
        text.index("PROVENANCE"),
    ]
    assert positions == sorted(positions)

    # The orchestration trace lives in the state, not in the Qloo recorder.
    assert state.transitions
    assert state.trace_rows
    assert state.ledger.problems() == []


def test_real_fixture_runs_stay_inside_the_budget():
    from app.runner import run_fixture as runner_run

    states = [run_strong_fixture(STRONG), runner_run(SPARSE)]
    for state in states:
        assert state.budget.steps_used <= state.budget.max_steps
        assert state.budget.qloo_calls_used <= state.budget.max_qloo_calls
        assert state.budget.qloo_calls_used == len(state.trace_rows) - 1  # minus the logical op
        assert state.status is RunStatus.FINISHED


def test_a_programme_with_no_usable_input_stops_as_invalid_input_end_to_end(tmp_path):
    """The input path, not a stub: a scenario whose programme carries nothing to
    look up. Written to a temporary directory, so the repository's two fixtures are
    untouched."""
    import json

    from app.runner import run_fixture as runner_run

    scenario = {
        "_fixture": True,
        "_fixture_notice": "temporary test scenario — invalid input",
        "scenario": "invalid_input_test",
        "description": "A programme with no ids at all: the agent must refuse as invalid input.",
        "programme": [{"title": "Untitled Reel", "year": None, "imdb_id": None, "entity_id": None}],
        "responses": {},
    }
    (tmp_path / "invalid_input_test.json").write_text(json.dumps(scenario), encoding="utf-8")

    from app.config import Settings

    settings = Settings.from_env(fixtures_dir=tmp_path, qloo_api_key=None)
    state = runner_run("invalid_input_test", settings=settings)

    assert state.stop.reason is StopReason.INVALID_INPUT
    assert state.stop.detail_code == "no_identifiers"
    assert state.budget.qloo_calls_used == 0
    assert not state.trace_rows
    assert "invalid_input" in state.rendered_text
    assert state.stop.reason is not StopReason.INSUFFICIENCY
