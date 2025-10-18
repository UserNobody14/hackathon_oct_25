from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid

from .codegen import generate_script
from .executor import execute_script
from .inspector import inspect_file


app = FastAPI(title="AIDA Backend API")
# Allow all origins in dev; tighten in production as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static artifacts mount
ARTIFACTS_ROOT = Path("artifacts").resolve()
ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_ROOT)), name="artifacts")


# Request/Response models aligned with frontend/src/lib/api.ts
class InspectRequest(BaseModel):
    path: str
    format: str
    rows: int = 1000
    seed: int = 42


class InspectResponse(BaseModel):
    schema: dict[str, str]
    samplePreview: list[dict]
    stats: dict


class GenerationPreferences(BaseModel):
    viz: str = Field("plotly", pattern="^(plotly|seaborn)$")
    engine: str = Field("pandas", pattern="^(pandas|polars)$")


class GenerateRequest(BaseModel):
    inspect: InspectResponse
    prefs: GenerationPreferences


class GenerateResponse(BaseModel):
    scriptPath: str
    scriptText: str


class ExecuteEnv(BaseModel):
    AIDA_INPUT: str
    AIDA_OUTPUT: str


class ExecuteRequest(BaseModel):
    scriptPath: str
    env: ExecuteEnv


class Artifact(BaseModel):
    type: str
    path: str
    title: str | None = None


class ExecuteResponse(BaseModel):
    artifacts: list[Artifact]


@app.post("/api/inspect", response_model=InspectResponse)
async def api_inspect(req: InspectRequest) -> InspectResponse:
    try:
        res = inspect_file(req.path, format=req.format, rows=req.rows, seed=req.seed)
        return InspectResponse(
            schema=res.schema, samplePreview=res.samplePreview, stats=res.stats
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest) -> GenerateResponse:
    try:
        result = generate_script(
            req.inspect.model_dump(), req.prefs.model_dump(), out_dir="scripts"
        )
        return GenerateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/execute")
async def api_execute(req: ExecuteRequest):
    # If client can handle streaming logs, we could stream stdout here. For now, run and return JSON.
    try:
        # Create a unique run directory under artifacts to avoid mixing outputs
        run_id = uuid.uuid4().hex
        run_dir = ARTIFACTS_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        result = execute_script(
            req.scriptPath,
            env={
                "AIDA_INPUT": req.env.AIDA_INPUT,
                "AIDA_OUTPUT": str(run_dir),
            },
            use_uv=True,
        )
        # Rewrite artifact filesystem paths to web URLs under /artifacts/{run_id}/...
        rewritten: list[dict] = []
        for a in result.get("artifacts", []):
            try:
                p = Path(a.get("path", "")).resolve()
                # Ensure path is inside run_dir
                rel = p.relative_to(run_dir)
                url_path = f"/artifacts/{run_id}/{rel.as_posix()}"
                rewritten.append(
                    {
                        "type": a.get("type", "html"),
                        "path": url_path,
                        "title": a.get("title"),
                    }
                )
            except Exception:
                # Fallback: do not expose arbitrary paths; skip
                continue
        return JSONResponse(content={"artifacts": rewritten})
    except RuntimeError as e:
        # e.args[0] may already include a JSON payload from executor
        try:
            payload = json.loads(e.args[0])
            return JSONResponse(content=payload, status_code=500)
        except Exception:
            raise HTTPException(status_code=500, detail=str(e))


def create_app() -> FastAPI:
    return app


def run(host: str = "127.0.0.1", port: int = 8099) -> None:
    # Lazy import to avoid uvicorn dependency at import time
    import uvicorn  # type: ignore

    uvicorn.run(
        "aida.server:create_app", host=host, port=port, reload=False, factory=True
    )


if __name__ == "__main__":
    run()
