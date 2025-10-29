from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterable


def _iter_html_artifacts(output_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for path in output_dir.glob("*.html"):
        title = path.stem.replace("_", " ").title()
        artifacts.append({"type": "html", "path": str(path), "title": title})
    return artifacts


def execute_script(
    script_path: str | os.PathLike[str],
    env: dict[str, str] | None = None,
    use_uv: bool = True,
    timeout: int | None = None,
) -> dict:
    script = Path(script_path).resolve()
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    output_dir = Path(merged_env.get("AIDA_OUTPUT", "artifacts")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd: list[str]
    if use_uv:
        cmd = ["uv", "run", "python", str(script)]
    else:
        cmd = ["python", str(script)]

    proc = subprocess.run(
        cmd,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )

    # Parse artifacts from script stdout - no fallback to directory scanning
    artifacts: list[dict] = []
    try:
        last_line = proc.stdout.strip().splitlines()[-1] if proc.stdout else ""
        parsed = json.loads(last_line)
        artifacts = parsed.get("artifacts", []) if isinstance(parsed, dict) else []
    except Exception as e:
        # No fallback - require proper JSON output from generated scripts
        error_msg = (
            f"Generated script did not produce valid artifacts JSON output.\n"
            f"Expected last line of stdout to be JSON with 'artifacts' array.\n"
            f"Parse error: {e}\n"
            f"Script stdout: {proc.stdout[:500] if proc.stdout else '(empty)'}"
        )
        raise RuntimeError(error_msg)

    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "artifacts": artifacts,
    }
    if proc.returncode != 0:
        # Provide helpful error while still returning any artifacts
        raise RuntimeError(json.dumps(result))
    return result
