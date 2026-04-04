"""Attribution Surveillance API endpoints."""

import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from api.main import state, _fix_values

router = APIRouter(prefix="/api/surveillance", tags=["surveillance"])

_surveillance_engine = None
_surveillance_result = None

HISTORY_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "attribution_history.json"
SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"
CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "contracts"


def _get_result():
    global _surveillance_engine, _surveillance_result
    if _surveillance_result is not None:
        return _surveillance_result

    if state.pipeline_result is None:
        raise HTTPException(400, "Pipeline has not been run. Run calculation first.")

    if not HISTORY_PATH.exists():
        raise HTTPException(
            404, "Attribution history not generated. Run: python -m generator.attribution_history"
        )

    history = json.load(open(HISTORY_PATH))

    contract = state.contract
    if contract is None:
        contract_path = CONTRACTS_DIR / "sample_mssp_contract.json"
        with open(contract_path) as f:
            contract = json.load(f)

    schedule = None
    if SCHEDULE_PATH.exists():
        with open(SCHEDULE_PATH) as f:
            schedule = json.load(f)

    from engine.surveillance_engine import SurveillanceEngine

    _surveillance_engine = SurveillanceEngine(history, state.pipeline_result, contract, schedule)
    _surveillance_result = _surveillance_engine.analyze()
    return _surveillance_result


def _serialize(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return _fix_values(asdict(obj))
    return obj


@router.get("/overview")
def get_overview():
    """High-level panel overview with 12-month trend."""
    sr = _get_result()
    jan = sr.monthly_snapshots[0] if sr.monthly_snapshots else None
    dec = sr.monthly_snapshots[-1] if sr.monthly_snapshots else None

    return {
        "current_attributed": sr.current_attributed_count,
        "current_at_risk": sr.current_at_risk_count,
        "current_financial_exposure": sr.current_financial_exposure,
        "monthly_snapshots": [_serialize(s) for s in sr.monthly_snapshots],
        "churn_by_quarter": sr.churn_by_quarter,
        "net_change_ytd": (dec.total_attributed - jan.total_attributed) if jan and dec else 0,
        "net_change_pct_ytd": round(
            (dec.total_attributed - jan.total_attributed) / jan.total_attributed, 4
        ) if jan and dec and jan.total_attributed > 0 else 0,
        "narrative_markers": sr.narrative_markers,
    }


@router.get("/changes")
def get_changes(
    month: str | None = None,
    classification: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Change events, optionally filtered by month and/or classification."""
    sr = _get_result()
    events = sr.change_events

    if month:
        events = [e for e in events if e.event_month == month]
    if classification:
        events = [e for e in events if e.change_classification == classification]

    total = len(events)
    paged = events[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": [_serialize(e) for e in paged],
    }


@router.get("/providers")
def get_providers():
    """Provider panel summaries for all PCPs."""
    sr = _get_result()
    return [_serialize(p) for p in sr.provider_panels]


@router.get("/providers/{npi}")
def get_provider_detail(npi: str):
    """Detailed panel info for a single provider."""
    sr = _get_result()

    panel = None
    for p in sr.provider_panels:
        if p.provider_npi == npi:
            panel = p
            break
    if panel is None:
        raise HTTPException(404, f"Provider {npi} not found")

    # Filter change events for this provider
    events = [
        e for e in sr.change_events
        if (e.prior_provider and e.prior_provider.get("npi") == npi)
        or (e.new_provider and e.new_provider.get("npi") == npi)
    ]

    # Filter worklist for this provider
    at_risk = [
        w for w in sr.retention_worklist
        if w.attributed_provider.get("npi") == npi
    ]

    return {
        "provider": _serialize(panel),
        "change_events": [_serialize(e) for e in events],
        "at_risk_members": [_serialize(w) for w in at_risk],
    }


@router.get("/worklist")
def get_worklist(
    urgency: str | None = None,
    provider_npi: str | None = None,
    min_roi: float | None = None,
    has_appointment: bool | None = None,
):
    """Retention worklist sorted by ROI."""
    sr = _get_result()
    items = sr.retention_worklist

    if urgency:
        items = [w for w in items if w.urgency == urgency]
    if provider_npi:
        items = [w for w in items if w.attributed_provider.get("npi") == provider_npi]
    if min_roi is not None:
        items = [w for w in items if w.roi_estimate >= min_roi]
    if has_appointment is not None:
        items = [w for w in items if w.has_upcoming_appointment == has_appointment]

    total_exposure = sum(w.financial_impact_if_lost["total"] for w in items)
    total_cost = sum(w.intervention_cost_estimate for w in items)
    total_recovery = sum(
        w.financial_impact_if_lost["total"] * w.recovery_probability for w in items
    )

    return {
        "total": len(items),
        "summary": {
            "total_financial_exposure": round(total_exposure, 2),
            "total_intervention_cost": round(total_cost, 2),
            "total_potential_recovery": round(total_recovery, 2),
            "aggregate_roi": round(total_recovery / total_cost, 2) if total_cost > 0 else 0,
        },
        "items": [_serialize(w) for w in items],
    }


@router.get("/worklist/{member_id}")
def get_worklist_member(member_id: str):
    """Detailed retention info for a single member."""
    sr = _get_result()

    item = None
    for w in sr.retention_worklist:
        if w.member_id == member_id:
            item = w
            break
    if item is None:
        raise HTTPException(404, f"Member {member_id} not in retention worklist")

    # Attribution history for this member
    history = json.load(open(HISTORY_PATH))
    member_history = []
    for snap in history.get("snapshots", []):
        status = "not_attributed"
        provider = None
        for m in snap["members"]:
            if m["member_id"] == member_id:
                status = "attributed"
                provider = {"npi": m["attributed_provider_npi"], "name": m["attributed_provider_name"]}
                break
        member_history.append({
            "month": snap["month"],
            "status": status,
            "provider": provider,
        })

    # Change events for this member
    events = [e for e in sr.change_events if e.member_id == member_id]

    # Cross-tab links
    clinical_link = None
    if item.has_upcoming_appointment:
        clinical_link = f"/clinical"

    recon_link = None
    for d in sr.settlement_attribution_discrepancies:
        if member_id in str(d):
            recon_link = f"/reconciliation"
            break

    return {
        "member": _serialize(item),
        "attribution_history": member_history,
        "change_events": [_serialize(e) for e in events],
        "clinical_brief_link": clinical_link,
        "reconciliation_link": recon_link,
    }


@router.get("/projections")
def get_projections():
    """Three projection scenarios."""
    sr = _get_result()
    return [_serialize(p) for p in sr.projections]


@router.get("/quality-impact")
def get_quality_impact():
    """Quality impact summary."""
    sr = _get_result()
    return sr.quality_impact_summary


@router.get("/financial-impact")
def get_financial_impact():
    """Financial impact breakdown."""
    sr = _get_result()
    worklist = sr.retention_worklist

    total_at_risk = sum(w.financial_impact_if_lost["total"] for w in worklist)
    total_cost = sum(w.intervention_cost_estimate for w in worklist)
    total_recovery = sum(
        w.financial_impact_if_lost["total"] * w.recovery_probability for w in worklist
    )

    cumulative_monthly = []
    running = 0.0
    for s in sr.monthly_snapshots:
        running += abs(s.cumulative_financial_impact - running) if cumulative_monthly else s.cumulative_financial_impact
        cumulative_monthly.append({
            "month": s.month,
            "cumulative_impact": s.cumulative_financial_impact,
        })

    return {
        "by_classification": sr.churn_by_classification,
        "by_quarter": sr.churn_by_quarter,
        "cumulative_monthly": cumulative_monthly,
        "total_at_risk": round(total_at_risk, 2),
        "total_intervention_cost": round(total_cost, 2),
        "total_potential_recovery": round(total_recovery, 2),
        "aggregate_roi": round(total_recovery / total_cost, 2) if total_cost > 0 else 0,
    }


@router.get("/churn-analysis")
def get_churn_analysis():
    """Cohort-level churn analytics."""
    sr = _get_result()

    by_provider = []
    for p in sr.provider_panels:
        if p.churn_rate_annualized > 0:
            by_provider.append({
                "npi": p.provider_npi,
                "name": p.provider_name,
                "churn_rate": p.churn_rate_annualized,
                "losses": p.jan_panel_size - p.current_panel_size if p.jan_panel_size > p.current_panel_size else 0,
            })

    seasonal_pattern = [
        {"month": s.month, "churn_rate": s.churn_rate}
        for s in sr.monthly_snapshots
    ]

    return {
        "by_classification": sr.churn_by_classification,
        "by_quarter": sr.churn_by_quarter,
        "by_provider": sorted(by_provider, key=lambda x: x["churn_rate"], reverse=True),
        "seasonal_pattern": seasonal_pattern,
    }
