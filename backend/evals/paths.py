from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
CORPUS_DIR = EVALS_DIR / "corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
GOLDEN_PATH = EVALS_DIR / "golden.jsonl"
EMBEDDING_CACHE_PATH = EVALS_DIR / "cache" / "embeddings.jsonl.gz"
JUDGE_CACHE_PATH = EVALS_DIR / "cache" / "judge.jsonl"
BASELINE_PATH = EVALS_DIR / "baseline.json"
RUNS_DIR = EVALS_DIR / "runs"
RESULTS_PATH = EVALS_DIR.parent.parent / "docs" / "V2_RESULTS.md"
