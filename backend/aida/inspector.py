from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class InspectResult:
    schema: dict[str, str]
    samplePreview: list[dict[str, object]]
    stats: dict[str, object]


SUPPORTED_FORMATS: set[str] = {"csv", "parquet", "json", "jsonl"}


def _detect_format(path: Path, provided_format: str | None) -> str:
    if provided_format:
        fmt = provided_format.lower()
        if fmt == "jsonl":
            return "jsonl"
        if fmt in SUPPORTED_FORMATS:
            return fmt
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"parquet", "pq"}:
        return "parquet"
    if suffix in {"jsonl", "ndjson"}:
        return "jsonl"
    if suffix == "json":
        return "json"
    return "csv"


def _pandas_dtype_to_str(dtype: pd.api.types.ExtensionDtype | np.dtype) -> str:
    # Normalize pandas/numpy dtype names to simple strings
    return str(dtype)


def _infer_schema(df: pd.DataFrame) -> dict[str, str]:
    return {col: _pandas_dtype_to_str(dtype) for col, dtype in df.dtypes.items()}


def _count_rows_csv(path: Path) -> int:
    # Fast-ish line count minus header
    with path.open("rb") as f:
        num_lines = sum(1 for _ in f)
    return max(0, num_lines - 1)


def _count_rows_jsonl(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for _ in f)


def _count_rows_parquet(path: Path) -> int:
    try:
        import pyarrow.parquet as pq  # type: ignore

        return int(pq.ParquetFile(str(path)).metadata.num_rows)
    except Exception:
        # Fallback: load to pandas and count; may be expensive but should succeed
        return int(pd.read_parquet(path).shape[0])


def _count_rows_json(path: Path) -> int:
    # Supports JSON array files only; for large files this will be expensive
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, list):
            return len(obj)
        if isinstance(obj, dict):
            # If dict of lists, choose the max length
            lens = [len(v) for v in obj.values() if isinstance(v, list)]
            return max(lens) if lens else 0
        return 0
    except Exception:
        return 0


def _sample_csv(path: Path, rows: int, seed: int) -> pd.DataFrame:
    # Deterministic sample: prefer head for performance and determinism
    # Advanced: could implement reservoir sampling without loading full file.
    return pd.read_csv(path, nrows=rows)


def _sample_parquet(path: Path, rows: int) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df.head(rows)


def _sample_jsonl(path: Path, rows: int) -> pd.DataFrame:
    # Read first N lines deterministically
    import itertools

    with path.open("r", encoding="utf-8") as f:
        lines: Iterable[str] = itertools.islice(f, rows)
        # pandas can read a list of json lines
        records = [json.loads(line) for line in lines if line.strip()]
    return pd.DataFrame(records)


def _sample_json(path: Path, rows: int) -> pd.DataFrame:
    # For JSON arrays or objects of arrays
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, list):
        return pd.DataFrame(obj[:rows])
    if isinstance(obj, dict):
        return pd.DataFrame(obj).head(rows)
    return pd.DataFrame()


def inspect_file(
    path: str | os.PathLike[str],
    format: str | None = None,
    rows: int = 1000,
    seed: int = 42,
) -> InspectResult:
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    fmt = _detect_format(p, format)

    if fmt == "csv":
        df = _sample_csv(p, rows=rows, seed=seed)
        row_count = _count_rows_csv(p)
    elif fmt == "parquet":
        df = _sample_parquet(p, rows=rows)
        row_count = _count_rows_parquet(p)
    elif fmt == "jsonl":
        df = _sample_jsonl(p, rows=rows)
        row_count = _count_rows_jsonl(p)
    elif fmt == "json":
        df = _sample_json(p, rows=rows)
        row_count = _count_rows_json(p)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    schema = _infer_schema(df)
    sample_preview = df.head(rows).to_dict(orient="records")
    stats: dict[str, object] = {
        "rowCount": int(row_count),
        "previewRowCount": int(len(sample_preview)),
        "format": fmt,
    }

    return InspectResult(schema=schema, samplePreview=sample_preview, stats=stats)

