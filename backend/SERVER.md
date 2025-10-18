# AIDA FastAPI Server

This server implements the frontend API contract in `frontend/src/lib/api.ts`:
- POST `/api/inspect`
- POST `/api/generate`
- POST `/api/execute`

It mirrors the Bun server contract, but runs purely in Python.

## Prerequisites
- Python 3.12+
- `uv` package manager installed

## Install dependencies
```bash
cd backend
uv lock
uv sync --frozen
```

## Run the server (development)
```bash
cd backend
uv run python -m aida.server
# serves on http://127.0.0.1:8099
```

Alternatively, with uvicorn directly (factory pattern):
```bash
cd backend
uv run uvicorn aida.server:create_app --host 127.0.0.1 --port 8099 --factory
```

Health check:
```bash
curl -s http://127.0.0.1:8099/health
```

## Endpoints

### POST /api/inspect
Request body:
```json
{
  "path": "/absolute/path/to/data.csv",
  "format": "csv",
  "rows": 1000,
  "seed": 42
}
```
Response body:
```json
{
  "schema": {"colA": "int64"},
  "samplePreview": [{"colA": 1}],
  "stats": {"rowCount": 123}
}
```

Example:
```bash
# create a tiny sample
cd /Users/benjaminsobel/Code/hackathon_oct_25
printf "a,b\n1,2\n3,4\n" > sample.csv

# call inspect
curl -sS -X POST http://127.0.0.1:8099/api/inspect \
  -H 'Content-Type: application/json' \
  -d '{"path":"/Users/benjaminsobel/Code/hackathon_oct_25/sample.csv","format":"csv","rows":2,"seed":42}'
```

### POST /api/generate
Request body (using previous inspect response):
```json
{
  "inspect": {"schema": {}, "samplePreview": [], "stats": {}},
  "prefs": {"viz": "plotly", "engine": "pandas"}
}
```
Response contains a path to the generated script and its text:
```json
{"scriptPath": "scripts/analysis_1734567890.py", "scriptText": "..."}
```

Example using the saved inspect file from `backend/.aida/inspect.json`:
```bash
cd backend
curl -sS -X POST http://127.0.0.1:8099/api/generate \
  -H 'Content-Type: application/json' \
  -d @.aida/inspect.json | jq .
```

### POST /api/execute
Request body:
```json
{
  "scriptPath": "scripts/analysis_1734567890.py",
  "env": {
    "AIDA_INPUT": "/absolute/path/to/data.csv",
    "AIDA_OUTPUT": "artifacts"
  }
}
```
Response body:
```json
{
  "artifacts": [
    {"type": "html", "path": "artifacts/report.html", "title": "Report"}
  ]
}
```

Example:
```bash
cd backend
SCRIPT=$(ls -1 scripts/analysis_*.py | tail -n1)
curl -sS -X POST http://127.0.0.1:8099/api/execute \
  -H 'Content-Type: application/json' \
  -d "{\"scriptPath\":\"$SCRIPT\",\"env\":{\"AIDA_INPUT\":\"../sample.csv\",\"AIDA_OUTPUT\":\"artifacts\"}}" | jq .
```

## Notes
- CORS is enabled for all origins by default for local development.
- The server shells out to `uv run` to execute generated scripts in the managed environment.
- For production, tighten CORS and add authentication as needed.
