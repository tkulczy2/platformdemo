#!/usr/bin/env python3
"""Export API JSON snapshots for GitHub Pages static demo (no running server required).

Runs the demo sequence via FastAPI TestClient, then writes GET responses to
frontend/public/gh-pages-snapshot/ using the same filename scheme as the frontend.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

# Repo root on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

OUT_DIR = ROOT / "frontend" / "public" / "gh-pages-snapshot"

# Dashboard + pipeline step shortcuts (see api/routes_drilldown.py)
CORE_METRIC_NAMES = [
    "attributed_population",
    "quality_composite",
    "actual_pmpm",
    "gross_savings",
    "shared_savings_amount",
    *[f"step_{i}" for i in range(1, 7)],
]


def url_to_snapshot_filename(method: str, url: str) -> str:
    """Match frontend snapshotPath(): path segments + sorted query abbreviations."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    key = "_".join(parts)
    q = parse_qs(parsed.query, keep_blank_values=True)
    items: list[tuple[str, str]] = []
    for k in sorted(q.keys()):
        v = q[k][0] if q[k] else ""
        short = "p" if k == "page" else "ps" if k == "page_size" else k
        items.append((short, v))
    if items:
        key += "_" + "_".join(f"{s}{v}" for s, v in items)
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", key)
    return f"{safe}.json"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def collect_code_refs_from_obj(obj: Any, out: set[tuple[str, str]]) -> None:
    """Gather (module, function) from nested code_references arrays."""

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            crs = x.get("code_references")
            if isinstance(crs, list):
                for cr in crs:
                    if isinstance(cr, dict) and "module" in cr and "function" in cr:
                        mod, fn = cr["module"], cr["function"]
                        if isinstance(mod, str) and isinstance(fn, str):
                            out.add((mod, fn))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)

    walk(obj)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, str] = {}

    def record(method: str, url: str) -> str:
        name = url_to_snapshot_filename(method, url)
        manifest[url] = name
        return name

    with TestClient(app) as client:
        assert client.post("/api/data/load-demo").status_code == 200
        assert client.post("/api/contract/load-demo").status_code == 200
        assert client.post("/api/calculate").status_code == 200
        assert client.post("/api/reconciliation/load-demo").status_code == 200
        assert client.post("/api/calculate").status_code == 200

        code_pairs: set[tuple[str, str]] = set()

        def get_save(path: str) -> Any:
            fname = record("GET", path)
            r = client.get(path)
            if r.status_code != 200:
                raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:500]}")
            data = r.json()
            write_json(OUT_DIR / fname, data)
            collect_code_refs_from_obj(data, code_pairs)
            return data

        def get_save_optional(path: str) -> Any | None:
            fname = record("GET", path)
            r = client.get(path)
            if r.status_code == 404:
                print(f"WARN: skip missing snapshot {path}", file=sys.stderr)
                del manifest[path]
                return None
            if r.status_code != 200:
                raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:500]}")
            data = r.json()
            write_json(OUT_DIR / fname, data)
            collect_code_refs_from_obj(data, code_pairs)
            return data

        get_save("/api/data/status")
        get_save("/api/contract")

        summary = get_save("/api/results/summary")

        step_rows = summary.get("steps") or []
        step_nums = [
            int(s["step_number"])
            for s in step_rows
            if isinstance(s, dict) and s.get("step_number") is not None
        ]
        if not step_nums:
            step_nums = [1, 2, 3, 4, 5]

        for step in step_nums:
            get_save(f"/api/results/step/{step}")

        recon = get_save("/api/reconciliation/summary")
        cat_dict = recon.get("categories") or {}
        if isinstance(cat_dict, dict):
            for category in cat_dict.keys():
                get_save(f"/api/reconciliation/detail/{category}")

        fm = summary.get("final_metrics") or {}
        qm = fm.get("quality_measures") or {}
        quality_names: list[str] = []
        if isinstance(qm, dict):
            quality_names = [f"quality_{k}" for k in qm.keys()]

        metric_names = list(dict.fromkeys([*CORE_METRIC_NAMES, *quality_names]))
        for m in metric_names:
            get_save_optional(f"/api/drilldown/metric/{m}")

        member_ids_for_cross_step: list[str] = []

        for step in step_nums:
            path = f"/api/drilldown/step/{step}/members?{urlencode({'page': 1, 'page_size': 50})}"
            data = get_save(path)
            members = data.get("members") or []
            page_ids: list[str] = []
            for row in members:
                if isinstance(row, dict) and row.get("member_id"):
                    page_ids.append(str(row["member_id"]))
            if step == 1:
                member_ids_for_cross_step = page_ids[:5]
            for mid in page_ids:
                get_save(f"/api/drilldown/step/{step}/member/{mid}")

        for mid in member_ids_for_cross_step:
            get_save(f"/api/drilldown/member/{mid}")

        for mod, fn in sorted(code_pairs):
            path = f"/api/code/{mod}/{fn}"
            try:
                get_save(path)
            except RuntimeError:
                # Optional introspection — skip if function renamed
                print(f"WARN: skip code snapshot {path}", file=sys.stderr)

        write_json(
            OUT_DIR / "manifest.json",
            {"files": manifest, "metric_names": metric_names, "code_pairs": [list(p) for p in sorted(code_pairs)]},
        )

    print(f"Wrote snapshot to {OUT_DIR} ({len(manifest)} response files + manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
