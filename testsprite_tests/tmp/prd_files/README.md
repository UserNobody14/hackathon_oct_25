# bun-react-tailwind-shadcn-template

To install dependencies:

```bash
bun install
```

To start a development server:

```bash
bun dev
```

To run for production:

```bash
bun start
```

This project was created using `bun init` in bun v1.2.21. [Bun](https://bun.com) is a fast all-in-one JavaScript runtime.

## Frontend Overview

- Pages: `File`, `Inspect`, `Script`, `Results`.
- Core component: `DataAnalyzer` orchestrates sampling, generation, execution, and rendering of results.
- The local Bun server serves the built assets and the app communicates with the Python backend via a simple HTTP API.

## Frontend Design

### Primary Component: `DataAnalyzer`
Responsible for the end-to-end UX from file selection to results. Core states:
- `idle → inspecting → generating → executing → succeeded | failed`

#### UI Structure
- File Input: File chooser (multipart upload); format autodetect with manual override.
- Sampling Controls: strategy (head/tail/random), row limit, seed.
- Inspect Panel: schema preview, sample rows (virtualized table), inferred types, null counts, cardinalities.
- Script Panel: read-only preview of generated Python; copy/download buttons.
- Run Panel: execution logs (streamed), config (viz library, output dir, CPU/memory hints).
- Results Panel: responsive gallery of charts + text insights; link to HTML report.

#### UX Principles
- Progressive disclosure: hide advanced knobs by default.
- Optimistic updates with clear loading states.
- Persistent session: remember last file and settings.
- Accessible keyboard navigation and ARIA labels for all controls.

#### Performance Notes
- Virtualize sample table (thousands of rows) and defer expensive computations.
- Stream backend logs and partial results for immediate feedback.
- Debounce prompt recomposition on rapid setting changes.

## Data Flow
- Upload file via multipart → backend stores under `uploads/` and returns absolute path.
- Backend `inspector` reads small samples (e.g., up to 1k rows) → `prompt_composer` → `codegen` emits `analysis_<timestamp>.py`.
- `executor` runs with `uv run` → artifacts (HTML, images) → frontend displays results.

## Frontend Testing

We use Vitest + Testing Library + Playwright, all run via Bun.

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

## Local Development (Frontend)

### Prerequisites
- Bun
- Node API-compatible browser tooling (bundled by Bun)

### Install

```bash
bun install
```

### Run (Dev)

```bash
# starts the app (dev hot reload). Default port configured in scripts is 4173
bun dev
```

### Test

```bash
# unit/integration
bun test

# e2e
bunx playwright install
bunx playwright test
```

## Backend API (for Frontend)

- `POST /api/upload` multipart/form-data field `file` → { path, originalName, size, mimeType }
- `POST /api/inspect` { path, format, rows, seed } → { schema, samplePreview, stats }
- `POST /api/generate` { inspect, prefs } → { scriptPath, scriptText }
- `POST /api/execute` { scriptPath, env: { AIDA_INPUT, AIDA_OUTPUT } } → stream(logs) + { artifacts }

Note: The frontend must first upload the file via `/api/upload` and then use the returned `path` for subsequent requests. Passing client-side file paths is not supported for security reasons.
