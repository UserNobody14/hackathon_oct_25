from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

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
        result = execute_script(
            req.scriptPath,
            env={"AIDA_INPUT": req.env.AIDA_INPUT, "AIDA_OUTPUT": req.env.AIDA_OUTPUT},
            use_uv=True,
        )
        return JSONResponse(content={"artifacts": result["artifacts"]})
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
