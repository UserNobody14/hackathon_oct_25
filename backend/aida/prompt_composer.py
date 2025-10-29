from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisPrefs:
    viz: str = "plotly"  # plotly | seaborn
    engine: str = "pandas"  # pandas | polars (future)
    max_charts: int = 8
    category_top_n: int = 30
    pairplot_max_numeric: int = 6
    correlation_min_numeric: int = 3
    top_corr_pairs: int = 5
    missingness_threshold: float = 0.05
    prefer_interactive: bool = True
    target: str | None = None
    time_col: str | None = None
    geospatial_enabled: bool = True
    lat_col: str | None = None
    lon_col: str | None = None
    location_col: str | None = None
    geo_scope: str | None = None


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
    sample_preview = inspect.get("samplePreview", [])[:5]
    system = (
        "You are an expert data scientist. Generate ONE self-contained Python 3.12 script that:\n"
        "- Imports only: os, json, pathlib.Path, numpy, pandas, and a single viz lib (plotly.express if prefs.viz=plotly else seaborn+matplotlib). Set numpy.random.seed(42).\n"
        "- IO: read input path from env AIDA_INPUT; write HTML/PNG artifacts to dir from AIDA_OUTPUT. Name files deterministically and descriptively.\n"
        "- Robustness requirements (MANDATORY):\n"
        "  * Wrap chart generation in try/except; skip failing plots but continue.\n"
        "  * Handle ImportError for viz libs: if plotly import fails, set px=None; if seaborn/matplotlib imports fail, skip those plots.\n"
        "  * Always create at least the overall describe HTML report.\n"
        "  * Never print anything except a single JSON object AS THE LAST LINE of stdout.\n"
        '  * In a finally block, print json.dumps({"artifacts": [...]}) on one line. Only include files that actually exist.\n'
        "- Chart selection rubric (choose up to prefs.max_charts, highest value first):\n"
        "  1) Time series: if a datetime-like column exists (prefs.time_col or inferred), plot line charts of key numeric metrics over time; resample sensibly if very long.\n"
        "  2) Numeric distributions: for each major numeric column, histogram with smart bins (log-scale if highly skewed); add KDE if seaborn; add boxplot for outliers.\n"
        "  3) Numeric vs numeric correlations: compute Pearson correlations among numeric columns (use Spearman if heavy tails or monotonic non-linear). Include a correlation heatmap when count(numeric) >= prefs.correlation_min_numeric. Identify the top prefs.top_corr_pairs absolute-value pairs (exclude duplicates/self-pairs) and create scatter plots for each; use alpha blending for dense data; annotate plot titles with the correlation coefficient.\n"
        "  4) Categorical distributions: bar charts of value counts for top prefs.category_top_n; include percent labels; truncate labels safely.\n"
        "  5) Numeric by category: box/violin or aggregated bar (mean ± std) for low-cardinality categoricals.\n"
        "  6) Two categoricals (both low-cardinality): grouped/stacked bar or heatmap of the contingency table.\n"
        "  7) Missingness: if any column has missing ratio >= prefs.missingness_threshold, include a missingness bar by column.\n"
        "  8) Geospatial (if prefs.geospatial_enabled):\n"
        "     - If columns resembling latitude/longitude exist (prefs.lat_col/prefs.lon_col or inferred by name), plot geographic scatter.\n"
        "       * If viz=plotly: prefer px.scatter_geo with scope from prefs.geo_scope when provided; set hover names/labels when available.\n"
        "       * If viz=seaborn/matplotlib: fallback to a simple lon vs lat scatter with appropriate aspect ratio and bounds.\n"
        "     - If a location code column exists (prefs.location_col or inferred like country/iso/state), aggregate counts and draw a choropleth when using plotly (skip otherwise).\n"
        "- Prefer interactive HTML when prefs.prefer_interactive and viz=plotly; otherwise save static PNGs.\n"
        "- Always include an overall describe table (HTML). Titles/axes must be clear and human-friendly.\n"
        '- At the end, print ONLY a JSON object to stdout of the form {"artifacts":[{"type":"html","path":"...","title":"..."}]} (no markdown, no extra text). Do not include triple backticks or markdown fences.'
    )
    user = (
        "Generate the script now. Preferences and context:\n"
        f"prefs={prefs.__dict__}\n"
        f"Schema (name:type): {schema}\n"
        f"Stats: {stats}\n"
        f"Sample preview (first {len(sample_preview)} rows): {sample_preview}\n"
        "If file type depends on extension, support csv/parquet/json/jsonl by extension."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
