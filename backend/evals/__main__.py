"""DocuMind eval CLI. Run from ``backend/``.

    python -m evals validate
    python -m evals retrieval [--offline] [--record --label L] [--check-baseline]
    python -m evals answers [--record --label L] [--limit N]

Needs EVAL_DATABASE_URL (or --database-url): a disposable Postgres+pgvector with
``alembic upgrade head`` applied. Never the production database.
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Callable
from dataclasses import asdict

from app.core.config import Settings, get_settings
from app.services.providers.factory import get_completion_provider, get_embedding_provider
from app.services.rate_limiter import SlidingWindowRateLimiter
from evals import paths
from evals.config import EvalSettings
from evals.embedding_cache import CachedEmbeddingProvider, EmbeddingCache
from evals.generation import TextCache
from evals.judge import Judge, JudgeCache, OpenAICompatibleJSONClient
from evals.metrics import regressions, summarize_answers, summarize_retrieval
from evals.report import (
    ANSWER_COLUMNS,
    RETRIEVAL_COLUMNS,
    git_commit,
    load_baseline,
    record_results,
    render_table,
    save_baseline,
    write_run,
)
from evals.rewrite import CachedRewriter
from evals.runner import (
    load_corpus,
    make_session_factory,
    require_disposable_database,
    require_migrated,
    reset_corpus,
    run_answers,
    run_retrieval,
)
from evals.schema import CorpusManifest, GoldenItem, corpus_problems, load_golden, load_manifest
from evals.throttle import rate_limit_signal

logger = logging.getLogger("evals")

_UNLIMITED_TOKENS = 1_000_000_000
_DEFAULT_TOLERANCE = 0.02


def _embedding_model_id(settings: Settings) -> str:
    # Part of the embedding cache key: keep the "gemini:<model>" format stable.
    return f"gemini:{settings.gemini_embedding_model}"


def _completion_model_id(settings: Settings) -> str:
    model = (
        settings.gemini_completion_model
        if settings.completion_provider == "gemini"
        else settings.groq_completion_model
    )
    return f"{settings.completion_provider}:{model}"


def _load_inputs() -> tuple[CorpusManifest, list[GoldenItem]]:
    manifest = load_manifest(paths.MANIFEST_PATH)
    items = load_golden(paths.GOLDEN_PATH)
    problems = corpus_problems(items, manifest, paths.CORPUS_DIR)
    if problems:
        raise SystemExit("Golden set / corpus problems:\n  " + "\n  ".join(problems))
    return manifest, items


def _database_url(args: argparse.Namespace, eval_settings: EvalSettings) -> str:
    url = args.database_url or eval_settings.eval_database_url
    if not url:
        raise SystemExit("Set EVAL_DATABASE_URL (backend/.env.eval) or pass --database-url")
    require_disposable_database(url, allow_remote=args.allow_remote_db)
    return url


def _embedder(settings: Settings, cache: EmbeddingCache, offline: bool) -> CachedEmbeddingProvider:
    return CachedEmbeddingProvider(
        cache,
        model=_embedding_model_id(settings),
        dim=settings.embedding_dim,
        inner=None if offline else get_embedding_provider(settings),
    )


def _rewriter(
    settings: Settings, eval_settings: EvalSettings, cache: TextCache, offline: bool
) -> CachedRewriter:
    return CachedRewriter(
        None if offline else get_completion_provider(settings),
        cache,
        SlidingWindowRateLimiter(eval_settings.eval_generation_rpm, _UNLIMITED_TOKENS),
        model=_completion_model_id(settings),
        max_attempts=eval_settings.eval_max_attempts,
    )


def cmd_validate(_args: argparse.Namespace) -> int:
    manifest, items = _load_inputs()
    counts: dict[str, int] = {}
    for item in items:
        counts[item.tag] = counts.get(item.tag, 0) + 1
    print(f"OK: {len(items)} golden items over {len(manifest.documents)} corpus files")
    print("  " + ", ".join(f"{tag}={n}" for tag, n in sorted(counts.items())))
    return 0


async def cmd_retrieval(args: argparse.Namespace) -> int:
    settings = get_settings()
    eval_settings = EvalSettings()
    manifest, items = _load_inputs()
    engine, factory = make_session_factory(_database_url(args, eval_settings))
    cache = EmbeddingCache.load(paths.EMBEDDING_CACHE_PATH)
    embedder = _embedder(settings, cache, args.offline)
    rewrite_cache = TextCache.load(paths.REWRITE_CACHE_PATH)
    rewriter = _rewriter(settings, eval_settings, rewrite_cache, args.offline)
    try:
        await require_migrated(factory)
        if args.rebuild:
            await reset_corpus(factory)
        chunk_counts = await load_corpus(
            factory, embedder, manifest, paths.CORPUS_DIR, settings, after_document=_saver(cache)
        )
        records = await run_retrieval(factory, embedder, items, rewriter=rewriter)
    finally:
        if cache.dirty:
            cache.save()
        if rewrite_cache.dirty:
            rewrite_cache.save()
        await engine.dispose()

    summary = summarize_retrieval([record.score for record in records])
    print(render_table(summary, RETRIEVAL_COLUMNS))
    print(f"embeddings: {embedder.hits} cached, {embedder.misses} fetched; chunks: {chunk_counts}")
    print(f"query rewrites: {rewriter.hits} cached, {rewriter.misses} fetched")
    run_path = write_run(
        paths.RUNS_DIR,
        "retrieval",
        args.label,
        {
            "commit": git_commit(),
            "summary": summary,
            "chunk_counts": chunk_counts,
            "records": [asdict(record) for record in records],
        },
    )
    print(f"run written to {run_path}")

    if args.record:
        record_results(
            paths.RESULTS_PATH,
            kind="retrieval",
            label=args.label,
            summary=summary,
            notes=args.notes,
        )
    if args.write_baseline:
        save_baseline(paths.BASELINE_PATH, summary, args.tolerance, git_commit())
        print(f"baseline written to {paths.BASELINE_PATH}")
    if args.check_baseline:
        baseline, tolerance = load_baseline(paths.BASELINE_PATH)
        failures = regressions(summary, baseline, tolerance)
        if failures:
            print("RETRIEVAL REGRESSION:\n  " + "\n  ".join(failures))
            return 1
        print(f"no regression vs baseline (tolerance {tolerance})")
    return 0


async def cmd_answers(args: argparse.Namespace) -> int:
    if args.record and args.limit:
        raise SystemExit("--record needs the full golden set; drop --limit")
    settings = get_settings()
    eval_settings = EvalSettings()
    if not eval_settings.groq_api_key:
        raise SystemExit("GROQ_API_KEY is required for the answer judge")
    manifest, items = _load_inputs()
    if args.limit:
        items = items[: args.limit]
    engine, factory = make_session_factory(_database_url(args, eval_settings))
    cache = EmbeddingCache.load(paths.EMBEDDING_CACHE_PATH)
    judge_cache = JudgeCache.load(paths.JUDGE_CACHE_PATH)
    answer_cache = TextCache.load(paths.ANSWER_CACHE_PATH)
    rewrite_cache = TextCache.load(paths.REWRITE_CACHE_PATH)
    rewriter = _rewriter(settings, eval_settings, rewrite_cache, offline=False)
    generation_model = _completion_model_id(settings)
    embedder = _embedder(settings, cache, offline=False)
    judge = Judge(
        OpenAICompatibleJSONClient(
            api_key=eval_settings.groq_api_key,
            base_url=eval_settings.eval_judge_base_url,
            model=eval_settings.eval_judge_model,
        ),
        judge_cache,
        SlidingWindowRateLimiter(eval_settings.eval_judge_rpm, _UNLIMITED_TOKENS),
        model=eval_settings.eval_judge_model,
        max_attempts=eval_settings.eval_max_attempts,
    )

    def save_caches() -> None:
        if cache.dirty:
            cache.save()
        if judge_cache.dirty:
            judge_cache.save()
        if answer_cache.dirty:
            answer_cache.save()
        if rewrite_cache.dirty:
            rewrite_cache.save()

    done = 0

    def after_item() -> None:
        nonlocal done
        done += 1
        save_caches()

    try:
        await require_migrated(factory)
        await load_corpus(
            factory, embedder, manifest, paths.CORPUS_DIR, settings, after_document=save_caches
        )
        records = await run_answers(
            factory,
            embedder,
            get_completion_provider(settings),
            judge,
            items,
            SlidingWindowRateLimiter(eval_settings.eval_generation_rpm, _UNLIMITED_TOKENS),
            answer_cache,
            generation_model=generation_model,
            top_k=args.top_k,
            max_attempts=eval_settings.eval_max_attempts,
            after_item=after_item,
            rewriter=rewriter,
        )
    except Exception as exc:
        signal = rate_limit_signal(exc)
        if signal is None or not signal.daily_quota:
            raise
        # Everything finished so far is cached; the next run resumes from here.
        print(
            f"Daily quota reached after {done} of {len(items)} questions. Answers and "
            "verdicts so far are cached; rerun the same command after the quota resets.",
            file=sys.stderr,
        )
        return 3
    finally:
        save_caches()
        await engine.dispose()

    summary = summarize_answers([record.score for record in records])
    print(render_table(summary, ANSWER_COLUMNS))
    print(f"judge: {judge.calls} calls, {judge.cache_hits} cached")
    run_path = write_run(
        paths.RUNS_DIR,
        "answers",
        args.label,
        {
            "commit": git_commit(),
            "judge_model": eval_settings.eval_judge_model,
            "generator": generation_model,
            "top_k": args.top_k,
            "summary": summary,
            "records": [asdict(record) for record in records],
        },
    )
    print(f"run written to {run_path}")
    if args.record:
        record_results(
            paths.RESULTS_PATH, kind="answers", label=args.label, summary=summary, notes=args.notes
        )
    return 0


def _saver(cache: EmbeddingCache) -> Callable[[], None]:
    def save() -> None:
        if cache.dirty:
            cache.save()

    return save


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check golden set, manifest and corpus hashes")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--database-url", help="defaults to EVAL_DATABASE_URL")
        p.add_argument("--allow-remote-db", action="store_true")
        p.add_argument("--label", default="adhoc", help="row label, e.g. baseline")
        p.add_argument("--notes", default="", help="free-text notes column")
        p.add_argument("--record", action="store_true", help="append to docs/V2_RESULTS.md")
        p.add_argument("--rebuild", action="store_true", help="re-ingest the corpus first")

    retrieval = sub.add_parser("retrieval", help="recall@k and MRR")
    common(retrieval)
    retrieval.add_argument("--offline", action="store_true", help="cache only; misses fail")
    retrieval.add_argument("--check-baseline", action="store_true")
    retrieval.add_argument("--write-baseline", action="store_true")
    retrieval.add_argument("--tolerance", type=float, default=_DEFAULT_TOLERANCE)

    answers = sub.add_parser("answers", help="judge-scored answer quality")
    common(answers)
    answers.add_argument("--top-k", type=int, default=5)
    answers.add_argument("--limit", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "retrieval":
        return asyncio.run(cmd_retrieval(args))
    return asyncio.run(cmd_answers(args))


if __name__ == "__main__":
    sys.exit(main())
