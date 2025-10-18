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

