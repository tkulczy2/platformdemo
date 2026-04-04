# VBC Attribution Surveillance Dashboard — Implementation Plan

## For Claude Code Implementation as an Extension of the VBC Demo Tool

---

## 1. What This Is

This plan adds an **Attribution Surveillance** tab to the existing VBC Demo Tool, alongside the Settlement View and Clinical View tabs. The Surveillance tab demonstrates the panel management and attribution monitoring product concept: a population-level operational dashboard that shows how the attributed patient panel is changing over time, quantifies the financial impact of those changes, and provides worklists for retention intervention.

Where the Clinical View shows a **provider** what to do with individual patients at the point of care, the Surveillance tab shows a **panel manager or VP of Population Health** what's happening across the entire attributed population, where the financial risk is concentrating, and which patients need retention outreach before the performance period closes.

**What the Surveillance tab demonstrates:**

- 12 months of simulated attribution history showing how the panel has evolved
- Attribution change detection and classification (why each patient's status changed)
- Financial impact quantification for every attribution change
- Attribution risk scoring across the full 1,000-member population
- Provider-level panel views showing attribution stability by PCP
- A prioritized retention worklist with recommended actions and ROI estimates
- Quality measure impact analysis showing how attribution changes affect quality scores
- A projection of year-end attribution and its financial consequences
- Connection to both the Settlement View (reconciliation discrepancies caused by attribution disagreements) and the Clinical View (the same at-risk patients appear in pre-visit briefs)

**What the Surveillance tab does NOT demonstrate (deferred):**

- Real-time alert delivery (email, Slack, webhook)
- Alert configuration UI
- Multi-contract attribution comparison
- Payer attribution roster auto-ingestion
- Care management platform integration

---

## 2. Dependencies

### On the Platform Demo Tool (must be complete)

- `generator/` — Synthetic data generation (members, providers, claims, eligibility)
- `engine/` — Calculation pipeline with full provenance
  - `step_2_attribution.py` — Attribution engine with member-level detail
  - `step_3_quality.py` — Quality measure status per member
  - `step_4_cost.py` — Per-member cost data
  - `step_6_reconciliation.py` — Payer comparison including attribution discrepancies
- `api/` — FastAPI endpoints
- `frontend/` — React UI with tab navigation
- `data/synthetic/` — All CSV files generated
- `data/contracts/sample_mssp_contract.json` — Contract configuration

### On the Clinical View (should be complete, but not strictly required)

The Surveillance tab can be built independently of the Clinical View. However, the cross-tab linking (clicking an at-risk patient in the surveillance worklist and jumping to their pre-visit brief) requires the Clinical View to be functional. If building in parallel, implement the cross-tab links as the last step.

The `AttributionRisk` dataclass and scoring logic defined in `engine/brief_engine.py` should be **reused, not duplicated.** The surveillance engine imports and extends this logic rather than reimplementing it.

---

## 3. Core Design Decision: Simulated Time Series, Not Real-Time

The Platform demo tool operates on a single point-in-time snapshot: data as of a specific date, one calculation run, one set of results. Real attribution surveillance requires continuous monitoring over time — daily snapshots, change detection between snapshots, trend analysis over months.

Building an actual time-series surveillance system is out of scope for a demo. Instead, this plan uses a **simulated attribution history**: the synthetic data generator produces 12 monthly attribution snapshots that show how the panel composition changed over a full performance year. The surveillance engine analyzes these pre-computed snapshots as if they were the output of a daily monitoring system.

This gives the demo the full narrative power of attribution surveillance — churn trends, seasonal patterns, financial impact accumulation — without requiring infrastructure for continuous background processing.

**The simulation is transparent.** The demo does not pretend to be running real-time calculations. The UI clearly labels the data as "Performance Year 2025 Attribution History" and allows the user to step through months to see how the panel evolved. This is actually more useful for a demo than real-time monitoring, because it lets the presenter tell a 12-month story in 5 minutes.

---

## 4. Architecture

### How the Surveillance Tab Fits

```
VBC Demo Tool
├── Tab: Settlement View (existing)
│   └── Reconciliation engine → Payer comparison → Dispute documentation
│
├── Tab: Clinical View (existing — from Clinical View plan)
│   └── Brief engine → Pre-visit briefs → Gap closure → Week in Review
│
└── Tab: Attribution Surveillance (NEW — this plan)
    ├── Panel Overview → Provider Panels → Retention Worklist → Projections
    └── Uses:
        ├── engine/ (existing — attribution, quality, cost StepResults)
        ├── engine/brief_engine.py (existing — AttributionRisk scoring, reused)
        ├── generator/attribution_history.py (NEW — 12-month snapshot generator)
        ├── engine/surveillance_engine.py (NEW — change detection, financial impact, projections)
        ├── api/routes_surveillance.py (NEW — surveillance endpoints)
        └── frontend/src/components/surveillance/ (NEW — dashboard UI)
```

### Data Flow

```
generator/attribution_history.py
    │
    ▼
data/synthetic/attribution_history.json  (12 monthly snapshots)
    │
    ▼
engine/surveillance_engine.py
    ├── Reads: attribution_history.json (time series)
    ├── Reads: PipelineResult (current-period calculation output)
    ├── Imports: AttributionRisk from brief_engine.py (risk scoring)
    ├── Produces: SurveillanceResult (panel analytics, change events, worklists, projections)
    │
    ▼
api/routes_surveillance.py
    │
    ▼
frontend/src/components/surveillance/*
```

---

## 5. Project Structure (New Files Only)

```
vbc-demo/
├── generator/
│   └── attribution_history.py         # NEW: 12-month attribution snapshot generator
│
├── engine/
│   └── surveillance_engine.py         # NEW: Change detection, impact, projections
│
├── api/
│   └── routes_surveillance.py         # NEW: Surveillance API endpoints
│
├── frontend/src/
│   └── components/
│       └── surveillance/              # NEW: Surveillance dashboard UI
│           ├── SurveillanceView.tsx    # Tab container and sub-navigation
│           ├── PanelOverview.tsx       # Population-level attribution summary
│           ├── AttributionTimeline.tsx # 12-month attribution trend chart
│           ├── ChangeEventTable.tsx    # Detailed change event log
│           ├── ProviderPanels.tsx      # Per-provider panel breakdown
│           ├── ProviderDetail.tsx      # Single provider's panel detail
│           ├── RetentionWorklist.tsx   # Prioritized retention action list
│           ├── FinancialImpact.tsx     # Financial impact of attribution changes
│           ├── QualityImpact.tsx       # Quality measure impact of attribution changes
│           ├── ProjectionView.tsx      # Year-end attribution and savings projection
│           ├── ChurnAnalysis.tsx       # Cohort-level churn analytics
│           └── CrossTabLinks.tsx       # Navigation links to Settlement/Clinical views
│
├── data/
│   └── synthetic/
│       └── attribution_history.json   # NEW: Generated 12-month snapshots
│
└── tests/
    ├── test_attribution_history.py    # NEW
    └── test_surveillance_engine.py    # NEW
```

---

## 6. Phase 1: Attribution History Generator

### File: `generator/attribution_history.py`

Generate 12 monthly attribution snapshots for the performance year (January 2025 through December 2025). Each snapshot represents the attributed population as of the last day of that month, calculated using the same attribution logic as the Platform's `step_2_attribution.py` but applied to a rolling data window.

### Why Simulate Rather Than Re-Run the Engine 12 Times

Running the full attribution engine 12 times with 12 different data-as-of dates would be the cleanest approach, but it requires 12 different views of the claims data (progressively more complete as the year advances). The synthetic data generator produces a single dataset with a single data-as-of date. Generating 12 valid claims snapshots that properly simulate run-out at each month would require a fundamental restructuring of the data generator.

Instead, this plan generates the attribution history as a **simulation layer on top of the existing dataset.** The generator:

1. Takes the current-period attribution output from `step_2_attribution.py` as the "ground truth" final state
2. Works backward to construct plausible monthly snapshots by simulating realistic attribution dynamics:
   - New attributions entering the panel each month (new enrollees, patients switching PCPs)
   - Lost attributions leaving the panel (disenrollment, PCP switching, death)
   - Provider reassignments within the ACO (plurality shifting between ACO providers)
   - Stability for the majority (most patients stay attributed to the same provider month-over-month)

This approach is less rigorous than re-running the attribution engine, but produces a realistic-looking time series that supports the demo narrative. The simulation parameters are tuned to produce industry-realistic churn rates.

### Simulation Parameters

```python
@dataclass
class AttributionHistoryConfig:
    """Parameters for simulating 12-month attribution history."""
    
    # Population dynamics
    base_population: int = 1000              # Starting attributed population (Jan)
    monthly_new_attribution_rate: float = 0.015   # ~1.5% new members per month
    monthly_lost_attribution_rate: float = 0.012  # ~1.2% lost members per month
    monthly_reassignment_rate: float = 0.005      # ~0.5% change providers within ACO per month
    
    # Seasonal patterns
    q1_churn_multiplier: float = 1.3         # Higher churn in Q1 (Medicare AEP effects)
    q4_churn_multiplier: float = 1.1         # Slight uptick in Q4 (pre-AEP shopping)
    summer_churn_multiplier: float = 0.8     # Lower churn Jun-Aug (stable period)
    
    # Attribution risk distribution at year-end
    pct_stable: float = 0.72                 # 72% of members stable throughout year
    pct_moderate_risk: float = 0.15          # 15% have moderate attribution risk
    pct_high_risk: float = 0.08             # 8% have high attribution risk
    pct_new: float = 0.05                    # 5% are new attributions this year
    
    # Financial parameters
    avg_attributed_member_annual_cost: float = 12400.0  # Average TCOC per member
    avg_shared_savings_per_member: float = 185.0        # Average SS contribution per member
    avg_quality_bonus_per_member: float = 42.0          # Average quality bonus per member
    
    # Seed for reproducibility
    seed: int = 42
```

### Snapshot Data Structure

Output file: `data/synthetic/attribution_history.json`

```json
{
  "performance_year": 2025,
  "contract_id": "CONTRACT-MSSP-2025",
  "generated_from": "simulation",
  "generation_note": "Simulated attribution history for demo purposes. Not derived from re-running the attribution engine on monthly data slices.",
  "snapshots": [
    {
      "month": "2025-01",
      "snapshot_date": "2025-01-31",
      "total_attributed": 987,
      "members": [
        {
          "member_id": "MBR-XXXXXX",
          "attributed_provider_npi": "1234567890",
          "attributed_provider_name": "Dr. Sarah Chen",
          "attribution_step": 1,
          "status": "attributed",
          "months_continuously_attributed": 14,
          "risk_tier": "stable"
        }
      ]
    },
    {
      "month": "2025-02",
      "snapshot_date": "2025-02-28",
      "total_attributed": 991,
      "members": [ ... ]
    }
  ],
  "change_events": [
    {
      "event_id": "CHG-00001",
      "member_id": "MBR-XXXXXX",
      "event_month": "2025-02",
      "event_type": "lost_attribution",
      "change_classification": "competing_provider",
      "prior_provider_npi": "1234567890",
      "prior_provider_name": "Dr. Sarah Chen",
      "new_provider_npi": "9876543210",
      "new_provider_name": "Dr. External Provider (non-ACO)",
      "reason": "Patient established plurality with non-ACO PCP based on 3 visits in Q4 2024 and Q1 2025",
      "member_risk_score": 1.24,
      "member_annual_cost_estimate": 15800.0,
      "quality_measures_affected": ["hba1c_control", "blood_pressure"],
      "quality_numerator_losses": ["hba1c_control"],
      "financial_impact": {
        "lost_tcoc_contribution": 15800.0,
        "lost_shared_savings_contribution": 237.0,
        "lost_quality_bonus_contribution": 58.0,
        "total_impact": 295.0
      },
      "intervention_opportunity": {
        "window_remaining_months": 10,
        "recommended_action": "Schedule wellness visit with attributed PCP to re-establish plurality",
        "estimated_intervention_cost": 250.0,
        "estimated_recovery_probability": 0.65,
        "roi_if_recovered": 1180.0
      }
    }
  ],
  "summary_by_month": [
    {
      "month": "2025-01",
      "total_attributed": 987,
      "new_attributions": 0,
      "lost_attributions": 0,
      "reassignments": 0,
      "net_change": 0,
      "cumulative_financial_impact": 0.0
    },
    {
      "month": "2025-02",
      "total_attributed": 991,
      "new_attributions": 18,
      "lost_attributions": 12,
      "reassignments": 3,
      "net_change": 4,
      "cumulative_financial_impact": -2340.0
    }
  ]
}
```

### Change Event Classification

Every attribution change must be classified into exactly one category. These categories are used throughout the dashboard for filtering and analysis:

| Classification | Description | Typical Cause | Intervention Potential |
|---|---|---|---|
| `competing_provider` | Patient built plurality with a non-ACO PCP | Patient visited another PCP more frequently | High — schedule a visit to re-establish plurality |
| `enrollment_gap` | Patient disenrolled from Medicare FFS | Moved to MA plan, moved out of area, Medicaid dual | Low — typically outside provider's control |
| `enrollment_termination` | Patient permanently left Medicare FFS | Death, aged out, permanent relocation | None |
| `reassignment_within_aco` | Patient's plurality shifted to a different ACO provider | Changed PCP within the network | Neutral — member stays in ACO, only panel-level impact |
| `new_enrollment` | Newly enrolled Medicare FFS beneficiary attributed to ACO | New to Medicare, moved into service area | N/A (positive event) |
| `new_plurality` | Existing enrollee newly meets plurality threshold with ACO provider | Patient started seeing ACO PCP more frequently | N/A (positive event) |
| `data_lag` | Attribution change appears to be a data timing artifact | Claims from competing provider arrived late | Low — will likely self-correct in next refresh |

### Generation Logic

```python
class AttributionHistoryGenerator:
    """
    Generates a simulated 12-month attribution history.
    
    Approach:
    1. Start with the full 1,000-member roster as the January baseline
    2. For each subsequent month, apply stochastic attribution dynamics:
       - Randomly select members to lose attribution (weighted by risk profile)
       - Randomly generate new attributions from a virtual "eligible pool"
       - Randomly reassign a small number of members between ACO providers
    3. For each change event, generate a plausible classification and financial impact
    4. Ensure the December snapshot roughly matches the current-period attribution
       output from step_2_attribution.py (the "ground truth")
    
    The generator uses the existing members.csv, providers.csv, and the
    PipelineResult's attribution StepResult to anchor the simulation in
    real synthetic data rather than generating everything from scratch.
    """
    
    def __init__(self, config: AttributionHistoryConfig, 
                 members_df: pd.DataFrame, 
                 providers_df: pd.DataFrame,
                 attribution_step_result: StepResult,
                 quality_step_result: StepResult,
                 cost_step_result: StepResult):
        ...
```

**Key generation rules:**

1. **Members who lose attribution must be real members from `members.csv`.** When a member is marked as "lost" in month N, their `member_id` comes from the existing roster. This ensures cross-referencing with the Platform's data is valid.

2. **Members who gain attribution should also be drawn from `members.csv`.** Rather than generating phantom members, use members who are in the roster but were initially excluded from attribution (e.g., those who didn't meet the plurality threshold in the Platform's calculation). This keeps the data internally consistent.

3. **The December snapshot should closely match the Platform's attribution output.** The simulation works backward from the known end state. Members who are attributed in the Platform's calculation should be attributed in December. Members who are not attributed should have been lost at some point during the year. Allow a small discrepancy (2-3%) to simulate realistic drift between the surveillance model and the calculation engine.

4. **Financial impact for each change event must be calculated from the member's actual data.** Use the member's cost data from `step_4_cost.py` and quality measure status from `step_3_quality.py` to compute realistic financial impact, not average estimates.

5. **Competing provider NPIs for `competing_provider` events should be drawn from the non-ACO providers in the provider roster** (or generated as external providers with realistic NPIs and names).

6. **Generate 5-8 non-ACO "competing providers"** with realistic names and specialties. These are the external PCPs that attributed members are drifting toward. Store them in the attribution_history.json for reference.

### Curated Narrative Moments

The history should include these specific patterns that the demo presenter can highlight:

1. **Q1 churn spike:** January and February show higher-than-average attribution losses, reflecting Medicare AEP effects. The financial impact section quantifies this seasonal pattern.

2. **A "save" story:** One member loses attribution in March (competing provider), then regains it in June after a retention visit with the ACO PCP re-establishes plurality. The change events show both the loss and the recovery, with the intervention documented.

3. **A cascade loss:** One provider (pick a PCP with a medium-sized panel) loses 4-5 attributed members over a 3-month period, suggesting a systemic issue (perhaps the provider reduced hours or relocated). The surveillance dashboard should surface this as a provider-level trend.

4. **A quality impact story:** A member who is lost to attribution in April was a quality measure numerator success — they had completed their HbA1c control and colorectal screening. Losing this member worsens two quality scores simultaneously. The change event documents the compound impact.

5. **An enrollment termination cluster:** Two members die during the year (realistic for an elderly Medicare population). These are `enrollment_termination` events with no intervention opportunity — included to show that the system distinguishes between preventable and non-preventable losses.

6. **Net positive trend:** Despite monthly churn, the overall panel grows modestly (net +1-2% over the year). This is realistic for a well-performing ACO and prevents the dashboard from telling an entirely negative story.

### Validation Criteria

After running the attribution history generator:
- `data/synthetic/attribution_history.json` exists and is valid JSON
- Contains exactly 12 monthly snapshots (January-December 2025)
- January snapshot has ~985-1000 members
- December snapshot member count is within 3% of the Platform's attribution output count
- All `member_id` values in all snapshots exist in `members.csv`
- All `attributed_provider_npi` values exist in `providers.csv`
- All change events reference valid member_ids
- Change events are internally consistent: a member marked as "lost" in month N does not appear as "attributed" in month N+1 (unless a recovery event is documented)
- At least 1 "save" story exists (loss followed by recovery)
- At least 1 cascade pattern exists (single provider losing 4+ members over 3 months)
- At least 1 quality impact story exists (lost member was a quality numerator success)
- Total change events: 80-120 across the year (realistic for a 1,000-member panel)
- Net population change over 12 months: +1% to +3%

---

## 7. Phase 2: Surveillance Engine

### File: `engine/surveillance_engine.py`

The surveillance engine analyzes the attribution history and produces a comprehensive `SurveillanceResult` that powers all dashboard views. Like the brief engine, it is a **read-only analysis layer** — it reads from the attribution history and the Platform's PipelineResult but never modifies either.

### Data Classes

```python
@dataclass
class MonthlySnapshot:
    """Attribution status for one month."""
    month: str                              # "2025-01"
    snapshot_date: str
    total_attributed: int
    new_attributions: int
    lost_attributions: int
    reassignments: int
    net_change: int
    churn_rate: float                       # lost / prior_month_total
    cumulative_financial_impact: float

@dataclass
class ChangeEvent:
    """A single attribution change event."""
    event_id: str
    member_id: str
    event_month: str
    event_type: str                         # "lost_attribution", "new_attribution", "reassignment"
    change_classification: str              # One of the 7 classification categories
    prior_provider: dict | None             # {npi, name}
    new_provider: dict | None               # {npi, name}
    reason: str                             # Human-readable explanation
    financial_impact: dict                  # {lost_tcoc, lost_ss, lost_quality, total}
    quality_measures_affected: list[str]    # Measure IDs affected by this change
    quality_numerator_losses: list[str]     # Measures where this member was a numerator success
    intervention: dict | None               # Intervention opportunity details
    provenance: dict                        # Link to source data

@dataclass
class ProviderPanelSummary:
    """Attribution summary for one provider."""
    provider_npi: str
    provider_name: str
    specialty: str
    current_panel_size: int
    jan_panel_size: int
    net_change: int
    net_change_pct: float
    churn_rate_annualized: float
    members_at_risk: int                    # Current high/moderate risk count
    financial_exposure: float               # Total financial impact of potential losses
    quality_impact: dict                    # {measure_id: rate_change_if_at_risk_lost}
    monthly_trend: list[int]                # Panel size per month (12 values)
    cascade_flag: bool                      # True if 4+ losses in any 3-month window

@dataclass
class RetentionWorklistItem:
    """A single item in the retention worklist."""
    rank: int
    member_id: str
    member_demographics: dict               # {age, sex}
    attributed_provider: dict               # {npi, name}
    attribution_risk: dict                  # Reuses AttributionRisk from brief_engine
    risk_factors: list[str]
    competing_provider: dict | None
    days_since_last_visit: int
    visits_this_year: int
    financial_impact_if_lost: dict          # {tcoc, shared_savings, quality_bonus, total}
    quality_measures_at_stake: list[dict]   # [{measure_id, measure_name, currently_met, rate_impact}]
    recommended_action: str
    intervention_cost_estimate: float
    recovery_probability: float
    roi_estimate: float                     # (financial_impact × recovery_probability) / intervention_cost
    days_remaining_in_period: int
    urgency: str                            # "critical", "high", "moderate"
    has_upcoming_appointment: bool           # Cross-reference with clinical schedule
    next_appointment_date: str | None       # If has_upcoming_appointment

@dataclass
class ProjectionScenario:
    """Year-end projection under a specific scenario."""
    scenario_name: str                      # "current_trajectory", "with_intervention", "worst_case"
    projected_attributed_count: int
    projected_churn_rate: float
    projected_shared_savings: float
    projected_quality_composite: float
    projected_quality_bonus: float
    projected_total_settlement: float
    key_assumptions: list[str]

@dataclass
class SurveillanceResult:
    """Complete output of the surveillance analysis."""
    # Timeline
    monthly_snapshots: list[MonthlySnapshot]    # 12 months
    change_events: list[ChangeEvent]            # All events across the year
    
    # Current state
    current_attributed_count: int
    current_at_risk_count: int
    current_financial_exposure: float           # Total $ at risk from at-risk members
    
    # Provider-level analysis
    provider_panels: list[ProviderPanelSummary]
    
    # Retention worklist
    retention_worklist: list[RetentionWorklistItem]  # Sorted by ROI desc
    
    # Projections
    projections: list[ProjectionScenario]       # 3 scenarios
    
    # Aggregate analytics
    churn_by_classification: dict               # {classification: {count, financial_impact}}
    churn_by_quarter: dict                      # {Q1: {new, lost, net}, Q2: ...}
    quality_impact_summary: dict                # {measure_id: {current_rate, rate_if_at_risk_lost, members_at_stake}}
    
    # Cross-tab connections
    settlement_attribution_discrepancies: list[dict]  # Attribution discrepancies from reconciliation
    clinical_view_at_risk_patients: list[str]         # member_ids that appear in both worklist and clinical schedule
```

### Surveillance Engine Logic

```python
class SurveillanceEngine:
    """
    Analyzes attribution history and current pipeline output to produce
    a comprehensive surveillance result.
    
    Usage:
        engine = SurveillanceEngine(
            attribution_history,      # Loaded from attribution_history.json
            pipeline_result,          # From the existing calculation pipeline
            contract_config,          # From sample_mssp_contract.json
            clinical_schedule=None    # Optional: weekly_schedule.json for cross-tab links
        )
        result = engine.analyze()
    """
```

### Analysis Methods (build in this order)

**1. `_build_monthly_snapshots()` → list[MonthlySnapshot]**

Transform the raw snapshot data from `attribution_history.json` into MonthlySnapshot objects. Calculate derived fields: churn_rate (lost / prior_month_total), cumulative_financial_impact (running sum of all lost member financial impacts).

**2. `_classify_change_events()` → list[ChangeEvent]**

Load change events from `attribution_history.json` and enrich them with:
- Financial impact calculated from the member's actual cost data (from step_4 output)
- Quality measures affected (from step_3 output — check which measures include this member)
- Quality numerator losses (was this member meeting the numerator criteria for any measure?)
- Provenance linking to the attribution StepResult for this member

**3. `_analyze_provider_panels()` → list[ProviderPanelSummary]**

For each PCP provider in the roster:
- Calculate current panel size from the December snapshot
- Calculate January panel size from the January snapshot
- Compute net change and churn rate
- Count members currently at moderate or high attribution risk (import `AttributionRisk` scoring from `brief_engine.py`)
- Calculate financial exposure: sum of `financial_impact_if_lost` for all at-risk members
- Compute quality impact: for each quality measure, what would the rate change be if all at-risk members were lost?
- Build the 12-month panel size trend (one value per month)
- Set cascade_flag if any 3-month rolling window has 4+ losses

**4. `_build_retention_worklist()` → list[RetentionWorklistItem]**

Build a prioritized retention worklist from all members with moderate or high attribution risk. For each at-risk member:

a. Import their `AttributionRisk` assessment (reuse from `brief_engine.py`)
b. Calculate `financial_impact_if_lost`:
   - `lost_tcoc`: The member's YTD cost (from step_4) extrapolated to annual
   - `lost_shared_savings`: Estimated shared savings contribution based on the member's cost relative to their risk-adjusted benchmark
   - `lost_quality_bonus`: Sum of quality bonus impact across all measures where the member is currently in the numerator
   - `total`: Sum of the above
c. Identify `quality_measures_at_stake`: which measures would lose a numerator member if this patient is lost?
d. Calculate `roi_estimate`:
   ```
   roi = (total_financial_impact × recovery_probability) / intervention_cost
   ```
   Where:
   - `recovery_probability` is based on the risk classification:
     - competing_provider with < 3 competing visits: 0.70
     - competing_provider with 3+ competing visits: 0.45
     - enrollment_gap (re-enrolled): 0.60
     - low visit frequency (no competing provider): 0.80
   - `intervention_cost` is estimated at $150-$350 depending on the recommended action:
     - Phone outreach: $50
     - Scheduled wellness visit: $250
     - Care coordination referral: $350
e. Set `urgency` based on days remaining in performance period and risk severity:
   - "critical": high_risk AND < 90 days remaining
   - "high": high_risk OR (moderate_risk AND < 60 days remaining)
   - "moderate": moderate_risk AND > 60 days remaining
f. Cross-reference with the clinical schedule: does this member have an upcoming appointment?

Sort the worklist by `roi_estimate` descending. The highest-ROI retention actions appear first — this means the worklist naturally prioritizes members where a small intervention cost can prevent a large financial loss with high probability.

**5. `_project_year_end()` → list[ProjectionScenario]**

Generate three year-end projection scenarios:

**Scenario A: "Current Trajectory"**
- Assumes churn continues at the current trailing-3-month rate
- No additional retention interventions
- Project month-by-month through the remaining performance period
- Calculate projected attributed count, quality composite, shared savings, and total settlement

**Scenario B: "With Targeted Intervention"**
- Assumes retention interventions are executed for all "critical" and "high" urgency worklist items
- Apply the `recovery_probability` to each intervened member
- Recalculate projected attribution, quality, and savings with recovered members included
- Show the delta from Scenario A: how much additional shared savings is captured

**Scenario C: "Worst Case"**
- Assumes all high-risk AND moderate-risk members are lost
- No recoveries
- Calculates the floor for attribution, quality, and savings
- Useful for downside risk quantification

Each scenario includes `key_assumptions` — a list of plain-English statements explaining the inputs to the projection.

**6. `_compute_aggregate_analytics()` → dict**

- `churn_by_classification`: Group all change events by classification, sum counts and financial impact per category
- `churn_by_quarter`: Aggregate new/lost/net by Q1-Q4
- `quality_impact_summary`: For each quality measure, compute: current rate, the rate if all at-risk members were lost (remove from numerator where applicable, remove from denominator), and the count of members at stake

**7. `_find_cross_tab_connections()` → dict**

- `settlement_attribution_discrepancies`: Pull attribution-category discrepancies from the reconciliation StepResult (step_6). These are members where the Platform and the payer disagree on attribution. Surface them as a link from the surveillance dashboard to the reconciliation view.
- `clinical_view_at_risk_patients`: Cross-reference the retention worklist member_ids against the clinical schedule's appointment list. If any at-risk member has an upcoming appointment, flag it — "This at-risk member is scheduled for a visit on [date]. View their pre-visit brief →"

### Validation Criteria

After building the surveillance engine:
- `SurveillanceEngine.analyze()` returns a valid `SurveillanceResult`
- 12 monthly snapshots with consistent total_attributed counts (each month's total = prior month + new - lost)
- Churn rates are plausible (0.5%-2.5% per month)
- All provider panels have correct panel sizes matching the December snapshot
- Retention worklist is sorted by ROI descending
- At least 1 cascade flag is set
- All 3 projection scenarios produce distinct results with Scenario B > Scenario A > Scenario C for projected_shared_savings
- Quality impact summary shows rate changes for at least 3 measures
- Cross-tab connections identify at least 1 settlement attribution discrepancy and at least 1 clinical schedule overlap

---

## 8. Phase 3: API Endpoints

### File: `api/routes_surveillance.py`

Add new endpoints to the existing FastAPI application. Register in `api/main.py`.

### Endpoints

```
GET /api/surveillance/overview
    Returns the high-level panel overview: current attributed count, at-risk count,
    financial exposure, and the 12-month snapshot trend.
    Response: {
        current_attributed: int,
        current_at_risk: int,
        current_financial_exposure: float,
        monthly_snapshots: list[MonthlySnapshot],
        churn_by_quarter: dict,
        net_change_ytd: int,
        net_change_pct_ytd: float
    }

GET /api/surveillance/changes?month={month}&classification={classification}
    Returns change events, optionally filtered by month and/or classification.
    Response: list[ChangeEvent]
    Supports pagination: ?offset=0&limit=20

GET /api/surveillance/providers
    Returns provider panel summaries for all PCPs.
    Response: list[ProviderPanelSummary]
    Default sort: by financial_exposure desc (most exposed provider first)

GET /api/surveillance/providers/{npi}
    Returns detailed panel information for a single provider, including:
    the 12-month panel trend, all change events for this provider's panel,
    at-risk members in this provider's panel, and quality impact specific
    to this provider's attributed population.
    Response: {
        provider: ProviderPanelSummary,
        change_events: list[ChangeEvent],
        at_risk_members: list[RetentionWorklistItem],
        quality_by_measure: dict
    }

GET /api/surveillance/worklist
    Returns the full retention worklist, sorted by ROI.
    Response: list[RetentionWorklistItem]
    Supports query params: ?urgency=critical&provider_npi=XXXX&min_roi=5.0

GET /api/surveillance/worklist/{member_id}
    Returns detailed retention information for a single member, including
    full attribution history (which months were they attributed, when did
    risk emerge), all change events involving this member, and cross-tab
    links to their clinical brief and any reconciliation discrepancies.
    Response: {
        member: RetentionWorklistItem,
        attribution_history: list[{month, status, provider}],
        change_events: list[ChangeEvent],
        clinical_brief_link: str | null,
        reconciliation_link: str | null
    }

GET /api/surveillance/projections
    Returns all three projection scenarios.
    Response: list[ProjectionScenario]

GET /api/surveillance/quality-impact
    Returns the quality impact summary: per-measure current rate,
    projected rate if at-risk members are lost, and members at stake.
    Response: dict (quality_impact_summary from SurveillanceResult)

GET /api/surveillance/financial-impact
    Returns financial impact breakdown: by classification, by quarter,
    cumulative over the year, and the intervention ROI summary.
    Response: {
        by_classification: dict,
        by_quarter: dict,
        cumulative_monthly: list[{month, cumulative_impact}],
        total_at_risk: float,
        total_intervention_cost: float,
        total_potential_recovery: float,
        aggregate_roi: float
    }

GET /api/surveillance/churn-analysis
    Returns cohort-level churn analytics: churn by classification,
    by quarter, by provider, and seasonal patterns.
    Response: {
        by_classification: dict,
        by_quarter: dict,
        by_provider: list[{npi, name, churn_rate, losses}],
        seasonal_pattern: list[{month, churn_rate}]
    }
```

### Integration with Existing API

In `api/main.py`, add:
```python
from api.routes_surveillance import router as surveillance_router
app.include_router(surveillance_router, prefix="/api/surveillance", tags=["surveillance"])
```

Initialize the SurveillanceEngine once at startup (or on first request). Cache the `SurveillanceResult` in memory — it's computed from static data and doesn't change during a demo session.

---

## 9. Phase 4: Frontend — Surveillance Dashboard UI

### Design Direction

Refer to the design-principles skill. For the Surveillance Dashboard:

**Personality: Sophistication & Trust with Data & Analysis.** This dashboard is consumed by VPs of Population Health, CFOs, and panel managers — people who make financial and operational decisions. It should feel like a financial analytics platform, not a clinical tool. Think Stripe Dashboard or Mercury's analytics — cool tones, data-dense but not cluttered, numbers as first-class citizens.

**Color foundation:** Cool slate foundation. Single accent: a deep blue-green (distinct from the Clinical View's warmer teal). Use red/amber/green sparingly and only for attribution risk status indicators.

**Typography:** Monospace for all numerical data, tabular-nums for column alignment. Geometric sans (Inter or system font) for labels and headers.

**Key visual choices:**
- The 12-month attribution timeline is the hero element — a large, clean area chart with net attribution count over time
- Financial numbers are always formatted with dollar signs and comma separators
- Percentage changes show directional arrows (↑ green for gains, ↓ red for losses)
- The retention worklist is a dense, sortable table — this is a power-user surface
- Provider panels use small multiples — one mini-chart per provider showing their 12-month trend

### Tab Integration

Add the third tab to the navigation:

```
[Settlement View]  [Clinical View]  [Attribution Surveillance]
```

### Sub-Navigation within the Surveillance Tab

The surveillance tab has its own internal navigation (sidebar or horizontal sub-nav):

```
Panel Overview  |  Provider Panels  |  Retention Worklist  |  Financial Impact  |  Projections
```

### Screen 1: Panel Overview (`PanelOverview.tsx` + `AttributionTimeline.tsx`)

The landing screen. Shows the population-level attribution story.

**Top Section — Key Metrics (4 metric cards in a row):**
- **Total Attributed:** Current count, with ↑/↓ vs. January and ↑/↓ vs. prior month
- **At Risk:** Count of moderate + high risk members, with financial exposure in dollars
- **YTD Churn Rate:** Annualized churn rate, with comparison to industry benchmark (~12-15% for Medicare ACOs)
- **Net Change:** YTD net attribution change (gains minus losses), with positive/negative coloring

**Hero Chart — Attribution Timeline (`AttributionTimeline.tsx`):**
- Large area chart showing total attributed population by month (12 data points)
- Stacked or overlaid: new attributions (green bars above the line), lost attributions (red bars below the line)
- Net change line overlaid
- Hover on any month shows: total attributed, new, lost, net change, cumulative financial impact
- Click on any month filters the change event table below to that month's events

**Change Event Summary (below the chart):**
- Horizontal bar chart or donut: change events by classification (competing_provider, enrollment_gap, etc.)
- Shows both count and financial impact for each category
- Click on a classification filters to those events

**Recent Change Events (`ChangeEventTable.tsx`):**
- Table showing the most recent 20 change events (or filtered set)
- Columns: Month, Member (demographics), Type, Classification, Prior Provider, Financial Impact, Action
- Sortable by any column
- Click on a row expands to show full detail: reason, quality measures affected, intervention opportunity
- "Export" button: download as CSV

**Quarterly Summary:**
- 4 mini-cards (Q1-Q4), each showing: new, lost, net, financial impact
- Highlight the Q1 churn spike pattern
- Q4 shows projected values if the performance period hasn't ended

### Screen 2: Provider Panels (`ProviderPanels.tsx` + `ProviderDetail.tsx`)

Shows attribution stability at the provider level. This is where cascade patterns become visible.

**Provider Panel Grid (`ProviderPanels.tsx`):**
- Card grid (one card per PCP provider, ~3 columns)
- Each card shows:
  - Provider name and specialty
  - Current panel size with ↑/↓ vs. January
  - Mini sparkline chart (12-month panel size trend)
  - At-risk member count with financial exposure
  - Churn rate (annualized)
  - Cascade warning flag (red badge if cascade_flag is true)
- Cards sorted by financial exposure (most exposed first)
- Click on a card opens ProviderDetail

**Provider Detail View (`ProviderDetail.tsx`):**
- Full-width view for a single provider
- **Panel Trend Chart:** Larger version of the sparkline — 12-month panel size with new/lost overlay
- **Panel Composition:** Pie or horizontal bar showing risk tier distribution (stable / moderate / high / new)
- **Change Event History:** Table of all change events for this provider's panel, sortable and filterable
- **At-Risk Members:** Subset of the retention worklist filtered to this provider's panel
- **Quality Impact:** Per-measure breakdown — if this provider's at-risk members are lost, what happens to each quality measure rate for this provider's panel?
- **The Save Story:** If the curated "save" event involves this provider, highlight it: "MBR-XXXX was lost in March but recovered in June after a retention visit. This demonstrates that intervention works."
- **The Cascade Story:** If this is the cascade provider, highlight the pattern: "This provider lost 5 members over March-May. Investigation recommended — possible provider availability or access issue."

### Screen 3: Retention Worklist (`RetentionWorklist.tsx`)

The operational heart of the dashboard. A dense, sortable, filterable table designed for panel managers to work from.

**Filters (top bar):**
- Urgency: All / Critical / High / Moderate
- Provider: All / [dropdown of PCP names]
- Risk classification: All / Competing Provider / Enrollment Gap / Low Frequency
- Minimum ROI: slider or input (default: show all)
- Has upcoming appointment: Yes / No / All

**Worklist Table:**
Columns:
- Rank (by ROI)
- Member (age/sex demographics)
- Provider (attributed PCP name)
- Risk Status (colored badge: red/yellow)
- Risk Factors (truncated list, expandable)
- Financial Impact (total $ at risk — monospace, right-aligned)
- Quality at Stake (count of measures affected, with a tooltip showing which measures)
- Recommended Action (one-line text)
- ROI (formatted as Nx, e.g., "4.7x" — monospace, right-aligned)
- Urgency (colored badge)
- Next Appt (date if has_upcoming_appointment, dash if not)

**Row Interaction:**
- Click a row to expand inline detail panel showing:
  - Full risk factor list
  - Competing provider detail (if applicable)
  - All quality measures at stake with current numerator status and rate impact if lost
  - Financial impact breakdown (TCOC, shared savings, quality bonus)
  - Intervention cost estimate and recovery probability
  - Attribution history for this member (mini timeline showing which months they were attributed)
- Cross-tab links at bottom of expanded detail:
  - "View Pre-Visit Brief →" (if they have an upcoming appointment in the clinical schedule)
  - "View in Settlement Reconciliation →" (if they are involved in an attribution discrepancy)

**Summary Bar (above the table):**
- Total worklist items: N
- Total financial exposure: $X
- Aggregate intervention cost: $Y
- Aggregate potential recovery: $Z
- Aggregate ROI: (Z / Y)x
- "If every retention action on this list is executed, projected recovery is $Z based on probability-weighted estimates."

### Screen 4: Financial Impact (`FinancialImpact.tsx` + `QualityImpact.tsx`)

The financial story of attribution churn. Designed for the CFO audience.

**Financial Impact Over Time:**
- Line chart: cumulative financial impact by month (starts at $0 in January, grows as losses accumulate)
- Stacked area below showing impact by classification category
- Annotation on the chart: "Q1 enrollment changes account for X% of total impact"

**Impact by Classification:**
- Horizontal bar chart: each classification category with its total financial impact
- Shows both count and dollars
- Highlights "competing_provider" as the largest controllable category

**Intervention ROI Summary:**
- Side-by-side comparison:
  - Left: "Total financial exposure from at-risk members: $X"
  - Right: "Total intervention cost for all retention actions: $Y"
  - Center: "Expected recovery (probability-weighted): $Z"
  - Bottom: "Net ROI: $(Z-Y) = Ax return on intervention investment"
- This is the slide a VP of Pop Health shows to the CFO to justify retention program funding

**Quality Impact (`QualityImpact.tsx`):**
- Table: one row per quality measure
- Columns: Measure Name, Current Rate, Rate if At-Risk Lost, Rate Change, Members at Stake, Financial Impact of Rate Change
- Conditional formatting: highlight measures where the rate change would drop below the quality gate threshold
- Narrative text: "If all 23 at-risk members are lost, 2 quality measures fall below the contract's quality gate threshold, eliminating $X in quality bonus."

### Screen 5: Projections (`ProjectionView.tsx`)

Three-scenario projection view. Shows the range of possible outcomes.

**Scenario Comparison:**
- Three columns, one per scenario: Current Trajectory, With Intervention, Worst Case
- Each column shows:
  - Projected attributed count at year-end
  - Projected churn rate
  - Projected shared savings
  - Projected quality composite
  - Projected quality bonus
  - Projected total settlement
- Key assumptions listed below each scenario (from `key_assumptions`)

**Visualization:**
- Grouped bar chart comparing the three scenarios on projected_total_settlement
- The delta between Scenario A and Scenario B is highlighted: "Targeted intervention adds $X to projected settlement"
- The delta between Scenario A and Scenario C is highlighted: "Downside risk without intervention: $Y"

**Narrative Summary:**
- Auto-generated paragraph: "Based on current attribution trends, the ACO is projected to receive $A in shared savings at year-end. If the [N] highest-ROI retention actions are executed at a total cost of $B, projected shared savings increase to $C — a net gain of $D. In a worst-case scenario where all at-risk members are lost, shared savings drop to $E."

### Cross-Tab Navigation (`CrossTabLinks.tsx`)

Reusable component for navigating between tabs. Appears wherever a cross-tab connection exists:

- In the retention worklist expanded detail: "View Pre-Visit Brief →" and "View in Settlement Reconciliation →"
- In the change event detail: "This member's attribution is disputed in the payer settlement → View Discrepancy"
- In the quality impact table: "View quality gap detail in the Clinical View →"

Implementation: use the React router (or the app's navigation system) to switch tabs and navigate to the specific item. Pass the `member_id` or `discrepancy_id` as a URL parameter so the target view can scroll to the relevant item.

---

## 10. Phase 5: Demo Narrative Integration

### Guided Walkthrough Extension

If the Clinical View's guided walkthrough is already implemented, extend it with surveillance-specific steps. If not, create a standalone walkthrough for the Surveillance tab.

### Surveillance Demo Script (8 steps)

**Step 1: Panel Overview**
Highlight: The full Panel Overview screen
Narrative: "This is what your population health team sees every morning. The attributed panel started the year at 987 members. Today it's at [N]. The timeline shows where the changes happened — and the financial impact of every change."

**Step 2: Q1 Churn Spike**
Highlight: The Q1 section of the attribution timeline
Narrative: "January and February show elevated churn — that's the Medicare Annual Enrollment Period effect. Twelve members lost attribution in these two months, representing $[X] in financial exposure. By detecting this pattern early, a retention program could have recovered an estimated $[Y]."

**Step 3: Cascade Provider**
Highlight: The cascade provider's card in Provider Panels
Narrative: "Dr. [Name]'s panel lost 5 members over three months. That's not random churn — that's a signal. Was the provider out on leave? Did they change locations? The surveillance system flags this pattern so leadership can investigate before the damage compounds."

**Step 4: Save Story**
Highlight: The recovered member's change event detail
Narrative: "Here's what intervention looks like. This member lost attribution in March — they'd been visiting a competing PCP. The panel manager scheduled a retention visit in May. By June, plurality was re-established. Cost of intervention: $250. Value recovered: $[X]. That's a [N]x return."

**Step 5: Retention Worklist**
Highlight: The retention worklist table
Narrative: "This is the operational output: a prioritized list of every member at risk, ranked by ROI. The top item has a projected return of [N]x on a $[cost] intervention. Your panel management team works from this list daily."

**Step 6: Quality Impact**
Highlight: The quality impact table
Narrative: "Attribution churn doesn't just affect cost — it affects quality scores. If these 23 at-risk members are lost, your HbA1c control rate drops [N] points and your colorectal screening rate drops [N] points. That's not just a quality issue — it threatens the quality gate that determines whether you receive shared savings at all."

**Step 7: Projections**
Highlight: The three-scenario projection view
Narrative: "Three scenarios, three outcomes. Without intervention, you're on track for $[A] in shared savings. Execute the top [N] retention actions at a total cost of $[B], and that improves to $[C]. The worst case — if every at-risk member is lost — drops you to $[D]. The retention program pays for itself [N] times over."

**Step 8: Cross-Tab Connection**
Highlight: A cross-tab link from the worklist to the Clinical View
Narrative: "And here's where it all connects. This at-risk member has an appointment Thursday. Click through to their pre-visit brief — the provider will see the attribution risk, the open quality gaps, and the specific actions that retain this member and close their care gaps in a single visit. One engine. Three audiences. Settlement reconciliation, clinical action, and panel management — all from the same data."

---

## 11. Build Order

**Strict sequential dependencies. Do not skip ahead.**

### Phase 1: Attribution History Generator (depends on Platform Phase 1-2)

Prerequisites: `generator/generate.py` has been run, `data/synthetic/` is populated, and the calculation pipeline produces a valid PipelineResult including step_2 (attribution), step_3 (quality), and step_4 (cost) results.

Build order:
1. `generator/attribution_history.py` — Config dataclass
2. `generator/attribution_history.py` — Core simulation logic (monthly snapshot generation)
3. `generator/attribution_history.py` — Change event generation with classification
4. `generator/attribution_history.py` — Financial impact calculation per event
5. `generator/attribution_history.py` — Curated narrative moments (save story, cascade, quality impact story)
6. `generator/attribution_history.py` — Competing provider generation (5-8 external PCPs)
7. `generator/attribution_history.py` — Run and write `attribution_history.json`
8. `tests/test_attribution_history.py` — Validation tests

**Validation checkpoint:** `data/synthetic/attribution_history.json` exists and passes all validation criteria from Section 6.

### Phase 2: Surveillance Engine (depends on Phase 1)

Build order:
1. `engine/surveillance_engine.py` — All dataclass definitions
2. `engine/surveillance_engine.py` — `SurveillanceEngine.__init__()` and data loading
3. `engine/surveillance_engine.py` — `_build_monthly_snapshots()`
4. `engine/surveillance_engine.py` — `_classify_change_events()`
5. `engine/surveillance_engine.py` — `_analyze_provider_panels()`
6. `engine/surveillance_engine.py` — `_build_retention_worklist()` (import AttributionRisk from brief_engine.py)
7. `engine/surveillance_engine.py` — `_project_year_end()` (three scenarios)
8. `engine/surveillance_engine.py` — `_compute_aggregate_analytics()`
9. `engine/surveillance_engine.py` — `_find_cross_tab_connections()`
10. `engine/surveillance_engine.py` — `analyze()` method that orchestrates all of the above
11. `tests/test_surveillance_engine.py` — Full test suite

**Validation checkpoint:** `SurveillanceEngine.analyze()` returns a valid `SurveillanceResult`. Three projection scenarios produce distinct results. Retention worklist is sorted by ROI. At least 1 cascade flag. Cross-tab connections populated.

### Phase 3: API Endpoints (depends on Phase 2)

Build order:
1. `api/routes_surveillance.py` — All endpoints
2. Register routes in `api/main.py`
3. Test all endpoints via FastAPI docs

**Validation checkpoint:** All endpoints return valid JSON. `/worklist` returns items sorted by ROI. `/projections` returns 3 scenarios. `/providers/{npi}` returns correct panel data for each PCP.

### Phase 4: Frontend (depends on Phase 3)

Build order:
1. Tab integration — add "Attribution Surveillance" tab to existing navigation
2. Sub-navigation within the surveillance tab
3. `PanelOverview.tsx` — Key metric cards
4. `AttributionTimeline.tsx` — 12-month hero chart (this is the most complex visualization)
5. `ChangeEventTable.tsx` — Event log with filtering
6. `ProviderPanels.tsx` — Provider card grid with sparklines
7. `ProviderDetail.tsx` — Single provider full view
8. `RetentionWorklist.tsx` — Dense sortable table with expandable rows
9. `FinancialImpact.tsx` — Cumulative impact charts and ROI summary
10. `QualityImpact.tsx` — Quality measure impact table
11. `ProjectionView.tsx` — Three-scenario comparison
12. `CrossTabLinks.tsx` — Navigation between tabs
13. Connect cross-tab links to Settlement View and Clinical View routes

**Validation checkpoint:** Navigate through all 5 sub-screens. Attribution timeline renders 12 months with correct counts. Provider sparklines match monthly data. Retention worklist is sortable and filterable. Cross-tab links navigate to the correct items in other tabs.

### Phase 5: Demo Walkthrough (depends on Phase 4)

Build order:
1. Add 8 surveillance steps to the demo script JSON (extend or create new)
2. Walkthrough overlay for surveillance-specific screens
3. Auto-navigation between surveillance sub-screens during walkthrough

**Validation checkpoint:** Walk through all 8 steps. Each step highlights the correct area and tells the right story.

---

## 12. Testing Strategy

### Unit Tests

`tests/test_attribution_history.py`:
- 12 snapshots exist with correct months
- Member counts are consistent (each month = prior + new - lost)
- All member_ids exist in members.csv
- All provider NPIs exist in providers.csv
- Change events are internally consistent (no member attributed after a terminal loss without a recovery event)
- At least 1 save story (loss + recovery for same member)
- At least 1 cascade pattern (4+ losses for a single provider in 3-month window)
- Total change events in plausible range (80-120)
- Net population change is positive (1-3%)
- Financial impact values are non-zero and use real member cost data

`tests/test_surveillance_engine.py`:
- Monthly snapshots have correct derived fields (churn_rate, cumulative_impact)
- Provider panel summaries have correct panel sizes matching December snapshot
- Retention worklist is sorted by ROI descending
- All worklist items have non-zero financial_impact and recovery_probability
- Three projection scenarios: Scenario B shared_savings > A > C
- Quality impact summary covers at least 3 measures
- Cross-tab connections: at least 1 settlement discrepancy, at least 1 clinical schedule overlap
- Churn by classification sums match total change event count
- Churn by quarter sums match total change event count

### Integration Tests

- Full flow: generate history → analyze → verify all API endpoints return correct data
- Cross-tab consistency: a member in the retention worklist with `has_upcoming_appointment=true` should have a valid appointment in the clinical schedule
- Cross-tab consistency: a member referenced in `settlement_attribution_discrepancies` should appear in the reconciliation StepResult
- Financial consistency: sum of all change event financial impacts should equal the cumulative_financial_impact in the last monthly snapshot

### Manual Test: Demo Walkthrough

Walk through the 8-step demo script and verify:
- Attribution timeline shows realistic 12-month pattern with visible Q1 spike
- The cascade provider's card has a warning badge
- The save story shows loss and recovery events with correct dates
- Retention worklist ROI values are plausible (1x-15x range)
- Quality impact table shows rate changes that make clinical sense
- Projections produce a clear financial case for intervention
- Cross-tab links navigate to the correct items in the Settlement and Clinical views

---

## 13. Resource Constraints

No additional infrastructure beyond what the Platform demo and Clinical View already use.

- **No new Python dependencies.** The surveillance engine uses pandas for data analysis and the existing provenance data structures.
- **No database.** Attribution history is a JSON file. Surveillance analysis is computed once and cached in memory.
- **Memory:** The attribution history (~12 snapshots × 1,000 members × ~200 bytes per entry) adds ~2.4MB. The SurveillanceResult is comparable. Total additional memory: < 10MB.
- **Startup time:** SurveillanceEngine initialization and analysis should complete in < 3 seconds.
- **Frontend charting:** Use the same charting library already in the Platform demo (Recharts if React, or d3 if the existing UI uses it). The attribution timeline is the most complex chart — 12-month area chart with overlay bars. All other charts are standard bar/line/table.

---

## 14. Relationship to the CLAUDE.md

Add the following to the existing CLAUDE.md at the project root:

```
## Attribution Surveillance Tab

Added after the Clinical View. See `Attribution_Surveillance_Dashboard_Implementation_Plan.md` for full specification.

### Key Architectural Rules
- The surveillance engine is a READ-ONLY analysis layer. It never modifies PipelineResult or attribution_history.json.
- Import and reuse AttributionRisk from engine/brief_engine.py — do NOT duplicate risk scoring logic.
- Financial impact for each change event must use the member's ACTUAL cost data from step_4, not average estimates.
- The attribution history is a SIMULATION, not a re-run of the attribution engine. This is by design and should be transparent in the UI.
- Cross-tab links must use real member_ids and navigate to actual items in the Settlement and Clinical views.
- All monetary values are formatted with $ signs, comma separators, and 2 decimal places.
- The retention worklist is sorted by ROI descending. This is the most important sort order — it ensures the highest-value retention actions surface first.
```
