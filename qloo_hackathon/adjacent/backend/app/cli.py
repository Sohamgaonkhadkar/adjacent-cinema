"""Adjacent CLI — the milestone's visible surface.

    python -m app.cli run --fixture fixtures/portland_strong.json --mock
    python -m app.cli run --fixture fixtures/insufficient_evidence.json --mock

The command syntax is unchanged from Milestone 1; the internals now run through the
agent orchestrator (`app.agent`). Runs are fixture-only on purpose: `--mock` is
required and no network call is made. Live mode arrives once docs/API_NOTES.md
records a real probe (particularly probe D — `filter.results.entities`), because the
ranking design depends on it.

Exit codes:
    0  the run finished: either it produced ranked cohorts (`complete`) or it
       refused (`insufficiency`) — a refusal is a correct product outcome
    2  the run could not proceed: bad arguments, unknown fixture, invalid input,
       a tool/transport failure, or an exhausted budget. The stderr line always
       names which of those it was, because they are not the same thing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .qloo.params import registry_summary, unverified_params
from .runner import render_agent_trace, render_run_json, run_fixture

EXIT_OK = 0
EXIT_CANNOT_RUN = 2


def _add_run_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "run",
        help="run one scenario end-to-end and print the milestone sections",
        description="Run the fixture spine: programme → resolution → taste → cohorts → rank → stop.",
    )
    parser.add_argument(
        "--fixture",
        default="portland_strong",
        help="fixture name or path (e.g. fixtures/portland_strong.json). Default: portland_strong",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="replay a fixture. Required in Milestone 1: no live Qloo call is made here.",
    )
    parser.add_argument("--json", action="store_true", help="print the full run as JSON")
    parser.add_argument("--out", type=Path, default=None, help="also write the JSON run to PATH")

    parser.add_argument(
        "--quiet-summary",
        action="store_true",
        help="print only the STOP section (used by CI checks)",
    )
    parser.add_argument(
        "--show-agent-trace",
        action="store_true",
        help="print only the ORCHESTRATION section: the agent's state transitions",
    )


def _add_demo_live_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "demo-live",
        help="run a complete live Adjacent analysis against real Qloo",
        description=(
            "Run the verified demo programme through the full pipeline: "
            "trusted resolution → taste DNA → cross-domain expansion → "
            "single-query ranking → evidence evaluation.  Requires QLOO_API_KEY."
        ),
    )
    parser.add_argument("--json", action="store_true", help="print the full run as JSON")
    parser.add_argument("--out", type=Path, default=None, help="also write the JSON run to PATH")


def _add_params_parser(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        "params",
        help="print the Qloo parameter allowlist and which entries are unverified",
        description="The same data as GET /debug/params, without needing a server.",
    )


def _add_fixtures_parser(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        "list-fixtures",
        help="list the available scenario fixtures",
    )


def _add_cleanup_guest_sessions_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "cleanup-guest-sessions",
        help="delete expired guest sessions and their campaign data",
        description=(
            "Sweep the FilmSponsor database for expired or revoked guest sessions "
            "and delete them together with all associated campaign data. Safe to run "
            "repeatedly (idempotent) and concurrently with a live server. Intended "
            "for cron or a systemd timer on the OCI host."
        ),
    )
    parser.add_argument(
        "--db",
        default=None,
        help=(
            "SQLite database path. Defaults to ADJACENT_EXPERIMENTS_DB or "
            "the built-in data/processed/experiments.db."
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="suppress output when zero sessions are cleaned")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description="Adjacent — audience adjacency engine")
    parser.add_argument("--version", action="version", version="adjacent 0.1.0-milestone1")
    subparsers = parser.add_subparsers(dest="command", required=False)
    _add_run_parser(subparsers)
    _add_demo_live_parser(subparsers)
    _add_params_parser(subparsers)
    _add_fixtures_parser(subparsers)
    _add_cleanup_guest_sessions_parser(subparsers)
    return parser


def _cmd_run(args: argparse.Namespace, settings: Settings) -> int:
    if not args.mock:
        if not settings.has_api_key:
            print(
                "Milestone 1 runs on fixtures only. Pass --mock "
                "(no API key required).\n"
                "A live run needs QLOO_API_KEY and the probe results in docs/API_NOTES.md.",
                file=sys.stderr,
            )
            return EXIT_CANNOT_RUN
        print(
            "Live mode is not enabled in Milestone 1: the ranking path depends on probe D "
            "(filter.results.entities), which has not been verified against the live API yet.\n"
            "Run with --mock.",
            file=sys.stderr,
        )
        return EXIT_CANNOT_RUN

    try:
        run = run_fixture(args.fixture, settings=settings)
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_run_json(run), encoding="utf-8")
        print(f"[wrote {args.out}]", file=sys.stderr)

    if args.json:
        print(render_run_json(run))
    elif args.show_agent_trace:
        print(render_agent_trace(run))
    elif args.quiet_summary:
        print(f"stop_reason = {run.stop_reason}")
        print(f"message     = {run.stop_message}")
    else:
        print(run.rendered_text)

    if run.stop is None or run.stop.ok:
        return EXIT_OK
    if run.stop.refuses_recommendation:
        # A refusal is the product working. Exit 0, but say so on stderr for scripts.
        print("[stop_reason=insufficiency — no recommendation produced]", file=sys.stderr)
        return EXIT_OK
    # Everything else is "this run did not finish": say which, on stderr.
    print(f"[stop_reason={run.stop_reason} — {run.stop_message}]", file=sys.stderr)
    return EXIT_CANNOT_RUN


def _cmd_demo_live(args: argparse.Namespace, settings: Settings) -> int:
    """Run the verified demo programme against live Qloo."""
    if not settings.has_api_key:
        print(
            "demo-live requires QLOO_API_KEY.  Set it in your environment or .env file.",
            file=sys.stderr,
        )
        return EXIT_CANNOT_RUN

    from .live_runner import run_live
    from .resolution.demo_programme import DEMO_PROGRAMME

    try:
        run = run_live(DEMO_PROGRAMME, settings=settings)
    except Exception as exc:
        print(f"Live run failed: {exc}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(run.to_json(), encoding="utf-8")
        print(f"[wrote {args.out}]", file=sys.stderr)

    if args.json:
        print(run.to_json())
    else:
        print(run.rendered_text or "")

    if run.stop is None or run.stop.ok:
        return EXIT_OK
    if run.stop.refuses_recommendation:
        print("[stop_reason=insufficiency — no recommendation produced]", file=sys.stderr)
        return EXIT_OK
    print(f"[stop_reason={run.stop_reason} — {run.stop_message}]", file=sys.stderr)
    return EXIT_CANNOT_RUN


def _cmd_params(settings: Settings) -> int:
    summary = registry_summary()
    summary["unverified"] = [u.model_dump() if hasattr(u, "model_dump") else u for u in unverified_params()]
    print(json.dumps(summary, indent=2, default=str))
    return EXIT_OK


def _cmd_list_fixtures(settings: Settings) -> int:
    for path in sorted(settings.fixtures_dir.glob("*.json")):
        print(path.name)
    return EXIT_OK


def _cmd_cleanup_guest_sessions(args: argparse.Namespace) -> int:
    """Sweep expired guest sessions and their campaign trees."""
    from .api.creator_routes import EXPERIMENTS_DB_PATH
    from .domain.filmsponsor_guest_sessions import GuestSessionStore
    from .domain.filmsponsor_repository import FilmSponsorRepository

    db_path = Path(args.db) if args.db else EXPERIMENTS_DB_PATH
    if not db_path.exists():
        if not args.quiet:
            print(f"Database does not exist yet: {db_path}", file=sys.stderr)
        return EXIT_OK

    # Open the repository first so session-table triggers can reference the
    # campaign tables (mirrors the server startup order).
    repo = FilmSponsorRepository(db_path)
    try:
        store = GuestSessionStore(db_path)
        try:
            count = store.cleanup()
        finally:
            store.close()
    finally:
        repo.close()

    if count or not args.quiet:
        print(f"Cleaned {count} expired guest session(s) from {db_path}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings.from_env()

    if args.command in (None, "run"):
        if args.command is None:
            parser.print_help()
            return EXIT_OK
        return _cmd_run(args, settings)
    if args.command == "demo-live":
        return _cmd_demo_live(args, settings)
    if args.command == "params":
        return _cmd_params(settings)
    if args.command == "list-fixtures":
        return _cmd_list_fixtures(settings)
    if args.command == "cleanup-guest-sessions":
        return _cmd_cleanup_guest_sessions(args)

    parser.print_help()
    return EXIT_CANNOT_RUN


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
