## AIDA Backend — Python Service and CLI

An implementation plan and setup guide for the Python backend that powers inspection, code generation, and execution. This document elaborates the backend sections from the main README with concrete steps using uv and Python 3.12, plus the HTTP contract used by the frontend.

### Goals
- Deterministic and reproducible analysis script generation
- Local-first execution with clear safety and resource limits
- Simple contracts to integrate with the Bun-powered frontend

---

## Prerequisites
- Python 3.12 (recommended)
- uv (Python packaging/runtime)
  - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Note: pyproject currently sets `requires-python = ">=3.13"`. Change this to `>=3.12` if you are on 3.12, then run `uv sync`.

---

## Environment Setup (uv)

Use uv to manage the environment from `pyproject.toml`.

```bash
# from repo root or the backend directory
uv sync            # creates venv and installs deps from pyproject

# run Python in the managed environment
uv run python -V   # should show 3.12.x
```

If you later add test dependencies or optional extras, prefer adding them to `pyproject.toml` and re-running `uv sync`.

---

## Current State vs. Planned Layout

Today, there is a placeholder:
- `backend/main.py` — minimal stub

Planned backend package (to be created iteratively):

```
backend/
  aida/
    __init__.py
    cli.py                # CLI entrypoint (Typer/Click)
    inspector.py          # sampling & lightweight profiling
    prompt_composer.py    # builds structured prompts from inspect output
    codegen.py            # generates deterministic analysis scripts
    executor.py           # runs generated scripts and collects artifacts
  tests/
    test_inspector.py
    test_codegen.py
    test_executor.py
```

Recommended supporting directories at repo root:
```
scripts/     # generated Python analysis scripts
.aida/       # ephemeral inspect outputs, temp files
artifacts/   # HTML reports, images, and other outputs from execution
```

---

## Runtime Flow (Backend responsibilities)
1. Inspect
   - Read small sample (default 1000 rows, seeded) and infer schema, basic stats
   - Output structured JSON (schema, samplePreview, stats)
2. Generate
   - Build prompt from inspect output and user preferences (viz, engine)
   - Emit a deterministic Python script and write to `scripts/analysis_<timestamp>.py`
3. Execute
   - Run the generated script with `AIDA_INPUT` and `AIDA_OUTPUT` env vars
   - Stream logs; collect artifacts (HTML/PNGs) and return metadata

Determinism guidelines:
- Set all random seeds in generated scripts
- Freeze any time-dependent values passed from backend
- Pin libraries in the uv environment (via `pyproject.toml`)

---

## CLI Design (to be implemented)

Use Typer (or Click) under `aida/cli.py` and expose commands via `uv run -m aida.cli` (module) or a console script entry in `pyproject.toml` later.

- Inspect
```bash
uv run -m aida.cli inspect \
  --file /absolute/path/to/data.csv \
  --format csv \
  --rows 1000 \
  --seed 42 \
  --out .aida/inspect.json
```

- Generate
```bash
uv run -m aida.cli generate \
  --inspect .aida/inspect.json \
  --viz plotly \
  --engine pandas \
  --out scripts/analysis_$(date +%s).py
```

- Execute
```bash
AIDA_INPUT=/absolute/path/to/data.csv AIDA_OUTPUT=artifacts \
uv run -m aida.cli execute --script scripts/analysis_123.py
```

- One-shot Analyze
```bash
uv run -m aida.cli analyze \
  --file /absolute/path/to/data.csv \
  --format csv \
  --viz plotly \
  --engine pandas \
  --out-dir artifacts
```

Exit codes and error messages should be explicit and actionable. Commands should write machine-readable JSON to stdout when requested (e.g., `--json`).

---

## HTTP API Contract (for frontend)

Endpoints (served by a lightweight Bun server that shells out to `uv run`, or by a Python HTTP server if preferred):

- POST `/api/inspect`
  - Request JSON:
```json
{
  "path": "/absolute/path/to/data.csv",
  "format": "csv",
  "rows": 1000,
  "seed": 42
}
```
  - Response JSON:
```json
{
  "schema": {"colA": "int64", "colB": "string"},
  "samplePreview": [{"colA": 1, "colB": "x"}],
  "stats": {"rowCount": 123456}
}
```

- POST `/api/generate`
  - Request JSON:
```json
{
  "inspect": { "schema": {}, "samplePreview": [], "stats": {} },
  "prefs": { "viz": "plotly", "engine": "pandas" }
}
```
  - Response JSON:
```json
{
  "scriptPath": "scripts/analysis_1734567890.py",
  "scriptText": "import ...\n..."
}
```

- POST `/api/execute`
  - Request JSON:
```json
{
  "scriptPath": "scripts/analysis_1734567890.py",
  "env": {
    "AIDA_INPUT": "/absolute/path/to/data.csv",
    "AIDA_OUTPUT": "artifacts"
  }
}
```
  - Streaming logs: Prefer `text/event-stream` or chunked `text/plain` during execution.
  - Final Response JSON:
```json
{
  "artifacts": [
    { "type": "html", "path": "artifacts/report.html", "title": "Report" },
    { "type": "html", "path": "artifacts/hist_colA.html", "title": "Distribution of colA" }
  ]
}
```

These shapes match the frontend types in `frontend/src/lib/api.ts`.

---

## Safety and Performance Guardrails
- Sampling defaults and caps (e.g., 1000 rows) to avoid reading full files by default
- File size checks; warn or refuse analysis for files > 1GB unless overridden
- Path sanitization; avoid network egress unless explicitly enabled
- Clear temp and artifact directories: `.aida/` and `artifacts/`
- Deterministic seeds and explicit version pinning for reproducibility
- Timeouts and resource hints for execution (CPU/memory notes)

---

## Environment Variables
- `AIDA_MODEL_PROVIDER`: `openai`, `anthropic`, `local`
- `AIDA_MODEL`: model id/name
- `AIDA_OUTPUT`: default artifact output directory (e.g., `artifacts`)

Optional future variables:
- `AIDA_ENGINE`: `pandas` or `polars` default
- `AIDA_VIZ`: default viz library (`plotly` or `seaborn`)

---

## Development & Testing

- Quick run (current stub):
```bash
uv run python backend/main.py
```

- Add tests under `backend/tests/` and run:
```bash
uv run pytest -q
```

- Lint/format (suggested tooling):
  - Ruff for linting: add to `pyproject.toml` and run `uvx ruff check .`
  - Black or Ruff formatter for formatting

---

## Next Steps (Implementation Plan)
1. Create package `backend/aida/` with `__init__.py`
2. Implement `inspector.py` with CSV/Parquet/JSON sampling, schema inference, and stats
3. Implement `prompt_composer.py` to build deterministic prompt context
4. Implement `codegen.py` to produce scripts with seeded randomness and explicit imports
5. Implement `executor.py` to run scripts via `uv run`, stream logs, and collect artifacts
6. Wire `cli.py` commands to call the modules above; add console_script in `pyproject.toml`
7. (Optional) Provide a Python HTTP server alternative mirroring the Bun endpoints

Keep contracts stable and versioned; ensure changes are reflected in the frontend types and tests.
