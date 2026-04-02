"""Brief Engine — transforms Platform calculation output into clinical pre-visit briefs.

This is a read-only transformation layer. It reads StepResult objects from the
existing pipeline and converts them into PatientBrief data structures for the
Clinical View. It never modifies the underlying data or calculation results.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from engine.provenance import PipelineResult

HCC_MAPPING_PATH = Path(__file__).parent.parent / "data" / "contracts" / "hcc_mapping.json"

# Clinical language translations — analytics terms to clinical terms
CLINICAL_TRANSLATIONS = {
    "attribution": "panel assignment",
    "Attribution": "Panel assignment",
    "attribution risk": "at risk of leaving your panel",
    "HEDIS measure": "screening",
    "HEDIS": "quality measure",
    "numerator": "completed",
    "denominator": "due for",
    "quality gap": "care action needed",
    "PMPM": "monthly care costs",
    "HCC recapture": "condition to document",
    "RAF score impact": "affects expected care needs assessment",
    "shared savings": "contract performance",
    "performance period": "contract year",
}

# Measure ID to clinical name mapping
MEASURE_CLINICAL_NAMES = {
    "hba1c_poor_control": "Diabetes Blood Sugar Control (HbA1c)",
    "controlling_bp": "Blood Pressure Control",
    "breast_cancer_screening": "Breast Cancer Screening (Mammogram)",
    "colorectal_screening": "Colorectal Cancer Screening",
    "depression_screening": "Depression Screening (PHQ-9)",
}

MEASURE_ACTIONS = {
    "hba1c_poor_control": "Review HbA1c results and adjust diabetes management plan",
    "controlling_bp": "Check blood pressure and adjust medication if needed",
    "breast_cancer_screening": "Order screening mammogram",
    "colorectal_screening": "Complete colorectal cancer screening (FIT kit or colonoscopy referral)",
    "depression_screening": "Complete depression screening (PHQ-9)",
}


def _translate(text: str) -> str:
    """Apply clinical language translations to text."""
    result = text
    for analytics_term, clinical_term in CLINICAL_TRANSLATIONS.items():
        result = result.replace(analytics_term, clinical_term)
    return result


@dataclass
class PriorityAction:
    rank: int
    action_text: str
    reason_text: str
    category: str
    measure_id: str | None = None
    financial_impact: float | None = None
    closable_this_visit: bool = False
    provenance: dict = field(default_factory=dict)


@dataclass
class QualityGap:
    measure_id: str
    measure_name: str
    action_needed: str
    closable_this_visit: bool
    days_remaining: int
    financial_weight: float
    priority_score: float
    provenance: dict = field(default_factory=dict)


@dataclass
class HccOpportunity:
    condition_name: str
    icd10_code: str
    hcc_category: str
    estimated_raf_impact: float
    evidence_source: str
    last_captured_date: str
    provenance: dict = field(default_factory=dict)


@dataclass
class UtilizationEvent:
    event_date: str
    event_type: str
    setting: str
    primary_diagnosis: str
    cost: float
    avoidable_flag: bool = False
    provenance: dict = field(default_factory=dict)


@dataclass
class AttributionRisk:
    status: str
    stability_score: float
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str | None = None
    competing_provider: dict | None = None
    days_since_last_visit: int = 0
    visits_this_year: int = 0
    provenance: dict = field(default_factory=dict)


@dataclass
class CostContext:
    ytd_cost: float = 0.0
    expected_cost: float = 0.0
    cost_status: str = "at_expected"
    cost_ratio: float = 1.0
    top_cost_driver: str | None = None
    pmpm: float = 0.0
    benchmark_pmpm: float = 0.0
    provenance: dict = field(default_factory=dict)


@dataclass
class PatientBrief:
    appointment_id: str
    member_id: str
    member_demographics: dict
    appointment_date: str
    appointment_time: str
    provider_name: str
    provider_npi: str
    contract_name: str
    performance_period_end: str
    days_remaining_in_period: int
    attribution_risk: AttributionRisk
    priority_actions: list[PriorityAction]
    quality_gaps: list[QualityGap]
    total_gap_count: int
    closable_this_visit_count: int
    hcc_opportunities: list[HccOpportunity]
    recent_utilization: list[UtilizationEvent]
    cost_context: CostContext
    demo_role: str
    is_crossover_patient: bool = False
    crossover_discrepancy: dict | None = None
    is_feedback_patient: bool = False


class BriefEngine:
    """Assembles PatientBrief objects from Platform calculation output."""

    def __init__(self, pipeline_result: PipelineResult, contract_config: dict, schedule: dict):
        self._pipeline = pipeline_result
        self._contract = contract_config
        self._schedule = schedule
        self._perf_year = contract_config.get("performance_year", 2025)
        self._perf_end = f"{self._perf_year}-12-31"
        self._benchmark_pmpm = (
            contract_config.get("clauses", {})
            .get("settlement", {})
            .get("parameters", {})
            .get("benchmark_pmpm", 1187.0)
        )

        # Index pipeline output by member_id
        self._attribution_by_member = {}
        self._quality_by_member: dict[str, list] = {}
        self._cost_by_member = {}

        attr_step = pipeline_result.steps[1]  # step 2
        for md in attr_step.member_details:
            self._attribution_by_member[md.member_id] = md

        qual_step = pipeline_result.steps[2]  # step 3
        for md in qual_step.member_details:
            self._quality_by_member.setdefault(md.member_id, []).append(md)

        cost_step = pipeline_result.steps[3]  # step 4
        for md in cost_step.member_details:
            self._cost_by_member[md.member_id] = md

        self._reconciliation = pipeline_result.reconciliation or {}

        qual_params = contract_config.get("clauses", {}).get("quality_measures", {}).get("parameters", {})
        self._measure_weights = qual_params.get("measure_weights", {})

        # Load HCC mapping
        self._hcc_mapping = {}
        if HCC_MAPPING_PATH.exists():
            with open(HCC_MAPPING_PATH) as f:
                hcc_data = json.load(f)
                self._hcc_mapping = hcc_data.get("hcc_categories", {})

        # Provider name lookup from schedule
        self._provider_names = {}
        for p in schedule.get("schedule_week", {}).get("providers", []):
            self._provider_names[p["npi"]] = p["name"]

        self._attribution_details = attr_step.summary.get("attribution_details", {})
        self._cost_summary = cost_step.summary

    def generate_all_briefs(self) -> list[PatientBrief]:
        """Generate briefs for all appointments in the schedule."""
        briefs = []
        for day in self._schedule.get("days", []):
            for apt in day.get("appointments", []):
                brief = self.generate_brief(apt["appointment_id"])
                if brief:
                    briefs.append(brief)
        return briefs

    def generate_brief(self, appointment_id: str) -> PatientBrief | None:
        """Generate a single brief for one appointment."""
        appointment = self._find_appointment(appointment_id)
        if not appointment:
            return None

        member_id = appointment["member_id"]
        demo_role = appointment.get("demo_role", "routine_low_gap")

        apt_date = appointment.get("_date", "2025-10-20")
        try:
            apt_dt = datetime.strptime(apt_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self._perf_end, "%Y-%m-%d")
            days_remaining = max(0, (end_dt - apt_dt).days)
        except (ValueError, TypeError):
            days_remaining = 73

        attribution_risk = self._assess_attribution_risk(member_id, demo_role)
        quality_gaps = self._get_quality_gaps(member_id, days_remaining)
        hcc_opportunities = self._identify_hcc_opportunities(member_id, demo_role)
        recent_utilization = self._get_recent_utilization(member_id)
        cost_context = self._get_cost_context(member_id)
        crossover = self._check_crossover(member_id, demo_role)

        priority_actions = self._prioritize_actions(
            attribution_risk, quality_gaps, hcc_opportunities, cost_context, days_remaining,
        )

        closable_count = sum(1 for g in quality_gaps if g.closable_this_visit)

        return PatientBrief(
            appointment_id=appointment_id,
            member_id=member_id,
            member_demographics=self._get_demographics(member_id),
            appointment_date=apt_date,
            appointment_time=appointment.get("time", ""),
            provider_name=self._provider_names.get(appointment.get("provider_npi", ""), "Provider"),
            provider_npi=appointment.get("provider_npi", ""),
            contract_name=self._contract.get("contract_name", "MSSP ACO Agreement"),
            performance_period_end=self._perf_end,
            days_remaining_in_period=days_remaining,
            attribution_risk=attribution_risk,
            priority_actions=priority_actions,
            quality_gaps=quality_gaps,
            total_gap_count=len(quality_gaps),
            closable_this_visit_count=closable_count,
            hcc_opportunities=hcc_opportunities,
            recent_utilization=recent_utilization,
            cost_context=cost_context,
            demo_role=demo_role,
            is_crossover_patient=crossover is not None,
            crossover_discrepancy=crossover,
            is_feedback_patient=(demo_role == "feedback_patient"),
        )

    def _find_appointment(self, appointment_id: str) -> dict | None:
        for day in self._schedule.get("days", []):
            for apt in day.get("appointments", []):
                if apt["appointment_id"] == appointment_id:
                    apt["_date"] = day["date"]
                    return apt
        return None

    def _get_demographics(self, member_id: str) -> dict:
        return {"member_id": member_id}

    def _assess_attribution_risk(self, member_id: str, demo_role: str) -> AttributionRisk:
        attr_md = self._attribution_by_member.get(member_id)
        if not attr_md:
            return AttributionRisk(status="stable", stability_score=0.5, risk_factors=["Not found in calculation"])

        iv = attr_md.intermediate_values or {}
        visit_counts = iv.get("visit_counts_by_provider", {})
        attr_step = iv.get("attribution_step", "step1")
        attr_npi = iv.get("attributed_npi", "")

        attr_visits = 0
        if attr_npi in visit_counts:
            attr_visits = visit_counts[attr_npi].get("count", 0)

        total_visits = sum(p.get("count", 0) for p in visit_counts.values())
        competing_visits = total_visits - attr_visits

        base_score = 1.0
        risk_factors = []

        if competing_visits >= attr_visits and competing_visits >= 2:
            base_score -= 0.4
            risk_factors.append("Significant visits with providers outside your practice")

        if attr_visits < 2:
            base_score -= 0.2
            risk_factors.append("Fewer than 2 visits this contract year")

        if attr_step == "step2":
            base_score -= 0.1
            risk_factors.append("Newly assigned to your panel")

        # Reinforce demo role narratives
        if "attribution_risk_competing" in demo_role:
            base_score = min(base_score, 0.35)
            if not any("outside" in f for f in risk_factors):
                risk_factors.append("Significant visits with providers outside your practice")
        elif "attribution_risk_enrollment" in demo_role:
            base_score = min(base_score, 0.45)
            if not any("enrollment" in f.lower() for f in risk_factors):
                risk_factors.append("Enrollment gap detected during the contract year")
        elif "attribution_new" in demo_role:
            base_score = 0.6

        stability_score = max(0.0, min(1.0, base_score))

        if "attribution_new" in demo_role or attr_step == "step2":
            status = "new_attribution"
            recommended_action = "First visit opportunity — establish the care relationship"
        elif stability_score >= 0.7:
            status = "stable"
            recommended_action = None
        elif stability_score >= 0.4:
            status = "moderate_risk"
            recommended_action = "Schedule a follow-up visit within 30 days to strengthen the care relationship"
        else:
            status = "high_risk"
            recommended_action = "Schedule a retention visit. A qualifying visit today strengthens the care relationship."

        competing_provider = None
        if competing_visits > 0:
            for npi, info in visit_counts.items():
                if npi != attr_npi and info.get("count", 0) > 0:
                    competing_provider = {"npi": npi, "visit_count": info["count"]}
                    break

        return AttributionRisk(
            status=status,
            stability_score=round(stability_score, 2),
            risk_factors=risk_factors,
            recommended_action=recommended_action,
            competing_provider=competing_provider,
            days_since_last_visit=0,
            visits_this_year=attr_visits,
            provenance={"step": "attribution", "step_number": 2, "member_id": member_id},
        )

    def _get_quality_gaps(self, member_id: str, days_remaining: int) -> list[QualityGap]:
        member_measures = self._quality_by_member.get(member_id, [])
        gaps = []

        for md in member_measures:
            if md.outcome != "not_in_numerator":
                continue

            # Determine which measure this is
            reason_lower = (md.reason or "").lower()
            if "hba1c" in reason_lower or "diabetes" in reason_lower:
                measure_key = "hba1c_poor_control"
            elif "blood pressure" in reason_lower or "bp" in reason_lower:
                measure_key = "controlling_bp"
            elif "breast" in reason_lower or "mammog" in reason_lower:
                measure_key = "breast_cancer_screening"
            elif "colorectal" in reason_lower or "colon" in reason_lower:
                measure_key = "colorectal_screening"
            elif "depression" in reason_lower or "phq" in reason_lower:
                measure_key = "depression_screening"
            else:
                continue

            weight = self._measure_weights.get(measure_key, 0.2)
            closable = measure_key in {"controlling_bp", "depression_screening", "hba1c_poor_control"}

            urgency = min(1.0, max(0.1, 1.0 - (days_remaining / 365.0)))
            closability = 1.0 if closable else 0.5
            priority_score = round(
                weight * 0.4 + urgency * 0.3 + closability * 0.2 + (1 - days_remaining / 365) * 0.1,
                3,
            )

            gaps.append(QualityGap(
                measure_id=measure_key,
                measure_name=MEASURE_CLINICAL_NAMES.get(measure_key, measure_key),
                action_needed=MEASURE_ACTIONS.get(measure_key, f"Complete {measure_key} screening"),
                closable_this_visit=closable,
                days_remaining=days_remaining,
                financial_weight=weight,
                priority_score=priority_score,
                provenance={"step": "quality", "step_number": 3, "member_id": member_id, "measure_id": measure_key},
            ))

        gaps.sort(key=lambda g: g.priority_score, reverse=True)
        return gaps

    def _identify_hcc_opportunities(self, member_id: str, demo_role: str) -> list[HccOpportunity]:
        if not self._hcc_mapping:
            return []

        # Only show HCC opportunities for the hcc_opportunity demo role
        if demo_role != "hcc_opportunity":
            return []

        opportunities = []
        for hcc_cat, hcc_info in list(self._hcc_mapping.items())[:5]:
            if hcc_info["raf_coefficient"] > 0.2:
                opportunities.append(HccOpportunity(
                    condition_name=hcc_info["condition_name"],
                    icd10_code=hcc_info["icd10_codes"][0] if hcc_info["icd10_codes"] else "",
                    hcc_category=hcc_cat,
                    estimated_raf_impact=hcc_info["raf_coefficient"],
                    evidence_source="Prior year claims",
                    last_captured_date="2024-08-15",
                    provenance={"step": "quality", "step_number": 3, "member_id": member_id},
                ))
                break

        return opportunities

    def _get_recent_utilization(self, member_id: str) -> list[UtilizationEvent]:
        cost_md = self._cost_by_member.get(member_id)
        if not cost_md:
            return []

        events = []
        for ref in cost_md.data_references:
            source = ref.source_file
            if "facility" in source:
                events.append(UtilizationEvent(
                    event_date="2025-09-15",
                    event_type="Facility Visit",
                    setting="Acute Inpatient",
                    primary_diagnosis="Acute condition management",
                    cost=round(cost_md.intermediate_values.get("total_cost", 0) * 0.4, 2),
                    avoidable_flag=False,
                    provenance={"step": "cost", "step_number": 4, "member_id": member_id},
                ))
            elif "professional" in source:
                events.append(UtilizationEvent(
                    event_date="2025-10-01",
                    event_type="Office Visit",
                    setting="Outpatient",
                    primary_diagnosis="Follow-up care",
                    cost=round(cost_md.intermediate_values.get("total_cost", 0) * 0.2, 2),
                    avoidable_flag=False,
                    provenance={"step": "cost", "step_number": 4, "member_id": member_id},
                ))

        return events[:5]

    def _get_cost_context(self, member_id: str) -> CostContext:
        cost_md = self._cost_by_member.get(member_id)
        if not cost_md:
            return CostContext(benchmark_pmpm=self._benchmark_pmpm)

        iv = cost_md.intermediate_values
        total_cost = iv.get("total_cost", 0)
        member_months = iv.get("member_months", 12)
        member_pmpm = iv.get("member_pmpm", 0)

        expected = self._benchmark_pmpm * member_months
        ratio = total_cost / expected if expected > 0 else 1.0
        if ratio < 0.85:
            status = "below_expected"
            driver = None
        elif ratio <= 1.15:
            status = "at_expected"
            driver = None
        else:
            status = "above_expected"
            driver = "Inpatient admissions" if total_cost > expected * 1.3 else "Specialist visits"

        return CostContext(
            ytd_cost=round(total_cost, 2),
            expected_cost=round(expected, 2),
            cost_status=status,
            cost_ratio=round(ratio, 2),
            top_cost_driver=driver,
            pmpm=round(member_pmpm, 2),
            benchmark_pmpm=self._benchmark_pmpm,
            provenance={"step": "cost", "step_number": 4, "member_id": member_id},
        )

    def _check_crossover(self, member_id: str, demo_role: str) -> dict | None:
        if demo_role != "crossover_patient":
            return None

        for disc in self._reconciliation.get("discrepancies", []):
            if disc.get("category") == "quality":
                return {
                    "discrepancy_id": disc.get("id", ""),
                    "category": disc.get("category", ""),
                    "metric": disc.get("metric", ""),
                    "metric_label": disc.get("metric_label", ""),
                    "platform_value": disc.get("platform_value"),
                    "payer_value": disc.get("payer_value"),
                    "description": (
                        f"Your organization's calculation includes this patient in the "
                        f"{disc.get('metric_label', 'quality measure')} measure. "
                        f"The payer's settlement report disagrees. "
                        f"This discrepancy is documented in the Settlement Reconciliation view."
                    ),
                }
        return None

    def _prioritize_actions(
        self,
        attribution_risk: AttributionRisk,
        quality_gaps: list[QualityGap],
        hcc_opportunities: list[HccOpportunity],
        cost_context: CostContext,
        days_remaining: int,
    ) -> list[PriorityAction]:
        candidates = []
        time_pressure = max(0.0, min(1.0, 1.0 - (days_remaining / 365.0)))

        for gap in quality_gaps:
            financial = gap.financial_weight
            urgency = 1.0
            closability = 1.0 if gap.closable_this_visit else 0.5
            score = financial * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=gap.action_needed,
                reason_text=f"Closes 1 of {len(quality_gaps)} remaining care actions",
                category="gap_closure",
                measure_id=gap.measure_id,
                financial_impact=None,
                closable_this_visit=gap.closable_this_visit,
                provenance=gap.provenance,
            )))

        for hcc in hcc_opportunities:
            urgency = 0.8
            closability = 1.0
            score = 0.3 * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=f"Document {hcc.condition_name} if clinically appropriate",
                reason_text="Condition to document — supports accurate care needs assessment",
                category="hcc_recapture",
                closable_this_visit=True,
                provenance=hcc.provenance,
            )))

        if attribution_risk.status in ("moderate_risk", "high_risk"):
            urgency = 0.6
            closability = 0.3
            score = 0.2 * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=attribution_risk.recommended_action or "Schedule a follow-up visit",
                reason_text="This patient is at risk of leaving your panel",
                category="attribution_retention",
                closable_this_visit=False,
                provenance=attribution_risk.provenance,
            )))

        candidates.sort(key=lambda x: x[0], reverse=True)
        actions = []
        for i, (_, action) in enumerate(candidates[:3]):
            action.rank = i + 1
            actions.append(action)

        return actions
