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

        # ── Surveillance endpoints ────────────────────────────────────────
        get_save_optional("/api/surveillance/overview")
        get_save_optional("/api/surveillance/changes?limit=200")
        providers_data = get_save_optional("/api/surveillance/providers")
        worklist_data = get_save_optional("/api/surveillance/worklist")
        get_save_optional("/api/surveillance/financial-impact")
        get_save_optional("/api/surveillance/quality-impact")
        get_save_optional("/api/surveillance/projections")
        get_save_optional("/api/surveillance/churn-analysis")

        if providers_data and isinstance(providers_data, list):
            for prov in providers_data:
                if isinstance(prov, dict) and prov.get("provider_npi"):
                    get_save_optional(f"/api/surveillance/providers/{prov['provider_npi']}")

        if worklist_data and isinstance(worklist_data, dict):
            for item in worklist_data.get("items", []):
                if isinstance(item, dict) and item.get("member_id"):
                    get_save_optional(f"/api/surveillance/worklist/{item['member_id']}")

        # ── Clinical endpoints ────────────────────────────────────────────
        schedule = get_save_optional("/api/clinical/schedule")
        get_save_optional("/api/clinical/week-summary")

        # Snapshot each day and each appointment brief + drilldowns
        if schedule and isinstance(schedule, dict):
            for day in schedule.get("days", []):
                if isinstance(day, dict) and day.get("date"):
                    get_save_optional(f"/api/clinical/schedule/{day['date']}")
                    for appt in day.get("appointments", []):
                        if not isinstance(appt, dict):
                            continue
                        aid = appt.get("appointment_id")
                        if not aid:
                            continue
                        brief = get_save_optional(f"/api/clinical/brief/{aid}")
                        if not brief or not isinstance(brief, dict):
                            continue
                        # Drilldown for each quality gap
                        for gap in brief.get("quality_gaps", []):
                            if isinstance(gap, dict) and gap.get("measure_id"):
                                get_save_optional(
                                    f"/api/clinical/brief/{aid}/drilldown/gap/{gap['measure_id']}"
                                )
                        # Drilldown for each HCC opportunity
                        for hcc in brief.get("hcc_opportunities", []):
                            if isinstance(hcc, dict) and hcc.get("hcc_category"):
                                get_save_optional(
                                    f"/api/clinical/brief/{aid}/drilldown/hcc/{hcc['hcc_category']}"
                                )
                        # Drilldown for attribution and cost
                        get_save_optional(f"/api/clinical/brief/{aid}/drilldown/attribution/attribution_risk")
                        get_save_optional(f"/api/clinical/brief/{aid}/drilldown/cost/cost_context")
                        # Drilldown for priority actions
                        for i, _action in enumerate(brief.get("priority_actions", []), start=1):
                            get_save_optional(
                                f"/api/clinical/brief/{aid}/drilldown/priority_action/{i}"
                            )

        # ── Code viewer snapshots ─────────────────────────────────────────
        for mod, fn in sorted(code_pairs):
            path = f"/api/code/{mod}/{fn}"
            try:
                get_save(path)
            except RuntimeError:
                print(f"WARN: skip code snapshot {path}", file=sys.stderr)

        write_json(
            OUT_DIR / "manifest.json",
            {"files": manifest, "metric_names": metric_names, "code_pairs": [list(p) for p in sorted(code_pairs)]},
        )

    print(f"Wrote snapshot to {OUT_DIR} ({len(manifest)} response files + manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
