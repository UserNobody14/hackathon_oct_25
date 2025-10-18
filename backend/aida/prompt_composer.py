from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisPrefs:
    viz: str = "plotly"  # plotly | seaborn
    engine: str = "pandas"  # pandas | polars (future)


def build_prompt(inspect: dict, prefs: AnalysisPrefs) -> dict:
    # Structured prompt-like payload; deterministic and explicit.
    return {
        "task": "Generate a deterministic EDA script.",
        "constraints": {
            "determinism": {
                "numpy_seed": 42,
                "random_seed": 42,
            },
            "io": {
                "input_env": "AIDA_INPUT",
                "output_env": "AIDA_OUTPUT",
            },
        },
        "prefs": {
            "viz": prefs.viz,
            "engine": prefs.engine,
        },
        "data": {
            "schema": inspect.get("schema", {}),
            "stats": inspect.get("stats", {}),
        },
    }


def build_messages(inspect: dict, prefs: AnalysisPrefs) -> list[dict[str, str]]:
    schema = inspect.get("schema", {})
    stats = inspect.get("stats", {})
    system = (
        "You are an expert data scientist. Generate a SINGLE self-contained Python script that:\n"
        "- Uses Python 3.12 and only imports: os, json, pathlib.Path, numpy, pandas, and one viz library (plotly.express if prefs.viz=plotly else seaborn+matplotlib).\n"
        "- Reads input file path from env AIDA_INPUT and writes HTML/PNG artifacts into directory from env AIDA_OUTPUT.\n"
        "- Sets deterministic seeds (numpy.random.seed(42)).\n"
        "- Creates multiple EDA outputs: overall describe table (HTML), histograms for numeric columns, bar charts for categorical columns (top 30), and an optional correlation heatmap if 2+ numeric cols.\n"
        "- Saves each artifact to the output dir with clear filenames.\n"
        '- At the end, print ONLY a JSON object to stdout of the form {"artifacts":[{"type":"html","path":"...","title":"..."}]} (no markdown, no extra text).\n'
        "- Do not include triple backticks or markdown fences."
    )
    user = (
        "Generate the script now. Preferences and context:\n"
        f"viz={prefs.viz}; engine={prefs.engine}.\n"
        f"Schema (name:type): {schema}.\n"
        f"Stats: {stats}.\n"
        "If file type depends on extension, support csv/parquet/json/jsonl by extension."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
