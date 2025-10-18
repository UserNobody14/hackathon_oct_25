from __future__ import annotations

import json
import os
import time
from pathlib import Path

import typer

from .executor import execute_script
from .inspector import InspectResult, inspect_file
from .codegen import generate_script


app = typer.Typer(add_completion=False)


@app.command()
def inspect(
    file: str = typer.Option(..., "--file", help="Path to input data file"),
    format: str | None = typer.Option(None, "--format", help="csv|parquet|json|jsonl"),
    rows: int = typer.Option(1000, "--rows", help="Preview/sample row count"),
    seed: int = typer.Option(42, "--seed", help="Deterministic sampling seed"),
    out: str = typer.Option(".aida/inspect.json", "--out", help="Output JSON path"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON to stdout"),
) -> None:
    res: InspectResult = inspect_file(file, format=format, rows=rows, seed=seed)
    payload = {
        "schema": res.schema,
        "samplePreview": res.samplePreview,
        "stats": res.stats,
    }
    out_path = Path(out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if json_out:
        typer.echo(json.dumps(payload))


@app.command()
def generate(
    inspect_json: str = typer.Option(..., "--inspect", help="Path to inspect JSON"),
    viz: str = typer.Option("plotly", "--viz", help="plotly|seaborn"),
    engine: str = typer.Option("pandas", "--engine", help="pandas|polars (future)"),
    out: str | None = typer.Option(None, "--out", help="Output script path"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON to stdout"),
) -> None:
    inspect_payload = json.loads(Path(inspect_json).read_text(encoding="utf-8"))
    prefs = {"viz": viz, "engine": engine}
    if out is None:
        ts = int(time.time())
        out = f"scripts/analysis_{ts}.py"
    result = generate_script(inspect_payload, prefs, out_dir=str(Path(out).parent))
    if json_out:
        typer.echo(json.dumps(result))
    else:
        typer.echo(json.dumps({"scriptPath": result["scriptPath"]}))


@app.command()
def execute(
    script_path: str = typer.Option(..., "--script", help="Path to generated script"),
    aida_input: str = typer.Option(..., "--input", help="Path to input data file"),
    aida_output: str = typer.Option("artifacts", "--output", help="Artifacts dir"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON to stdout"),
) -> None:
    env = {"AIDA_INPUT": aida_input, "AIDA_OUTPUT": aida_output}
    result = execute_script(script_path, env=env, use_uv=True)
    payload = {"artifacts": result["artifacts"]}
    if json_out:
        typer.echo(json.dumps(payload))
    else:
        typer.echo(json.dumps(payload))


@app.command()
def analyze(
    file: str = typer.Option(..., "--file", help="Path to input data file"),
    format: str | None = typer.Option(None, "--format", help="csv|parquet|json|jsonl"),
    viz: str = typer.Option("plotly", "--viz", help="plotly|seaborn"),
    engine: str = typer.Option("pandas", "--engine", help="pandas|polars (future)"),
    out_dir: str = typer.Option("artifacts", "--out-dir", help="Artifacts dir"),
    rows: int = typer.Option(1000, "--rows", help="Preview/sample row count"),
    seed: int = typer.Option(42, "--seed", help="Deterministic sampling seed"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON to stdout"),
) -> None:
    tmp_inspect = Path(".aida/inspect.json")
    tmp_inspect.parent.mkdir(parents=True, exist_ok=True)

    # Inspect
    res: InspectResult = inspect_file(file, format=format, rows=rows, seed=seed)
    inspect_payload = {
        "schema": res.schema,
        "samplePreview": res.samplePreview,
        "stats": res.stats,
    }
    tmp_inspect.write_text(json.dumps(inspect_payload, indent=2), encoding="utf-8")

    # Generate
    gen = generate_script(
        inspect_payload, {"viz": viz, "engine": engine}, out_dir="scripts"
    )

    # Execute
    env = {"AIDA_INPUT": str(Path(file).resolve()), "AIDA_OUTPUT": out_dir}
    exec_result = execute_script(gen["scriptPath"], env=env, use_uv=True)
    payload = {"artifacts": exec_result["artifacts"]}

    if json_out:
        typer.echo(json.dumps(payload))
    else:
        typer.echo(json.dumps(payload))


def run() -> None:
    app()


if __name__ == "__main__":
    run()

