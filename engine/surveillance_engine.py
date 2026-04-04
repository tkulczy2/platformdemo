"""Surveillance Engine — analyses attribution history and pipeline output.

Read-only analysis layer. Reads attribution_history.json and PipelineResult
but never modifies either. Produces a SurveillanceResult powering all
dashboard views.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from engine.brief_engine import AttributionRisk
from engine.provenance import PipelineResult

SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MonthlySnapshot:
    month: str
    snapshot_date: str
    total_attributed: int
    new_attributions: int
    lost_attributions: int
    reassignments: int
    net_change: int
    churn_rate: float
    cumulative_financial_impact: float


@dataclass
class ChangeEvent:
    event_id: str
    member_id: str
    event_month: str
    event_type: str
    change_classification: str
    prior_provider: dict | None
    new_provider: dict | None
    reason: str
    financial_impact: dict
    quality_measures_affected: list[str]
    quality_numerator_losses: list[str]
    intervention: dict | None
    member_risk_score: float = 1.0
    member_annual_cost_estimate: float = 0.0
    provenance: dict = field(default_factory=dict)


@dataclass
class ProviderPanelSummary:
    provider_npi: str
    provider_name: str
    specialty: str
    current_panel_size: int
    jan_panel_size: int
    net_change: int
    net_change_pct: float
    churn_rate_annualized: float
    members_at_risk: int
    financial_exposure: float
    quality_impact: dict
    monthly_trend: list[int]
    cascade_flag: bool


@dataclass
class RetentionWorklistItem:
    rank: int
    member_id: str
    member_demographics: dict
    attributed_provider: dict
    attribution_risk: dict
    risk_factors: list[str]
    competing_provider: dict | None
    days_since_last_visit: int
    visits_this_year: int
    financial_impact_if_lost: dict
    quality_measures_at_stake: list[dict]
    recommended_action: str
    intervention_cost_estimate: float
    recovery_probability: float
    roi_estimate: float
    days_remaining_in_period: int
    urgency: str
    has_upcoming_appointment: bool
    next_appointment_date: str | None


@dataclass
class ProjectionScenario:
    scenario_name: str
    projected_attributed_count: int
    projected_churn_rate: float
    projected_shared_savings: float
    projected_quality_composite: float
    projected_quality_bonus: float
    projected_total_settlement: float
    key_assumptions: list[str]


@dataclass
class SurveillanceResult:
    monthly_snapshots: list[MonthlySnapshot]
    change_events: list[ChangeEvent]
    current_attributed_count: int
    current_at_risk_count: int
    current_financial_exposure: float
    provider_panels: list[ProviderPanelSummary]
    retention_worklist: list[RetentionWorklistItem]
    projections: list[ProjectionScenario]
    churn_by_classification: dict
    churn_by_quarter: dict
    quality_impact_summary: dict
    settlement_attribution_discrepancies: list[dict]
    clinical_view_at_risk_patients: list[str]
    narrative_markers: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SurveillanceEngine:
    """Analyses attribution history and pipeline output."""

    def __init__(
        self,
        attribution_history: dict,
        pipeline_result: PipelineResult,
        contract_config: dict,
        clinical_schedule: dict | None = None,
    ):
        self._history = attribution_history
        self._pipeline = pipeline_result
        self._contract = contract_config
        self._schedule = clinical_schedule

        # Index pipeline data
        self._attr_step = pipeline_result.steps[1]
        self._qual_step = pipeline_result.steps[2]
        self._cost_step = pipeline_result.steps[3]

        self._attribution_details = self._attr_step.summary.get("attribution_details", {})
        self._attributed_population = set(self._attr_step.summary.get("attributed_population", []))

        # Member cost lookup
        self._member_costs: dict[str, float] = {}
        for md in self._cost_step.member_details:
            self._member_costs[md.member_id] = md.intermediate_values.get("total_cost", 0)

        # Member risk scores
        self._member_risk_scores: dict[str, float] = {}
        # Pull from history December snapshot
        dec_snap = self._history["snapshots"][-1] if self._history.get("snapshots") else None
        if dec_snap:
            for m in dec_snap["members"]:
                self._member_risk_scores[m["member_id"]] = m.get("risk_tier", "stable")

        # Quality data per member — map to measure_id via reason text
        self._member_quality: dict[str, dict] = {}
        for md in self._qual_step.member_details:
            measure_key = self._reason_to_measure(md.reason or "")
            if measure_key:
                self._member_quality.setdefault(md.member_id, {})[measure_key] = md.outcome

        # Quality summary from step 3
        self._quality_summary = self._qual_step.summary

        # Contract parameters
        self._perf_year = contract_config.get("performance_year", 2025)
        settlement_params = (
            contract_config.get("clauses", {})
            .get("settlement", {})
            .get("parameters", {})
        )
        self._benchmark_pmpm = settlement_params.get("benchmark_pmpm", 1187.0)
        self._shared_savings_rate = settlement_params.get("shared_savings_rate", 0.50)
        self._quality_gate = settlement_params.get("quality_gate_threshold", 0.40)

        # Attribution by member from step 2
        self._attr_by_member = {}
        for md in self._attr_step.member_details:
            self._attr_by_member[md.member_id] = md

        # Schedule member IDs
        self._schedule_member_ids: set[str] = set()
        self._schedule_dates: dict[str, str] = {}
        if self._schedule:
            for day in self._schedule.get("days", []):
                for apt in day.get("appointments", []):
                    mid = apt["member_id"]
                    self._schedule_member_ids.add(mid)
                    self._schedule_dates[mid] = day["date"]

    @staticmethod
    def _reason_to_measure(reason: str) -> str | None:
        """Map a quality member detail reason to a measure key."""
        r = reason.lower()
        if "hba1c" in r or "diabetes" in r:
            return "hba1c_poor_control"
        if "blood pressure" in r or "bp " in r:
            return "controlling_bp"
        if "breast" in r or "mammog" in r:
            return "breast_cancer_screening"
        if "colorectal" in r or "colon" in r:
            return "colorectal_screening"
        if "depression" in r or "phq" in r:
            return "depression_screening"
        return None

    def analyze(self) -> SurveillanceResult:
        """Run the full surveillance analysis."""
        snapshots = self._build_monthly_snapshots()
        change_events = self._classify_change_events()
        provider_panels = self._analyze_provider_panels()
        worklist = self._build_retention_worklist()
        projections = self._project_year_end(snapshots, worklist)
        aggregates = self._compute_aggregate_analytics(change_events)
        cross_tab = self._find_cross_tab_connections(worklist)

        # Current state from December snapshot
        dec_snap = self._history["snapshots"][-1]
        current_count = dec_snap["total_attributed"]
        at_risk = [
            m for m in dec_snap["members"]
            if m.get("risk_tier") in ("high_risk", "moderate_risk")
        ]
        at_risk_count = len(at_risk)
        financial_exposure = sum(
            self._member_costs.get(m["member_id"], 12400) * 0.02
            for m in at_risk
        )

        return SurveillanceResult(
            monthly_snapshots=snapshots,
            change_events=change_events,
            current_attributed_count=current_count,
            current_at_risk_count=at_risk_count,
            current_financial_exposure=round(financial_exposure, 2),
            provider_panels=provider_panels,
            retention_worklist=worklist,
            projections=projections,
            churn_by_classification=aggregates["by_classification"],
            churn_by_quarter=aggregates["by_quarter"],
            quality_impact_summary=aggregates["quality_impact"],
            settlement_attribution_discrepancies=cross_tab["settlement_discrepancies"],
            clinical_view_at_risk_patients=cross_tab["clinical_at_risk"],
            narrative_markers=self._history.get("narrative_markers", {}),
        )

    # ------------------------------------------------------------------
    # 1. Monthly snapshots
    # ------------------------------------------------------------------

    def _build_monthly_snapshots(self) -> list[MonthlySnapshot]:
        summaries = self._history.get("summary_by_month", [])
        snapshots = []
        prev_total = 0

        for i, s in enumerate(summaries):
            total = s["total_attributed"]
            lost = s.get("lost_attributions", 0)
            churn_rate = lost / prev_total if prev_total > 0 else 0.0

            snapshots.append(MonthlySnapshot(
                month=s["month"],
                snapshot_date=self._history["snapshots"][i]["snapshot_date"] if i < len(self._history["snapshots"]) else s["month"] + "-28",
                total_attributed=total,
                new_attributions=s.get("new_attributions", 0),
                lost_attributions=lost,
                reassignments=s.get("reassignments", 0),
                net_change=s.get("net_change", 0),
                churn_rate=round(churn_rate, 4),
                cumulative_financial_impact=s.get("cumulative_financial_impact", 0),
            ))
            prev_total = total

        return snapshots

    # ------------------------------------------------------------------
    # 2. Change events
    # ------------------------------------------------------------------

    def _classify_change_events(self) -> list[ChangeEvent]:
        raw_events = self._history.get("change_events", [])
        events = []

        for e in raw_events:
            mid = e["member_id"]
            # Enrich with pipeline data
            quality_affected = e.get("quality_measures_affected", [])
            quality_losses = e.get("quality_numerator_losses", [])

            events.append(ChangeEvent(
                event_id=e["event_id"],
                member_id=mid,
                event_month=e["event_month"],
                event_type=e["event_type"],
                change_classification=e["change_classification"],
                prior_provider=e.get("prior_provider"),
                new_provider=e.get("new_provider"),
                reason=e.get("reason", ""),
                financial_impact=e.get("financial_impact", {}),
                quality_measures_affected=quality_affected,
                quality_numerator_losses=quality_losses,
                intervention=e.get("intervention_opportunity"),
                member_risk_score=e.get("member_risk_score", 1.0),
                member_annual_cost_estimate=e.get("member_annual_cost_estimate", 0),
                provenance={"step": "attribution", "step_number": 2, "member_id": mid},
            ))

        return events

    # ------------------------------------------------------------------
    # 3. Provider panels
    # ------------------------------------------------------------------

    def _analyze_provider_panels(self) -> list[ProviderPanelSummary]:
        snapshots = self._history.get("snapshots", [])
        if not snapshots:
            return []

        jan_snap = snapshots[0]
        dec_snap = snapshots[-1]

        # Build provider → members mapping for each month
        monthly_panels: dict[str, list[int]] = {}  # npi → [count_per_month]
        all_provider_npis: set[str] = set()

        for snap in snapshots:
            month_panels: dict[str, int] = {}
            for m in snap["members"]:
                npi = m["attributed_provider_npi"]
                all_provider_npis.add(npi)
                month_panels[npi] = month_panels.get(npi, 0) + 1
            for npi in all_provider_npis:
                monthly_panels.setdefault(npi, []).append(month_panels.get(npi, 0))

        # December membership by provider
        dec_panels: dict[str, list[dict]] = {}
        for m in dec_snap["members"]:
            dec_panels.setdefault(m["attributed_provider_npi"], []).append(m)

        # January membership by provider
        jan_panels: dict[str, int] = {}
        for m in jan_snap["members"]:
            jan_panels[m["attributed_provider_npi"]] = jan_panels.get(m["attributed_provider_npi"], 0) + 1

        # Change events by provider
        provider_losses: dict[str, list[int]] = {}
        for e in self._history.get("change_events", []):
            if e["event_type"] == "lost_attribution" and e.get("prior_provider"):
                npi = e["prior_provider"]["npi"]
                month = int(e["event_month"].split("-")[1])
                provider_losses.setdefault(npi, []).append(month)

        summaries = []
        for npi in sorted(all_provider_npis):
            dec_members = dec_panels.get(npi, [])
            current_size = len(dec_members)
            jan_size = jan_panels.get(npi, 0)
            net_change = current_size - jan_size
            net_pct = net_change / jan_size if jan_size > 0 else 0

            # Members at risk
            at_risk_members = [
                m for m in dec_members
                if m.get("risk_tier") in ("high_risk", "moderate_risk")
            ]
            at_risk_count = len(at_risk_members)

            # Financial exposure
            fin_exposure = sum(
                self._member_costs.get(m["member_id"], 12400) * 0.02
                for m in at_risk_members
            )

            # Churn rate
            losses = provider_losses.get(npi, [])
            total_losses = len(losses)
            avg_panel = (jan_size + current_size) / 2 if (jan_size + current_size) > 0 else 1
            churn_annualized = total_losses / avg_panel if avg_panel > 0 else 0

            # Cascade detection: 4+ losses in any 3-month window
            cascade = False
            for start in range(1, 11):
                window = [m for m in losses if start <= m <= start + 2]
                if len(window) >= 4:
                    cascade = True
                    break

            # Monthly trend
            trend = monthly_panels.get(npi, [0] * 12)
            # Pad to 12 if shorter
            while len(trend) < 12:
                trend.append(trend[-1] if trend else 0)

            # Quality impact stub
            quality_impact = {}

            # Provider name from December snapshot
            provider_name = ""
            if dec_members:
                provider_name = dec_members[0].get("attributed_provider_name", "")

            summaries.append(ProviderPanelSummary(
                provider_npi=npi,
                provider_name=provider_name,
                specialty="Family Medicine",
                current_panel_size=current_size,
                jan_panel_size=jan_size,
                net_change=net_change,
                net_change_pct=round(net_pct, 4),
                churn_rate_annualized=round(churn_annualized, 4),
                members_at_risk=at_risk_count,
                financial_exposure=round(fin_exposure, 2),
                quality_impact=quality_impact,
                monthly_trend=trend[:12],
                cascade_flag=cascade,
            ))

        # Sort by financial exposure desc
        summaries.sort(key=lambda s: s.financial_exposure, reverse=True)
        return summaries

    # ------------------------------------------------------------------
    # 4. Retention worklist
    # ------------------------------------------------------------------

    def _build_retention_worklist(self) -> list[RetentionWorklistItem]:
        dec_snap = self._history["snapshots"][-1]
        at_risk = [
            m for m in dec_snap["members"]
            if m.get("risk_tier") in ("high_risk", "moderate_risk")
        ]

        items = []
        for m in at_risk:
            mid = m["member_id"]
            npi = m["attributed_provider_npi"]

            # Compute attribution risk using brief_engine logic
            attr_md = self._attr_by_member.get(mid)
            risk_status = m.get("risk_tier", "moderate_risk")

            iv = attr_md.intermediate_values if attr_md else {}
            visit_counts = iv.get("visit_counts_by_provider", {})
            attr_visits = 0
            competing_prov = None
            if npi in visit_counts:
                attr_visits = visit_counts[npi].get("count", 0)
            for other_npi, info in visit_counts.items():
                if other_npi != npi and info.get("count", 0) > 0:
                    competing_prov = {"npi": other_npi, "visit_count": info["count"]}
                    break

            # Risk factors
            risk_factors = []
            if competing_prov:
                risk_factors.append(f"Competing visits with provider {competing_prov['npi']}")
            if attr_visits < 2:
                risk_factors.append("Fewer than 2 visits with attributed provider this year")
            if m.get("months_continuously_attributed", 0) < 4:
                risk_factors.append("Recently attributed — care relationship not established")

            # Financial impact
            actual_cost = self._member_costs.get(mid, 12400)
            risk_score = 1.0  # Default
            ss_contribution = 185.0 * risk_score
            quality_contribution = 42.0 * risk_score
            total_impact = ss_contribution + quality_contribution

            financial_impact_if_lost = {
                "tcoc": round(actual_cost, 2),
                "shared_savings": round(ss_contribution, 2),
                "quality_bonus": round(quality_contribution, 2),
                "total": round(total_impact, 2),
            }

            # Quality measures at stake
            member_quality = self._member_quality.get(mid, {})
            quality_at_stake = []
            for measure_id, outcome in member_quality.items():
                if outcome == "in_numerator":
                    quality_at_stake.append({
                        "measure_id": measure_id,
                        "measure_name": measure_id.replace("_", " ").title(),
                        "currently_met": True,
                        "rate_impact": -0.001,
                    })

            # ROI calculation
            if competing_prov and competing_prov.get("visit_count", 0) >= 3:
                recovery_prob = 0.45
                cost = 250.0
                action = "Schedule wellness visit with attributed PCP to re-establish plurality"
            elif competing_prov:
                recovery_prob = 0.70
                cost = 250.0
                action = "Schedule wellness visit with attributed PCP to re-establish plurality"
            elif attr_visits < 2:
                recovery_prob = 0.80
                cost = 150.0
                action = "Phone outreach to schedule follow-up appointment"
            else:
                recovery_prob = 0.65
                cost = 250.0
                action = "Schedule care coordination visit"

            roi = (total_impact * recovery_prob) / cost if cost > 0 else 0

            # Days remaining
            days_remaining = 73  # Oct 20 to Dec 31

            # Urgency
            if risk_status == "high_risk" and days_remaining < 90:
                urgency = "critical"
            elif risk_status == "high_risk" or (risk_status == "moderate_risk" and days_remaining < 60):
                urgency = "high"
            else:
                urgency = "moderate"

            # Cross-reference with clinical schedule
            has_appt = mid in self._schedule_member_ids
            next_date = self._schedule_dates.get(mid)

            items.append(RetentionWorklistItem(
                rank=0,  # Set after sorting
                member_id=mid,
                member_demographics={"age": 0, "sex": ""},
                attributed_provider={"npi": npi, "name": m.get("attributed_provider_name", "")},
                attribution_risk={
                    "status": risk_status,
                    "stability_score": 0.3 if risk_status == "high_risk" else 0.5,
                    "risk_factors": risk_factors,
                },
                risk_factors=risk_factors,
                competing_provider=competing_prov,
                days_since_last_visit=0,
                visits_this_year=attr_visits,
                financial_impact_if_lost=financial_impact_if_lost,
                quality_measures_at_stake=quality_at_stake,
                recommended_action=action,
                intervention_cost_estimate=cost,
                recovery_probability=recovery_prob,
                roi_estimate=round(roi, 2),
                days_remaining_in_period=days_remaining,
                urgency=urgency,
                has_upcoming_appointment=has_appt,
                next_appointment_date=next_date,
            ))

        # Sort by ROI descending
        items.sort(key=lambda x: x.roi_estimate, reverse=True)
        for i, item in enumerate(items):
            item.rank = i + 1

        return items

    # ------------------------------------------------------------------
    # 5. Projections
    # ------------------------------------------------------------------

    def _project_year_end(
        self,
        snapshots: list[MonthlySnapshot],
        worklist: list[RetentionWorklistItem],
    ) -> list[ProjectionScenario]:
        # Current metrics
        current_count = snapshots[-1].total_attributed if snapshots else 1000
        quality_composite = self._quality_summary.get("composite_score", 0.65)
        actual_pmpm = self._cost_step.summary.get("adjusted_pmpm", 1100)

        # Trailing 3-month churn rate
        recent = snapshots[-3:] if len(snapshots) >= 3 else snapshots
        avg_churn = sum(s.churn_rate for s in recent) / len(recent) if recent else 0.01

        # Base settlement calculation
        savings_per_member = max(0, self._benchmark_pmpm - actual_pmpm) * 12
        total_savings = savings_per_member * current_count * self._shared_savings_rate
        quality_bonus = total_savings * 0.1 if quality_composite >= self._quality_gate else 0

        # Scenario A: Current Trajectory
        projected_losses_a = int(current_count * avg_churn * 3)  # remaining ~3 months
        count_a = current_count - projected_losses_a
        savings_a = savings_per_member * count_a * self._shared_savings_rate
        quality_a = savings_a * 0.1 if quality_composite >= self._quality_gate else 0

        scenario_a = ProjectionScenario(
            scenario_name="current_trajectory",
            projected_attributed_count=count_a,
            projected_churn_rate=round(avg_churn * 12, 4),
            projected_shared_savings=round(savings_a, 2),
            projected_quality_composite=round(quality_composite, 4),
            projected_quality_bonus=round(quality_a, 2),
            projected_total_settlement=round(savings_a + quality_a, 2),
            key_assumptions=[
                f"Churn continues at trailing 3-month rate ({avg_churn:.1%}/month)",
                "No additional retention interventions",
                f"Quality composite holds at {quality_composite:.1%}",
            ],
        )

        # Scenario B: With Targeted Intervention
        critical_high = [w for w in worklist if w.urgency in ("critical", "high")]
        recovered = sum(1 for w in critical_high if w.recovery_probability > 0.5)
        intervention_cost = sum(w.intervention_cost_estimate for w in critical_high)
        count_b = count_a + recovered
        savings_b = savings_per_member * count_b * self._shared_savings_rate
        quality_b_composite = min(1.0, quality_composite + 0.01 * (recovered / max(current_count, 1)))
        quality_b = savings_b * 0.1 if quality_b_composite >= self._quality_gate else 0

        scenario_b = ProjectionScenario(
            scenario_name="with_intervention",
            projected_attributed_count=count_b,
            projected_churn_rate=round(avg_churn * 12 * 0.7, 4),
            projected_shared_savings=round(savings_b, 2),
            projected_quality_composite=round(quality_b_composite, 4),
            projected_quality_bonus=round(quality_b, 2),
            projected_total_settlement=round(savings_b + quality_b, 2),
            key_assumptions=[
                f"Execute retention actions for {len(critical_high)} critical/high urgency members",
                f"Total intervention cost: ${intervention_cost:,.2f}",
                f"Expected recoveries: {recovered} members based on probability-weighted estimates",
                "Churn rate reduced by 30% through targeted outreach",
            ],
        )

        # Scenario C: Worst Case
        at_risk_count = len(worklist)
        count_c = current_count - at_risk_count
        savings_c = savings_per_member * count_c * self._shared_savings_rate
        worst_quality = max(0, quality_composite - 0.05)
        quality_c = savings_c * 0.1 if worst_quality >= self._quality_gate else 0

        scenario_c = ProjectionScenario(
            scenario_name="worst_case",
            projected_attributed_count=count_c,
            projected_churn_rate=round(at_risk_count / current_count, 4) if current_count else 0,
            projected_shared_savings=round(savings_c, 2),
            projected_quality_composite=round(worst_quality, 4),
            projected_quality_bonus=round(quality_c, 2),
            projected_total_settlement=round(savings_c + quality_c, 2),
            key_assumptions=[
                f"All {at_risk_count} at-risk members are lost",
                "No recoveries",
                "Quality composite drops by ~5 points due to numerator losses",
            ],
        )

        return [scenario_a, scenario_b, scenario_c]

    # ------------------------------------------------------------------
    # 6. Aggregate analytics
    # ------------------------------------------------------------------

    def _compute_aggregate_analytics(self, events: list[ChangeEvent]) -> dict:
        # By classification
        by_class: dict[str, dict] = {}
        for e in events:
            cls = e.change_classification
            if cls not in by_class:
                by_class[cls] = {"count": 0, "financial_impact": 0}
            by_class[cls]["count"] += 1
            by_class[cls]["financial_impact"] += e.financial_impact.get("total_impact", 0)

        for cls in by_class:
            by_class[cls]["financial_impact"] = round(by_class[cls]["financial_impact"], 2)

        # By quarter
        by_quarter: dict[str, dict] = {}
        for e in events:
            month = int(e.event_month.split("-")[1])
            q = f"Q{(month - 1) // 3 + 1}"
            if q not in by_quarter:
                by_quarter[q] = {"new": 0, "lost": 0, "net": 0, "reassignments": 0}
            if e.event_type == "new_attribution":
                by_quarter[q]["new"] += 1
            elif e.event_type == "lost_attribution":
                by_quarter[q]["lost"] += 1
            elif e.event_type == "reassignment":
                by_quarter[q]["reassignments"] += 1
        for q in by_quarter:
            by_quarter[q]["net"] = by_quarter[q]["new"] - by_quarter[q]["lost"]

        # Quality impact
        quality_impact: dict[str, dict] = {}
        measures = self._quality_summary.get("measures", {})

        dec_snap = self._history["snapshots"][-1]
        at_risk_ids = set(
            m["member_id"] for m in dec_snap["members"]
            if m.get("risk_tier") in ("high_risk", "moderate_risk")
        )

        for measure_id, measure_info in measures.items():
            if not isinstance(measure_info, dict):
                continue
            current_rate = measure_info.get("rate", 0)
            eligible = measure_info.get("eligible_count", 1)
            numerator = measure_info.get("numerator_count", 0)

            # Count at-risk members in this measure's numerator
            at_risk_in_numerator = 0
            at_risk_in_measure = 0
            for mid in at_risk_ids:
                mq = self._member_quality.get(mid, {})
                if measure_id in mq:
                    at_risk_in_measure += 1
                    if mq[measure_id] == "in_numerator":
                        at_risk_in_numerator += 1

            # Projected rate if at-risk members lost from denominator
            new_numerator = max(0, numerator - at_risk_in_numerator)
            new_eligible = max(1, eligible - at_risk_in_measure)
            projected_rate = (new_numerator / new_eligible * 100) if new_eligible > 0 else 0

            quality_impact[measure_id] = {
                "measure_name": measure_info.get("measure_name", measure_id),
                "current_rate": round(current_rate, 2),
                "rate_if_at_risk_lost": round(projected_rate, 2),
                "rate_change": round(projected_rate - current_rate, 2),
                "members_at_stake": at_risk_in_numerator,
                "eligible_count": eligible,
            }

        return {
            "by_classification": by_class,
            "by_quarter": by_quarter,
            "quality_impact": quality_impact,
        }

    # ------------------------------------------------------------------
    # 7. Cross-tab connections
    # ------------------------------------------------------------------

    def _find_cross_tab_connections(self, worklist: list[RetentionWorklistItem]) -> dict:
        # Settlement attribution discrepancies
        discrepancies = []
        recon = self._pipeline.reconciliation or {}
        for d in recon.get("discrepancies", []):
            if d.get("category") == "attribution":
                discrepancies.append(d)

        # Clinical schedule overlap
        worklist_ids = {w.member_id for w in worklist}
        clinical_at_risk = list(worklist_ids & self._schedule_member_ids)

        return {
            "settlement_discrepancies": discrepancies,
            "clinical_at_risk": clinical_at_risk,
        }
