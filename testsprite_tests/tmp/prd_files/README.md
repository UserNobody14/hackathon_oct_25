## AIDA — AI Instant Data Analysis

An AI-assisted tool that, given a local data file (csv, parquet, json), quickly samples and inspects it, then auto-generates a high-quality Python analysis script that produces rich visualizations and insights. The generated script is reproducible, editable, and can be run locally. Everything runs on your machine by default.

### Goals
- **Zero-setup insight**: Point to a file, get meaningful charts, stats, and a narrative within minutes.
- **Reproducibility**: Generate a deterministic Python script you can version, audit, and customize.
- **Privacy-first**: Local-first workflow. Optional model providers pluggable via environment variables.
- **Front‑end usability**: Clear UX for uploading/selecting files, sampling controls, script preview, and results.

### Non‑Goals (initial release)
- Full data cleaning/ETL pipeline builder.
- Distributed/cluster execution.
- Handling exotic formats beyond csv/parquet/json.

## High‑Level Flow
1. User selects a file in the UI (or via CLI).
2. Tool performs lightweight inspection: schema inference, sampling, basic profiling.
3. A prompt composer builds a context to guide code generation.
4. An LLM-based generator emits a Python script tailored to the dataset (visualizations, stats, commentary).
5. The script is saved to disk, then executed to produce artifacts (HTML report and/or images).
6. Frontend shows the generated script, logs, and visualizations.

## Architecture Overview

### Components
- **Frontend (React + Vite, managed by bun)**
  - Pages: File Select, Inspect, Script, Results.
  - Core component: `DataAnalyzer` orchestrates sampling, generation, execution, rendering.
  - Local Bun server bridges frontend to Python via a simple HTTP API.

- **Backend/CLI (Python 3.12, managed by uv)**
  - `inspector`: sampling (random/head/tail), schema & basic profiling.
  - `prompt_composer`: builds system+user prompts from schema, samples, and user preferences.
  - `codegen`: generates a deterministic Python analysis script.
  - `executor`: runs the generated script in an isolated venv and collects outputs.

- **LLM Provider (pluggable)**
  - OpenAI-compatible, Anthropic-compatible, or local models. Selected via environment variables.

### Data Flow
- Frontend uploads path/metadata → Backend `inspector` reads small samples (e.g., 1k rows max) → `prompt_composer` → `codegen` emits `analysis_<timestamp>.py` → `executor` runs with `uv run` → artifacts (HTML, PNGs) → Frontend displays results.

### Supported Formats
- CSV (delimiter and encoding inference)
- Parquet (via pyarrow)
- JSON (line-delimited suggested; fallbacks included)

## Frontend Design (Focus)

### Primary Component: `DataAnalyzer`
Responsible for the end-to-end UX from file selection to results. Core states:
- `idle` → `inspecting` → `generating` → `executing` → `succeeded` | `failed`

#### UI Structure
- **File Input**: Path picker or drag-and-drop; format autodetect with manual override.
- **Sampling Controls**: strategy (head/tail/random), row limit, seed.
- **Inspect Panel**: schema preview, sample rows (virtualized table), inferred types, null counts, cardinalities.
- **Script Panel**: read-only preview of generated Python; copy/download buttons.
- **Run Panel**: execution logs (streamed), config (viz library, output dir, CPU/memory hints).
- **Results Panel**: responsive gallery of charts + text insights; link to HTML report.

#### UX Principles
- Progressive disclosure: hide advanced knobs by default.
- Optimistic updates with clear loading states.
- Persistent session: remember last file and settings.
- Accessible keyboard navigation and ARIA labels for all controls.

#### Performance Notes
- Virtualize sample table (thousands of rows) and defer expensive computations.
- Stream backend logs and partial results for immediate feedback.
- Debounce prompt recomposition on rapid setting changes.

## Frontend Testing Strategy (Focus)

We use Vitest + Testing Library + Playwright, all run via bun.

### Unit/Component Tests
- Render `DataAnalyzer` with a mocked backend service.
- Assert state transitions for `idle → inspecting → generating → executing → succeeded`.
- Verify accessibility: landmarks, labels, focus order, keyboard triggers.
- Validate sampling controls change the request payloads.
- Snapshot minimal DOM chunks only for critical templates.

```bash
# run unit tests
bun test
```

### Integration Tests
- Mock HTTP API (MSW) to simulate inspector/codegen/executor responses and streaming logs.
- Validate that generated script preview updates and results gallery renders charts metadata.

### E2E Tests (Playwright)
- Happy path: select file → inspect → generate → execute → view charts.
- Error paths: bad file, unsupported format, generation timeout, execution error.
- Visual regression: pin critical states (empty, loading, results) with screenshots.

```bash
# install and run e2e
bunx playwright install
bunx playwright test
```

### Contract Tests
- Define TypeScript types for backend payloads (inspect request, generation request, run result).
- Assert shape compatibility between frontend client and backend server.

## Python Code Generation

### Script Characteristics
- Deterministic: set random seeds, freeze current time passed in by backend.
- Explicit imports; pinned libraries in `uv` environment.
- Configurable backend preferences (pandas vs polars; seaborn vs plotly) via generation options.
- Outputs: `report.html` (plotly or ydata-profiling when feasible) and individual images when static libs are selected.

### Example Generated Script Skeleton

```python
import os
import random
import numpy as np
import pandas as pd
import plotly.express as px

random.seed(42)
np.random.seed(42)

def main(input_path: str, output_dir: str) -> None:
    df = pd.read_csv(input_path)  # format handler is chosen based on metadata
    # Basic profile
    summary = df.describe(include='all')
    # Example viz
    for col in df.select_dtypes(include=['number']).columns:
        fig = px.histogram(df, x=col, nbins=30, title=f"Distribution of {col}")
        fig.write_html(os.path.join(output_dir, f"hist_{col}.html"))

if __name__ == "__main__":
    main(input_path=os.environ["AIDA_INPUT"], output_dir=os.environ["AIDA_OUTPUT"]) 
```

## Local Development

### Prerequisites
- bun (`brew install bun`)
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12

### Install

```bash
# frontend deps
bun install

# python env and deps
uv venv
uv pip install -r requirements.txt
```

### Run (Dev)

```bash
# start frontend (Vite)
bun dev

# run backend commands as needed
uv run aida --help
```

### Test

```bash
# frontend unit/integration
bun test

# e2e
bunx playwright install
bunx playwright test

# python
uv run pytest -q
```

## CLI Workflow

### Inspect
```bash
uv run aida inspect --file data/sample.csv --format csv --rows 1000 --seed 42 --out .aida/inspect.json
```

### Generate Script
```bash
uv run aida generate \
  --inspect .aida/inspect.json \
  --viz plotly \
  --engine pandas \
  --out scripts/analysis_$(date +%s).py
```

### Execute Script
```bash
AIDA_INPUT=data/sample.csv AIDA_OUTPUT=artifacts \
uv run python scripts/analysis_123.py
```

### End-to-end (one shot)
```bash
uv run aida analyze --file data/sample.csv --format csv --viz plotly --engine pandas --out-dir artifacts
```

## Backend API (for Frontend)

- `POST /api/inspect` { path, format, rows, seed } → { schema, samplePreview, stats }
- `POST /api/generate` { inspect, prefs } → { scriptPath, scriptText }
- `POST /api/execute` { scriptPath, env: { AIDA_INPUT, AIDA_OUTPUT } } → stream(logs) + { artifacts }

Implementation detail: a lightweight Bun server can expose these endpoints and shell out to `uv run` for Python commands.

## Dataset Handling & Safety
- Never read entire files by default; sample capped rows.
- Size guardrails; warn on files >1GB.
- Sanitized paths; refuse network egress unless enabled.
- Clear temp cleanup policy (`.aida/`, `artifacts/`).

## Proposed Repo Layout

```
frontend/
  src/
    components/DataAnalyzer.tsx
    lib/api.ts
    pages/{File,Inspect,Script,Results}.tsx
  tests/
    DataAnalyzer.test.tsx
    e2e/
backend/
  aida/
    cli.py
    inspector.py
    prompt_composer.py
    codegen.py
    executor.py
  tests/
scripts/
artifacts/
.aida/
```

## Roadmap
- Add profiling with `ydata-profiling` optionally for HTML summaries.
- Add semantic chart selection (anomaly detection, time series decomposition).
- Add parquet columnar lazy loading with Polars.
- Add notebook emission alongside scripts.

## Environment Variables
- `AIDA_MODEL_PROVIDER`: `openai`, `anthropic`, `local`.
- `AIDA_MODEL`: model name/id.
- `AIDA_OUTPUT`: default output directory for artifacts.

## Contributing
PRs welcome. Please include tests for frontend components and Python modules. Keep generated scripts deterministic. Prefer `bun` and `uv` commands in docs and scripts.


