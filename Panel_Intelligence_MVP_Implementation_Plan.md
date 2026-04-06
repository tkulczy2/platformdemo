# VBC Panel Intelligence MVP — Clinical View Implementation Plan

## For Claude Code Implementation as an Extension of the VBC Demo Tool

---

## 1. What This Is

This plan adds a **Clinical View** tab to the existing VBC Transparent Calculation Demo Tool. The Clinical View demonstrates the Panel Intelligence product concept: a forward-looking clinical action layer that uses the Platform's calculation engine to generate pre-visit briefs, surface attribution risk, and recommend gap closure and retention actions.

The Clinical View is **not a separate application.** It is a new tab in the existing React frontend that shares the same backend data, calculation engine, and API layer. It reads from the same synthetic data generated in Phase 1, consumes the same calculation engine output from Phase 2, and adds new API endpoints and frontend components.

**What the Clinical View demonstrates:**

- A one-week synthetic patient schedule showing upcoming appointments
- Per-patient pre-visit briefs with prioritized clinical actions
- Attribution risk indicators with retention recommendations
- Quality measure gap closure opportunities with contract-aware prioritization
- HCC recapture identification
- A "week in review" summary showing aggregate statistics
- One patient who appears in BOTH the clinical view and the reconciliation view, connecting the two product surfaces

**What the Clinical View does NOT demonstrate (deferred):**

- Real-time alert engine
- Panel management dashboard
- EHR integration (SMART on FHIR, CDS Hooks)
- Provider feedback loop (except one scripted interaction in the demo)
- Multi-contract views

---

## 2. Dependencies on Existing Demo Tool

**This plan assumes the following are already built and working:**

- `generator/` — Synthetic data generation (1,000 members, 50 providers, 100K+ claims)
- `engine/` — Calculation pipeline producing StepResult objects with full provenance
  - `step_2_attribution.py` — Attribution assignments with member-level detail
  - `step_3_quality.py` — Quality measure status per member (numerator/denominator/gap)
  - `step_4_cost.py` — Per-member PMPM and service category decomposition
  - `step_6_reconciliation.py` — Payer comparison with discrepancy identification
- `api/` — FastAPI endpoints for calculation results and drill-down
- `frontend/` — React UI with dashboard, drill-down, and reconciliation views
- `data/synthetic/` — All CSV files and JSON files generated
- `data/contracts/sample_mssp_contract.json` — Contract configuration

**If any of these are not complete, stop. Build the Platform demo first.**

---

## 3. Architecture

### How the Clinical View Fits

```
Existing Demo Tool
├── Tab: Settlement View (existing)
│   ├── Upload → Contract Config → Dashboard → Drill-down → Reconciliation
│   └── Uses: engine/pipeline.py → api/routes_*.py → frontend/components/*
│
└── Tab: Clinical View (NEW — this plan)
    ├── Weekly Schedule → Patient Brief → Brief Drill-down → Week in Review
    └── Uses:
        ├── engine/ (existing — reads StepResult output, no changes needed)
        ├── generator/clinical_schedule.py (NEW — generates the week's schedule)
        ├── engine/brief_engine.py (NEW — assembles briefs from engine output)
        ├── api/routes_clinical.py (NEW — clinical view endpoints)
        └── frontend/src/components/clinical/ (NEW — clinical view UI)
```

### Key Principle: Read-Only Consumer of the Platform Engine

The Clinical View **never modifies** the calculation engine or its output. It reads StepResult objects from the existing pipeline and transforms them into clinical presentations. If the calculation engine changes, the Clinical View's data source changes automatically.

The brief engine (`brief_engine.py`) is a **transformation layer**, not a calculation layer. It:
1. Reads attribution MemberDetail from step_2 output → extracts attribution status and risk indicators
2. Reads quality measure MemberDetail from step_3 output → extracts open gaps per patient
3. Reads cost MemberDetail from step_4 output → extracts cost trajectory and drivers
4. Reads discrepancy data from step_6 output → identifies the crossover patient
5. Combines all of the above into a BriefResult data structure per patient per encounter

---

## 4. Project Structure (New Files Only)

```
vbc-demo/
├── generator/
│   └── clinical_schedule.py           # NEW: One-week schedule generator
│
├── engine/
│   └── brief_engine.py                # NEW: Pre-visit brief assembly
│
├── api/
│   └── routes_clinical.py             # NEW: Clinical view API endpoints
│
├── frontend/src/
│   └── components/
│       └── clinical/                  # NEW: Clinical view UI
│           ├── ClinicalView.tsx       # Tab container and navigation
│           ├── WeeklySchedule.tsx     # Week-at-a-glance schedule view
│           ├── DailySchedule.tsx      # Single day's patient list
│           ├── PatientBrief.tsx       # Full pre-visit brief display
│           ├── BriefDrilldown.tsx     # Provenance drill-down for brief items
│           ├── WeekInReview.tsx       # Aggregate statistics summary
│           ├── AttributionRisk.tsx    # Attribution risk indicator component
│           ├── GapCard.tsx            # Individual quality gap display
│           ├── HccCard.tsx            # Individual HCC opportunity display
│           ├── CostContext.tsx        # Cost trajectory gauge
│           └── FeedbackModal.tsx      # Provider feedback interaction (demo)
│
├── data/
│   └── synthetic/
│       └── weekly_schedule.json       # NEW: Generated schedule for the demo week
│
└── tests/
    ├── test_clinical_schedule.py      # NEW
    └── test_brief_engine.py           # NEW
```

---

## 5. Phase 1: Synthetic Schedule Generator

### File: `generator/clinical_schedule.py`

Generate a one-week patient schedule (Monday through Friday) for the demo. This is a **curated** schedule, not a random sample. Each day is designed to tell a specific part of the product story.

### Schedule Design

The schedule covers **one week: Monday through Friday** at a single practice with **3 providers** (selected from the existing provider roster — pick 3 PCPs).

**Total encounters for the week: 45-55** (9-11 per day, split across 3 providers). This is realistic for a small primary care practice.

#### Day-by-Day Narrative Arc

**Monday — "Baseline Day" (10 patients)**
- Purpose: Establish what a normal day looks like. Briefs are short and straightforward.
- Patient mix:
  - 6 patients with 0–1 open quality gaps (routine visits, brief is minimal)
  - 3 patients with 2 open gaps (shows prioritization within the brief)
  - 1 patient with 0 gaps but an HCC recapture opportunity (introduces HCC concept)
- Attribution risk: All 10 patients have stable attribution (green indicators)
- Narrative: "This is what Panel Intelligence looks like on a quiet day. Even routine encounters have value — that HCC recapture on patient #7 is worth documenting."

**Tuesday — "Gap Closure Opportunity Day" (11 patients)**
- Purpose: Show the quality gap closure workflow in depth.
- Patient mix:
  - 4 patients with 1 open gap each (different measures — HbA1c, BP, colorectal, depression)
  - 3 patients with 2-3 open gaps (shows prioritization scoring)
  - 2 patients with 0 gaps (contrast — brief confirms "nothing to do here")
  - 1 patient with 4 open gaps AND high cost trajectory (introduces cost context)
  - **1 CROSSOVER PATIENT** — this patient has an open quality gap AND appears as a discrepancy in the reconciliation view (the payer excluded them from the measure denominator, but the Platform's calculation includes them)
- Attribution risk: 10 patients stable, 1 patient with moderate risk (yellow indicator)
- Narrative: "Tuesday is where the clinical team starts seeing real value. The brief prioritizes gap closures by financial impact — closing the colorectal screening gap on Mrs. Chen is worth more to the contract than the depression screening on Mr. Park because of the measure weights."

**Wednesday — "Attribution Risk Day" (10 patients)**
- Purpose: Introduce the attribution surveillance story.
- Patient mix:
  - 5 patients with stable attribution and 0-1 gaps (routine)
  - 3 patients with **elevated attribution risk** (yellow/red indicators)
    - Patient A: Has been visiting a competing PCP outside the network; plurality is shifting. Brief includes the attribution note.
    - Patient B: Has an enrollment gap — dropped off Medicare for 2 months and re-enrolled. Attribution continuity is uncertain.
    - Patient C: Is a new attribution pickup — wasn't attributed in the prior period, now is. Brief notes this is a new panel member.
  - 2 patients with moderate gaps and stable attribution
- Narrative: "Wednesday is when the panel manager pays attention. Three patients are at risk. Patient A needs a retention visit scheduled. Patient B's enrollment gap means we need to verify their eligibility. Patient C is new to our panel — this is the first visit where we can establish the care relationship."

**Thursday — "High-Cost Patient Day" (11 patients)**
- Purpose: Show the cost context and utilization summary sections of the brief.
- Patient mix:
  - 6 patients with routine profiles
  - 2 patients with **high cost trajectory** (top decile)
    - Patient D: Recent inpatient admission + 2 ED visits in 90 days. Brief shows utilization timeline and flags avoidable ED utilization.
    - Patient E: High pharmacy spend driven by specialty medications. Brief shows pharmacy cost breakdown.
  - 2 patients with elevated attribution risk (reinforces Wednesday's theme)
  - 1 patient with 3 quality gaps + high cost (compound complexity)
- Narrative: "Thursday demonstrates that the brief isn't just about quality checkboxes. The cost context tells the provider that Patient D's two recent ED visits are driving the panel's PMPM above benchmark, and a care plan to manage their chronic condition could avoid future utilization."

**Friday — "Week in Review Day" (10 patients)**
- Purpose: Lighter patient load + the week-in-review summary screen.
- Patient mix:
  - 7 routine patients (0-1 gaps, stable attribution)
  - 2 patients with moderate gaps
  - 1 patient who the demo user will interact with via the **provider feedback** feature (marking a recommendation as "patient declined")
- Narrative: "Friday wraps the week. After the last patient, the team reviews the Week in Review screen — aggregate statistics on gaps addressed, attribution risk across the panel, projected quality score improvement, and the one discrepancy that connects back to the settlement reconciliation."

### Schedule Data Structure

Output file: `data/synthetic/weekly_schedule.json`

```json
{
  "schedule_week": {
    "start_date": "2025-10-20",
    "end_date": "2025-10-24",
    "practice_name": "Meridian Primary Care Associates",
    "providers": [
      {
        "npi": "1234567890",
        "name": "Dr. Sarah Chen",
        "specialty": "Family Medicine",
        "panel_size": 342
      },
      {
        "npi": "2345678901",
        "name": "Dr. James Rivera",
        "specialty": "Internal Medicine",
        "panel_size": 298
      },
      {
        "npi": "3456789012",
        "name": "Dr. Priya Patel",
        "specialty": "Family Medicine",
        "panel_size": 315
      }
    ]
  },
  "days": [
    {
      "date": "2025-10-20",
      "day_name": "Monday",
      "narrative_theme": "Baseline Day",
      "appointments": [
        {
          "appointment_id": "APT-001",
          "time": "08:30",
          "member_id": "MBR-XXXXXX",
          "provider_npi": "1234567890",
          "appointment_type": "Follow-up",
          "duration_minutes": 20,
          "demo_role": "routine_low_gap",
          "demo_notes": "Routine visit, 1 open gap (blood pressure). Establishes baseline brief experience."
        }
      ]
    }
  ]
}
```

### Member Selection Logic

The schedule generator must select real members from `data/synthetic/members.csv` who match the required patient profiles for each day. Selection criteria:

1. Run the existing calculation pipeline to get current attribution status, quality gap counts, cost data, and discrepancy flags for all 1,000 members
2. For each appointment slot in the schedule template, find a member from the dataset who matches the required profile:
   - `routine_low_gap`: Attributed, 0-1 open quality gaps, cost below 75th percentile, stable attribution
   - `moderate_gap`: Attributed, 2-3 open quality gaps
   - `high_gap`: Attributed, 4+ open quality gaps
   - `hcc_opportunity`: Attributed, diagnosis on problem list not captured in current-year claims
   - `attribution_risk_competing`: Attributed, but has significant visit volume with a non-ACO provider
   - `attribution_risk_enrollment`: Attributed, but has an enrollment gap in the eligibility data
   - `attribution_new`: Not attributed in a simulated prior period, now attributed
   - `high_cost`: Attributed, YTD cost in top 10%, recent inpatient or ED utilization
   - `crossover_patient`: Attributed, has at least one quality discrepancy in the reconciliation step (payer disagrees on measure status)
   - `feedback_patient`: Attributed, has an open gap that is plausible for "patient declined" (e.g., colorectal screening)

3. Each selected member should only appear ONCE in the weekly schedule (no duplicate appointments)
4. Distribute patients across the 3 providers roughly evenly (3-4 per provider per day)
5. Appointment times should be realistic: start at 08:00-08:30, appointments every 20-30 minutes, lunch break 12:00-13:00, last appointment by 16:00

**IMPORTANT:** The member selection depends on calculation engine output. This means the schedule generator must be run AFTER the calculation pipeline has been executed at least once. The generator should:
1. Load the PipelineResult (or the relevant StepResult objects)
2. Classify all 1,000 members by profile type
3. Select members that best fit each day's requirements
4. Write the schedule JSON

### Validation Criteria

After running the schedule generator:
- `data/synthetic/weekly_schedule.json` exists and is valid JSON
- Contains exactly 5 days (Monday-Friday)
- Contains 45-55 total appointments
- All `member_id` values exist in `members.csv`
- All `provider_npi` values match one of the 3 selected providers
- No duplicate `member_id` across the entire week
- Exactly 1 appointment has `demo_role: "crossover_patient"`
- Exactly 1 appointment has `demo_role: "feedback_patient"`
- At least 3 appointments have `demo_role` containing "attribution_risk"

---

## 6. Phase 2: Brief Engine

### File: `engine/brief_engine.py`

The brief engine transforms Platform calculation output into patient-level clinical briefs. It is a **read-only transformation layer** — it never modifies the underlying data or calculation results.

### Data Classes

```python
@dataclass
class PriorityAction:
    """One of the top 3 actions for the encounter."""
    rank: int                           # 1, 2, or 3
    action_text: str                    # Clinical language: "Order FIT kit for colorectal screening"
    reason_text: str                    # "Closes 1 of 3 remaining quality gaps"
    category: str                       # "gap_closure", "hcc_recapture", "attribution_retention", "cost_management"
    measure_id: str | None              # e.g., "colorectal_screening" (null if not measure-related)
    financial_impact: float | None      # Estimated dollar impact on contract
    closable_this_visit: bool           # Can this action be completed in one encounter?
    provenance: dict                    # Link back to StepResult for drill-down

@dataclass
class QualityGap:
    """An open quality measure gap for this patient."""
    measure_id: str
    measure_name: str                   # Clinical language, NOT HEDIS jargon
    action_needed: str                  # "Complete colorectal cancer screening (FIT kit or colonoscopy)"
    closable_this_visit: bool
    days_remaining: int                 # Days until performance period close
    financial_weight: float             # Contract weight for this measure
    priority_score: float               # Composite: financial_weight × urgency × closability
    provenance: dict                    # StepResult reference for drill-down

@dataclass
class HccOpportunity:
    """A potential HCC recapture opportunity."""
    condition_name: str                 # "Type 2 Diabetes Mellitus"
    icd10_code: str                     # "E11.9"
    hcc_category: str                   # "HCC 19"
    estimated_raf_impact: float         # e.g., 0.105
    evidence_source: str                # "Problem list" or "Prior year claims"
    last_captured_date: str             # When this was last captured in claims
    provenance: dict

@dataclass
class UtilizationEvent:
    """A recent utilization event for the timeline."""
    event_date: str
    event_type: str                     # "ED Visit", "Inpatient Admission", "Specialist Visit"
    setting: str                        # "Emergency Department", "Acute Inpatient", etc.
    primary_diagnosis: str              # Clinical language
    cost: float
    avoidable_flag: bool                # Was this flagged as potentially avoidable?
    provenance: dict

@dataclass
class AttributionRisk:
    """Attribution risk assessment for this patient."""
    status: str                         # "stable", "moderate_risk", "high_risk", "new_attribution"
    stability_score: float              # 0.0 to 1.0 (1.0 = very stable)
    risk_factors: list[str]             # Human-readable risk factor descriptions
    recommended_action: str | None      # "Schedule retention visit" or null if stable
    competing_provider: dict | None     # {name, npi, visit_count} if applicable
    days_since_last_visit: int
    visits_this_year: int
    provenance: dict

@dataclass
class CostContext:
    """Cost trajectory context for the brief."""
    ytd_cost: float
    expected_cost: float                # Risk-adjusted expectation
    cost_status: str                    # "below_expected", "at_expected", "above_expected"
    cost_ratio: float                   # ytd_cost / expected_cost
    top_cost_driver: str | None         # "Inpatient admissions" if above expected
    pmpm: float
    benchmark_pmpm: float
    provenance: dict

@dataclass
class PatientBrief:
    """Complete pre-visit brief for one patient encounter."""
    # Header
    appointment_id: str
    member_id: str
    member_demographics: dict           # {age, sex, zip (last 3 digits only)}
    appointment_date: str
    appointment_time: str
    provider_name: str
    provider_npi: str
    contract_name: str
    performance_period_end: str
    days_remaining_in_period: int

    # Attribution
    attribution_risk: AttributionRisk

    # Priority Actions (top 3)
    priority_actions: list[PriorityAction]  # Exactly 3 (or fewer if nothing to recommend)

    # Quality Gaps
    quality_gaps: list[QualityGap]      # All open gaps, sorted by priority_score desc
    total_gap_count: int
    closable_this_visit_count: int

    # HCC Opportunities
    hcc_opportunities: list[HccOpportunity]

    # Utilization
    recent_utilization: list[UtilizationEvent]  # Last 90 days, sorted by date desc

    # Cost
    cost_context: CostContext

    # Demo metadata
    demo_role: str                      # From the schedule: what story does this patient tell?
    is_crossover_patient: bool          # Does this patient also appear in reconciliation view?
    crossover_discrepancy: dict | None  # If crossover: the reconciliation discrepancy detail
    is_feedback_patient: bool           # Is this the patient for the feedback demo interaction?
```

### Brief Assembly Logic

```python
class BriefEngine:
    """
    Assembles PatientBrief objects from Platform calculation output.

    Usage:
        engine = BriefEngine(pipeline_result, contract_config, schedule)
        briefs = engine.generate_all_briefs()
        brief = engine.generate_brief(appointment_id)
    """

    def __init__(self, pipeline_result: PipelineResult, contract_config: dict, schedule: dict):
        """
        pipeline_result: Output of the existing calculation pipeline
        contract_config: The sample_mssp_contract.json
        schedule: The weekly_schedule.json
        """
        # Index pipeline output by member_id for fast lookup
        self._attribution_by_member = self._index_step_by_member(pipeline_result, "attribution")
        self._quality_by_member = self._index_step_by_member(pipeline_result, "quality")
        self._cost_by_member = self._index_step_by_member(pipeline_result, "cost")
        self._reconciliation = pipeline_result.reconciliation
        self._contract = contract_config
        self._schedule = schedule

    def generate_brief(self, appointment_id: str) -> PatientBrief:
        """Generate a single brief for one appointment."""
        appointment = self._find_appointment(appointment_id)
        member_id = appointment["member_id"]

        attribution_risk = self._assess_attribution_risk(member_id)
        quality_gaps = self._get_quality_gaps(member_id)
        hcc_opportunities = self._identify_hcc_opportunities(member_id)
        recent_utilization = self._get_recent_utilization(member_id)
        cost_context = self._get_cost_context(member_id)
        crossover = self._check_crossover(member_id)

        priority_actions = self._prioritize_actions(
            attribution_risk, quality_gaps, hcc_opportunities, cost_context
        )

        return PatientBrief(
            appointment_id=appointment_id,
            member_id=member_id,
            # ... assemble all fields
        )
```

### Priority Action Ranking Logic

The top 3 priority actions are selected from all possible actions across categories, ranked by a composite score:

```
priority_score = (financial_impact × 0.4) + (clinical_urgency × 0.3) + (closability × 0.2) + (time_pressure × 0.1)
```

Where:
- `financial_impact`: Normalized 0-1 based on the action's estimated dollar impact on the contract
- `clinical_urgency`: 1.0 for overdue screenings, 0.8 for HCC recapture, 0.6 for attribution retention, 0.4 for cost management
- `closability`: 1.0 if completable in this encounter (e.g., order a test), 0.5 if requires referral, 0.3 if requires multi-visit plan
- `time_pressure`: Days remaining in performance period, normalized (fewer days = higher score)

Actions that are NOT closable in this visit can still appear in the top 3 if their financial impact is high enough (e.g., "Refer for colonoscopy — closes colorectal screening gap worth $X to the contract"). But closable actions get a significant boost.

### Attribution Risk Assessment Logic

The brief engine calculates an attribution risk score for each patient based on data available in the existing calculation output:

1. **Visit recency**: Days since last visit with the attributed provider. > 180 days = high risk factor
2. **Visit frequency**: Number of qualifying visits this year with attributed provider. < 2 = risk factor
3. **Competing provider visits**: Does the patient have qualifying visits with non-ACO providers? If competing provider visit count >= attributed provider visit count, high risk
4. **Enrollment continuity**: Any enrollment gaps in the current performance year? Gap = risk factor
5. **New vs. established**: Was this patient attributed in the prior period? New attribution = flag (not risk, but noteworthy)

Score calculation:
```
base_score = 1.0
if days_since_last_visit > 180: base_score -= 0.3
if visits_this_year < 2: base_score -= 0.2
if competing_visits >= attributed_visits: base_score -= 0.4
if enrollment_gap: base_score -= 0.2
stability_score = max(0.0, base_score)
```

Status mapping:
- stability_score >= 0.7: "stable" (green)
- stability_score >= 0.4: "moderate_risk" (yellow)
- stability_score < 0.4: "high_risk" (red)
- New attribution (not in prior period): "new_attribution" (blue)

### HCC Identification Logic

Compare the patient's diagnosis codes from the EHR problem list (in `clinical_screenings.csv` or a diagnoses column in claims data) against current-year claims:

1. Collect all ICD-10 codes associated with the patient from any historical source (prior-year claims, problem list)
2. Map each to HCC categories using a simplified HCC mapping table (include the top 30 most common HCCs)
3. Check whether each HCC-relevant diagnosis appears in current-year claims
4. If a diagnosis was captured in prior years but NOT in current-year claims, flag it as a recapture opportunity
5. Estimate RAF impact using a simplified RAF coefficient table

**IMPORTANT:** The HCC mapping table and RAF coefficients should be stored as a JSON configuration file (`data/contracts/hcc_mapping.json`), not hardcoded. Include:
- ICD-10 code → HCC category mapping (top 30 HCCs)
- HCC category → RAF coefficient (approximate values, clearly labeled as illustrative)
- HCC category → condition name (human-readable)

### Clinical Language Translation

The brief engine translates ALL analytics terminology into clinical language. This translation must be applied consistently:

| Analytics Term | Clinical Term in Brief |
|---|---|
| "Attribution" | "Panel assignment" or "care relationship" |
| "Attribution risk" | "At risk of leaving your panel" |
| "HEDIS measure" | "[Specific screening/test name]" |
| "Numerator/Denominator" | "Completed/Due for" |
| "Quality gap" | "Screening due" or "Care action needed" |
| "PMPM" | "Monthly care costs" |
| "HCC recapture" | "Condition to document" |
| "RAF score impact" | "Affects expected care needs assessment" |
| "Shared savings" | "Contract performance" |
| "Performance period" | "Contract year" |

**Implement this as a translation dictionary in `engine/brief_engine.py` that is applied to all outward-facing text strings.**

### Crossover Patient Logic

One patient in the schedule is flagged as the crossover patient — they appear in both the Clinical View (with an open quality gap) and the Reconciliation View (with a quality measure discrepancy). The brief engine must:

1. Identify this patient from the schedule (`demo_role: "crossover_patient"`)
2. Find their discrepancy in the reconciliation StepResult
3. Include the discrepancy detail in the brief: "Note: Your organization's calculation shows this patient is eligible for [measure]. The payer's settlement report excludes them. This discrepancy is documented in the Settlement Reconciliation view."
4. The provenance drill-down for this patient's gap should link to the reconciliation discrepancy data, enabling the demo presenter to click through from the clinical view to the reconciliation view

### Validation Criteria

After building the brief engine:
- `BriefEngine.generate_all_briefs()` returns a brief for every appointment in the schedule
- Every brief has exactly 0-3 priority actions (never more than 3)
- Every brief has an attribution risk assessment with a valid status
- Quality gaps are sorted by priority_score descending
- The crossover patient's brief includes the crossover discrepancy detail
- All text in the brief uses clinical language (no "HEDIS", "PMPM", "attribution", "numerator", "denominator")
- Run a text search across all generated brief text for forbidden terms — fail if any are found

---

## 7. Phase 3: API Endpoints

### File: `api/routes_clinical.py`

Add new endpoints to the existing FastAPI application. Register these routes in `api/main.py`.

### Endpoints

```
GET /api/clinical/schedule
    Returns the full weekly schedule with day-level narrative themes.
    Response: The weekly_schedule.json structure.

GET /api/clinical/schedule/{date}
    Returns a single day's schedule with appointment list.
    Response: One day from the schedule with appointments.

GET /api/clinical/brief/{appointment_id}
    Returns the full PatientBrief for one appointment.
    Response: Complete PatientBrief as JSON (all fields from the dataclass).
    IMPORTANT: This is the main data endpoint for the brief UI.

GET /api/clinical/brief/{appointment_id}/drilldown/{item_type}/{item_id}
    Returns provenance detail for a specific item in the brief.
    item_type: "gap", "hcc", "utilization", "attribution", "cost", "priority_action"
    item_id: The specific gap/hcc/event identifier
    Response: The provenance dict from the relevant item, expanded with full
    StepResult detail including contract clauses, code references, and data references.
    This powers the three-panel drill-down when a user clicks on a brief item.

GET /api/clinical/week-summary
    Returns aggregate statistics for the week.
    Response: See Week in Review specification below.

POST /api/clinical/feedback/{appointment_id}
    Records provider feedback on a brief recommendation.
    Body: { "item_type": "gap", "item_id": "colorectal_screening", "feedback": "patient_declined", "note": "Patient declined screening — will revisit at next annual" }
    Response: Updated brief with the feedback recorded and statistics adjusted.
    NOTE: This only needs to work for the one feedback_patient in the demo.
    Store feedback in memory (not persistent). It resets when the server restarts.
```

### Integration with Existing API

In `api/main.py`, add:
```python
from api.routes_clinical import router as clinical_router
app.include_router(clinical_router, prefix="/api/clinical", tags=["clinical"])
```

The clinical endpoints should initialize the BriefEngine once (on first request or at startup) using the existing PipelineResult. The BriefEngine instance can be cached in-memory since the underlying data doesn't change during a demo session.

---

## 8. Phase 4: Frontend — Clinical View UI

### Design Direction

Refer to the design-principles skill for the overall aesthetic. For the Clinical View specifically:

**Personality: Warmth & Approachability with Data & Analysis undertones.** The clinical view is consumed by providers — it should feel warmer and more approachable than the settlement reconciliation view (which targets analysts and CFOs). But it still displays data, so it needs the precision of an analytics tool.

**Color foundation:** Cool foundation (slate/blue-gray base) with a warm accent. Use teal or a muted green as the primary accent — it reads as "clinical" without being the stereotyped healthcare blue.

**Key visual elements:**
- Attribution status indicators: Green (stable), Yellow (moderate risk), Red (high risk), Blue (new to panel)
- Priority action cards: Visually dominant, large, scannable. The top 3 actions should be the first thing the eye lands on.
- Quality gap table: Dense but readable. Monospace for numbers. Sortable columns.
- Utilization timeline: Horizontal timeline with event markers. Inpatient = red marker, ED = orange, Specialist = gray.
- Cost gauge: Simple horizontal bar or arc. Below/At/Above expected with color coding.

### Tab Integration

Add a tab to the existing top-level navigation:

```
[Settlement View]  [Clinical View]
```

When the user clicks "Clinical View", the entire content area below the tabs switches to the clinical view components. The tab should be visually distinct but consistent with the existing tab style.

### Screen 1: Weekly Schedule (`WeeklySchedule.tsx` + `DailySchedule.tsx`)

The landing screen for the Clinical View tab. Displays the week at a glance.

**Layout:**
- Top: Practice name, week date range, provider roster (names + panel sizes)
- Below: 5 day columns (Monday-Friday), each showing:
  - Day name and date
  - Narrative theme label (subtle, e.g., "Baseline Day" in muted text)
  - Appointment count badge
  - List of appointments, each showing:
    - Time
    - Patient identifier (age/sex, de-identified — e.g., "72F" not a name, per HIPAA demo hygiene)
    - Provider name
    - Mini attribution status dot (green/yellow/red/blue)
    - Gap count badge (e.g., "3 gaps" in a small pill)
  - Click on any appointment → navigates to the PatientBrief screen

**Interaction:** Click on a day header to expand it into the DailySchedule view (full-width, more detail per appointment). Click on any patient row to open the brief.

### Screen 2: Patient Brief (`PatientBrief.tsx`)

This is the core screen of the Clinical View. It displays the full pre-visit brief for one patient encounter.

**Layout — follows the brief content structure from Section 7.1 of the product plan:**

**Header Bar:**
- Left: Patient demographics (age/sex), appointment date/time, provider name
- Center: Attribution status indicator (colored dot + label: "Stable" / "At Risk" / "New to Panel")
- Right: Days remaining in contract year (countdown-style, e.g., "73 days remaining")
- Background: Subtle tint matching attribution status color

**Priority Actions Section (visually dominant):**
- 1-3 large cards, stacked vertically
- Each card shows:
  - Rank number (1, 2, 3) in a large circle
  - Action text in bold (clinical language)
  - Reason text in regular weight below
  - Category tag (small pill: "Screening Due", "Condition to Document", "Retention Visit")
  - "Can close today" badge if closable_this_visit is true
  - Click anywhere on the card → opens BriefDrilldown for that action
- If no actions to recommend, show a single card: "No priority actions for this encounter. Routine visit."

**Quality Gaps Section:**
- Table with columns: Measure (clinical name), Action Needed, Closable Today? (checkmark/X), Days Remaining, Priority (high/medium/low)
- Sorted by priority_score descending
- Each row is clickable → opens BriefDrilldown for that gap
- Below table: summary line "X of Y gaps can be closed in this encounter"

**HCC Opportunities Section:**
- Only displayed if hcc_opportunities is non-empty
- Card per opportunity: Condition name, ICD-10 code (monospace), "Document if clinically appropriate"
- Each card is clickable → opens BriefDrilldown

**Recent Utilization Section:**
- Horizontal timeline for the last 90 days
- Event markers: circles on the timeline at event dates
  - Color: Red = inpatient, Orange = ED, Blue = specialist, Gray = other
  - Size: proportional to cost (within reason)
- Below timeline: list of events with date, type, diagnosis, cost
- Avoidable events flagged with a subtle warning indicator
- Each event is clickable → opens BriefDrilldown

**Cost Context Section:**
- Horizontal bar gauge: "Below Expected — At Expected — Above Expected"
- Patient's position marked on the gauge
- If above expected: one line showing the top cost driver
- Muted, not visually dominant — cost is context, not the primary action

**Attribution Note (conditional):**
- Only displayed when attribution_risk.status is NOT "stable"
- Yellow or red banner at the bottom of the brief
- One sentence explanation + recommended action
- For "new_attribution": Blue banner, informational tone ("New to your panel — first visit opportunity")

**Crossover Banner (conditional):**
- Only displayed for the crossover patient
- A distinctive banner (perhaps with a link icon) that says:
  "This patient has a discrepancy in the Settlement Reconciliation view. [View in Settlement Tab →]"
- Clicking the link switches to the Settlement View tab and navigates to the relevant discrepancy

**Feedback Button (conditional):**
- Only displayed for the feedback patient (or could be displayed on all briefs but only functional for the feedback patient in the demo)
- Small button on each priority action / gap: "Mark as addressed" or "Patient declined"
- Clicking opens the FeedbackModal

### Screen 3: Brief Drill-down (`BriefDrilldown.tsx`)

When a user clicks on any item in the brief (a priority action, a quality gap, an HCC opportunity, a utilization event), this component opens showing the provenance chain — **using the same three-panel pattern as the existing Settlement View drill-down.**

**Layout: Three vertical panels side by side**

| Panel 1: Contract Language | Panel 2: Interpretation + Data | Panel 3: Code |
|---|---|---|
| The specific contract clause governing this item. For a quality gap: the measure specification language. For attribution risk: the attribution methodology clause. | Plain-English interpretation of the logic, plus the specific data rows that fed the determination. Patient-level detail with source file references. | The Python function that executed the logic, with the relevant lines highlighted. |

**This is the same pattern as the existing drill-down component.** If possible, reuse the existing DrilldownView component and feed it the provenance data from the brief item. The data structure (ContractClause, DataReference, CodeReference) is identical — it's just sourced from the BriefEngine's provenance instead of the PipelineResult directly.

**Key difference from the Settlement drill-down:** The clinical view drill-down should include a header line in clinical language explaining what the user is looking at: "Why is colorectal screening showing as due for this patient?" Then the three panels show the evidence.

### Screen 4: Week in Review (`WeekInReview.tsx`)

Accessible via a "Week in Review" button/link on the Weekly Schedule screen. Displays aggregate statistics for the demo week.

**Layout: Dashboard-style summary with narrative sections**

**Top Section — Key Numbers:**
- Total encounters this week: N
- Encounters with attributed patients: N (% of total)
- Quality gaps addressable this week: N across N patients
- Projected gap closures (if all addressable gaps were closed): N
- Attribution risk patients seen this week: N

**Quality Impact Section:**
- Current quality scorecard (from Platform engine output) — bar chart showing each measure's current rate vs. target
- "If all addressable gaps identified this week were closed" — overlay showing projected improvement
- Table: measure-by-measure breakdown of gaps identified, gaps closable this week, projected rate improvement, and financial impact

**Attribution Section:**
- Panel attribution summary: Total attributed members, members at risk, members newly attributed
- This week's at-risk patients: list with risk factors and recommended retention actions
- Narrative text: "3 patients seen this week have elevated attribution risk. If all three complete a retention visit, the projected attribution retention rate for the panel improves from X% to Y%."
- Estimated financial impact of attribution churn: "Each lost attributed member costs approximately $X in expected shared savings contribution based on the current contract parameters."

**Cost Section:**
- Average PMPM for patients seen this week vs. panel benchmark
- High-cost patients seen: count and aggregate cost
- Avoidable utilization identified: count and estimated avoidable cost

**Crossover Section:**
- "Settlement Reconciliation Connection" — highlight the crossover patient
- Brief narrative: "Patient [demographics] seen on Tuesday has an open [measure] gap. Your organization's calculation includes this patient in the measure denominator. The payer's settlement report does not. If this discrepancy is resolved in your favor, the measure rate improves by X percentage points and the quality bonus impact is $Y."
- Link to the reconciliation view for this specific discrepancy

**Feedback Section (if feedback was submitted during the demo):**
- Show the feedback interaction: "Dr. [name] marked [measure] as 'Patient Declined' for patient [demographics]. This feedback adjusts the projected gap closure rate from X% to Y% — reflecting clinical reality rather than theoretical maximum."
- This section only appears if the demo user used the feedback feature

### Component: FeedbackModal (`FeedbackModal.tsx`)

A simple modal that appears when the demo user clicks "Mark as addressed" or "Patient declined" on a brief item.

**Options:**
- "Completed" — Gap was closed during the encounter
- "Patient declined" — Patient was offered but declined
- "Clinically inappropriate" — Recommendation not applicable for this patient
- "Already addressed" — Data is stale; this was already done
- Optional free-text note field

**On submit:**
- POST to `/api/clinical/feedback/{appointment_id}`
- Close the modal
- Update the brief to show the feedback inline (strikethrough on the gap, with the feedback reason)
- The Week in Review statistics should reflect the feedback

**In the demo, this only needs to work for the one feedback patient.** For other patients, the button can either be hidden or display a tooltip: "In the full product, providers can submit feedback on any recommendation."

---

## 9. Phase 5: Demo Narrative and Guided Walkthrough

### Guided Demo Mode

Add an optional guided walkthrough mode that overlays the Clinical View with narrative prompts. This is for the demo presenter to use when walking through the product with a prospective provider organization.

**Implementation:** A simple step-by-step overlay system (not a full tour library — keep it lightweight).

Each step shows:
- A highlighted area of the screen
- A narrative text box with 2-3 sentences explaining what the viewer is seeing
- "Next" and "Back" buttons

### Demo Script (12 steps)

**Step 1: Weekly Schedule Overview**
Highlight: The full weekly schedule screen
Narrative: "This is what your analytics team's output looks like when it reaches the clinical workflow. The Platform's calculation engine — the same one that audits your payer settlements — generates a pre-visit brief for every attributed patient on today's schedule."

**Step 2: Monday Baseline**
Highlight: Monday's appointment list
Narrative: "Monday is a typical day. Most patients have stable panel assignments and one or two care actions. The brief keeps things simple — your providers spend 15 seconds reviewing it and know exactly what to prioritize."

**Step 3: First Brief — Routine Patient**
Highlight: A Monday patient's brief (open it)
Narrative: "This is a standard brief. One open screening gap, stable panel assignment, costs in line with expectations. The provider sees one action: 'Complete blood pressure screening.' That's it."

**Step 4: Tuesday Crossover Patient**
Highlight: The crossover patient's brief
Narrative: "This patient has an open quality gap — but there's something else. See the banner at the bottom? Your Platform calculation includes this patient in the colorectal screening measure. The payer's settlement report excluded them. That's real money — and the same engine that flagged it for your finance team is now telling the provider to order the screening."

**Step 5: Drill-Down on a Gap**
Highlight: Three-panel drill-down for the crossover patient's gap
Narrative: "Click any recommendation and you see the same provenance chain as the Settlement View: the contract language, the data, the code. The provider doesn't need this level of detail — but your analytics team can audit every recommendation."

**Step 6: Wednesday Attribution Risk**
Highlight: A high-risk attribution patient's brief
Narrative: "This patient has been seeing another provider outside the network. The visit pattern is shifting — three visits with the competing provider this year versus two with yours. The brief surfaces this: 'At risk of leaving your panel. A qualifying visit today strengthens the care relationship.'"

**Step 7: Attribution Risk Detail**
Highlight: The attribution note in the brief
Narrative: "The analytics team configured the attribution logic in the Platform. Panel Intelligence translates that into action: the provider knows to prioritize this visit, the panel manager knows to schedule a follow-up, and the finance team knows the dollar impact if we lose this patient."

**Step 8: Thursday High-Cost Patient**
Highlight: A high-cost patient's brief with utilization timeline
Narrative: "This patient has two ED visits in the last 90 days and cost in the top decile. The brief shows the utilization timeline and the cost context — the provider can see the pattern and build a care plan to prevent the next ED visit."

**Step 9: Provider Feedback**
Highlight: The feedback patient's brief with the feedback button
Narrative: "Not every recommendation is appropriate. Here, the provider marks 'Patient declined' for the colorectal screening. The system records the feedback — the gap stays open in the measure calculation, but the team knows it's been addressed and isn't a care gap, it's a patient preference."

**Step 10: Week in Review**
Highlight: The Week in Review summary screen
Narrative: "At the end of the week, the panel management team sees the aggregate picture: how many gaps were addressable, how many patients were at attribution risk, what the projected quality improvement would be if all recommendations were acted on."

**Step 11: Crossover Connection**
Highlight: The crossover section in Week in Review
Narrative: "And here's where the two products connect. The settlement discrepancy your finance team identified? It's the same patient your provider saw on Tuesday. One engine, two audiences, one source of truth."

**Step 12: Closing**
Highlight: The tab bar showing both Settlement View and Clinical View
Narrative: "This is what it looks like when your analytics infrastructure reaches the point of care. The same calculation engine that audits your payer settlements generates the clinical intelligence your providers use every day. Your analytics team built it once — and it serves every stakeholder in the organization."

### Implementation Notes for the Walkthrough

- Store the demo script as a JSON array in `frontend/src/data/demo_script.json`
- Each step specifies: a route to navigate to (if needed), an element selector to highlight, and the narrative text
- The overlay should be a semi-transparent backdrop with the highlighted area cut out
- Steps that require navigation (e.g., opening a specific patient's brief) should auto-navigate when "Next" is clicked
- The walkthrough should be toggleable — a "Start Demo" button on the Clinical View and a way to exit at any time
- Keep the walkthrough implementation simple: a React context that tracks the current step and renders the overlay. Do not use a third-party tour library.

---

## 10. Build Order

**Strict sequential dependencies. Do not skip ahead.**

### Phase 1: Schedule Generator (depends on existing Phase 1-2 completion)

Prerequisites: `generator/generate.py` has been run, `data/synthetic/` is populated, and the calculation pipeline produces valid PipelineResult.

Build order:
1. `data/contracts/hcc_mapping.json` — HCC mapping table and RAF coefficients
2. `generator/clinical_schedule.py` — Schedule generation logic
3. Run the schedule generator and validate output
4. `tests/test_clinical_schedule.py` — Validate schedule constraints

**Validation checkpoint:** `data/synthetic/weekly_schedule.json` exists and passes all validation criteria from Phase 1 above.

### Phase 2: Brief Engine (depends on Phase 1)

Build order:
1. `engine/brief_engine.py` — Data classes first (all the @dataclass definitions)
2. `engine/brief_engine.py` — BriefEngine class: `__init__` and indexing logic
3. `engine/brief_engine.py` — `_assess_attribution_risk()` method
4. `engine/brief_engine.py` — `_get_quality_gaps()` method with clinical language translation
5. `engine/brief_engine.py` — `_identify_hcc_opportunities()` method
6. `engine/brief_engine.py` — `_get_recent_utilization()` method
7. `engine/brief_engine.py` — `_get_cost_context()` method
8. `engine/brief_engine.py` — `_prioritize_actions()` method
9. `engine/brief_engine.py` — `_check_crossover()` method
10. `engine/brief_engine.py` — `generate_brief()` and `generate_all_briefs()` methods
11. `tests/test_brief_engine.py` — Test all methods

**Validation checkpoint:** `BriefEngine.generate_all_briefs()` returns valid briefs for all appointments. No forbidden analytics terms in any brief text. Crossover patient brief includes discrepancy detail.

### Phase 3: API Endpoints (depends on Phase 2)

Build order:
1. `api/routes_clinical.py` — All endpoints
2. Register routes in `api/main.py`
3. Test all endpoints via FastAPI docs (http://localhost:8000/docs)

**Validation checkpoint:** All 6 endpoints return valid JSON. `/brief/{id}` returns a full PatientBrief. `/brief/{id}/drilldown/gap/{gap_id}` returns provenance with contract clauses, data references, and code references.

### Phase 4: Frontend (depends on Phase 3)

Build order:
1. Tab integration — add "Clinical View" tab to existing navigation
2. `WeeklySchedule.tsx` + `DailySchedule.tsx` — Schedule display
3. `AttributionRisk.tsx`, `GapCard.tsx`, `HccCard.tsx`, `CostContext.tsx` — Reusable components
4. `PatientBrief.tsx` — Full brief layout (the core screen)
5. `BriefDrilldown.tsx` — Provenance drill-down (reuse existing pattern)
6. `FeedbackModal.tsx` — Feedback interaction
7. `WeekInReview.tsx` — Aggregate statistics
8. Crossover patient link (Clinical View → Settlement View navigation)

**Validation checkpoint:** Navigate through the full demo flow: schedule → brief → drill-down → back → week in review. Crossover link navigates to the correct reconciliation discrepancy. Feedback modal updates the brief.

### Phase 5: Demo Walkthrough (depends on Phase 4)

Build order:
1. `frontend/src/data/demo_script.json` — 12-step script
2. Walkthrough overlay component (highlight + narrative)
3. Step navigation logic (auto-navigate to routes as needed)
4. "Start Demo" button integration

**Validation checkpoint:** Walk through all 12 steps. Each step highlights the correct area, displays the narrative, and navigates correctly.

---

## 11. Testing Strategy

### Unit Tests

`tests/test_clinical_schedule.py`:
- Schedule JSON structure validation
- No duplicate member_ids across the week
- Correct day count (5) and appointment count range (45-55)
- All member_ids exist in members.csv
- All demo_role values are valid
- Crossover patient exists exactly once
- Feedback patient exists exactly once

`tests/test_brief_engine.py`:
- Brief generation for each demo_role type
- Attribution risk scoring: verify score calculation matches the formula
- Quality gap prioritization: verify sort order matches priority_score
- Clinical language translation: verify no forbidden terms in output
- Crossover patient: verify discrepancy detail is populated
- HCC identification: verify at least one opportunity is found for the hcc_opportunity patient
- Priority action count: verify 0-3 actions per brief (never more)
- Empty case handling: verify brief generation for a patient with no gaps, no risk, no HCC (should produce a minimal brief)

### Integration Tests

- Full flow: generate schedule → generate all briefs → verify every appointment has a valid brief
- API: hit each endpoint and verify response schema
- Crossover: verify the crossover patient's member_id appears in both the clinical brief response and the reconciliation discrepancy list

### Manual Test: Demo Walkthrough

Walk through the 12-step demo script and verify:
- Each screen renders without errors
- Brief content is clinically sensible (not garbage data)
- Drill-down provenance shows real contract language, real data references, real code references
- Crossover link navigates correctly between tabs
- Feedback modal works for the feedback patient
- Week in Review statistics are mathematically consistent with the individual briefs

---

## 12. Resource Constraints

This runs on a personal laptop alongside the existing demo tool. No additional infrastructure.

- **No new dependencies beyond what the Platform demo already uses.** Python 3.11+, FastAPI, React 18, TypeScript, Tailwind, pandas. The brief engine uses pandas for data indexing — no new libraries needed.
- **No database.** The schedule is a JSON file. Briefs are generated on-demand from in-memory PipelineResult. Feedback is stored in a Python dict that resets on server restart.
- **No external APIs.** HCC mapping and RAF coefficients are local JSON files.
- **Memory:** The brief engine caches indexed PipelineResult data. For 1,000 members this is negligible (< 50MB additional).
- **Startup time:** The BriefEngine initialization (indexing PipelineResult by member) should take < 2 seconds.
- **Brief generation time:** A single brief should generate in < 100ms. All 50 briefs for the week should generate in < 3 seconds.
