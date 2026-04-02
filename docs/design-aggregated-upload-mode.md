# Design: Aggregated (Provider-Level) Upload Mode for Privacy-Safe Reconciliation

## Context

Payers and providers may be unwilling to share individual-level PHI with a third-party platform. This blocks adoption. We need a mode where both parties upload **provider-level aggregated data** (no member PHI), and the platform reconciles their results, identifies discrepancies, and supports what-if analysis on contract parameters.

This is a **new upload mode** alongside the existing individual-level mode — not a replacement.

## How It Works

Each party (payer and provider) independently runs Steps 1-3 on their own systems using their own member-level data. They then upload **provider-level summaries** to the platform. The platform:

1. Ingests both parties' aggregated results
2. Runs Steps 4-6 (cost aggregation, settlement, reconciliation) on the aggregated data
3. Identifies discrepancies between the two parties at the **provider level**
4. Enables what-if analysis on contract parameters (benchmark, MSR, quality gate, savings rate)
5. Provides provider-level drill-down (not member-level)

## Aggregated CSV Schemas

### `aggregated_attribution.csv` (one row per provider)
```
npi, provider_name, attributed_count, qualifying_visit_count, step1_count, step2_count
1234567890, Dr. Smith, 50, 312, 45, 5
```

### `aggregated_quality.csv` (one row per provider per measure)
```
npi, measure_id, denominator, exclusions, eligible, numerator, rate
1234567890, hba1c_poor_control, 42, 3, 39, 32, 0.821
1234567890, controlling_bp, 38, 2, 36, 28, 0.778
```

### `aggregated_cost.csv` (one row per provider)
```
npi, member_months, total_allowed, total_paid, pmpm_allowed, pmpm_paid, professional_cost, facility_cost, pharmacy_cost
1234567890, 588, 524000.00, 498000.00, 891.16, 846.94, 312000.00, 185000.00, 27000.00
```

### `aggregated_enrollment.csv` (one row per provider)
```
npi, total_members, avg_enrollment_months, members_full_year, members_partial_year
1234567890, 50, 11.2, 45, 5
```

### ACO-level summary row
Each file includes a row with `npi = "ACO-TOTAL"` containing the ACO-wide totals.

## Pipeline Changes

### New: `engine/aggregated_loader.py`
- Loads the 4 aggregated CSVs into an `AggregatedData` dataclass
- Validates schemas, checks that ACO-TOTAL row exists
- Validates that per-provider rows sum to ACO-TOTAL (flags discrepancies)

### New: `engine/aggregated_pipeline.py`
- **Skips Steps 1-3** (pre-computed by each party)
- Ingests attribution/quality/enrollment summaries as "Step 1-3 results"
- **Runs Step 4** on aggregated cost data (sum costs, compute PMPM, apply maturity if monthly breakdown provided)
- **Runs Step 5** normally (settlement is already aggregate-only)
- **Runs Step 6** comparing payer vs provider aggregated results at provider level

### Modified: `engine/provenance.py`
- `MemberDetail` → generalize to `EntityDetail` (can be a member OR a provider)
- Or: keep `MemberDetail` but populate with provider-level entries (member_id = NPI)
- `DataReference` points to aggregated CSV rows instead of individual claim rows

### Modified: `engine/step_6_reconciliation.py`
- New comparison mode: provider-by-provider reconciliation
- For each provider, compare: attributed count, quality rates per measure, cost PMPM
- Identify providers with largest discrepancies
- Aggregate financial impact per provider

## API Changes

### New endpoints
```
POST /api/data/upload-aggregated      Upload aggregated CSV files
POST /api/data/load-demo-aggregated   Load demo aggregated data
GET  /api/data/mode                   Returns "individual" or "aggregated"
```

### Modified endpoints
- `/api/calculate` — detects data mode and runs appropriate pipeline
- `/api/drilldown/metric/{name}` — returns provider-level details in aggregated mode
- `/api/drilldown/step/{n}/members` — returns providers instead of members in aggregated mode

## Frontend Changes

### Upload screen (`DataUpload.tsx`)
- Add toggle/tabs: "Individual Data" vs "Aggregated Data"
- Aggregated mode shows different file expectations (4 summary CSVs)
- "Load Demo Data" works for both modes

### Drill-down (`DrilldownView.tsx`)
- **Sidebar**: Shows provider list instead of member list (NPI + name + count)
- **Center panel**: Shows provider-level aggregates instead of member rows
  - "Dr. Smith (NPI 1234567890): 50 attributed, HbA1c rate 82.1% (32/39)"
  - Source data table shows the aggregated CSV row, not individual claims
- **Left/Right panels**: Unchanged (contract language + code still apply)

### Dashboard (`ResultsDashboard.tsx`)
- Mostly unchanged — same top-level metrics
- Quality scorecard still shows per-measure rates
- Drill-down navigates to provider-level view

### New: Provider comparison view
- Side-by-side: payer's provider-level numbers vs provider's numbers
- Highlight providers with largest discrepancies
- Sort by financial impact

## Files to Create/Modify

### New files
- `engine/aggregated_loader.py` — aggregated CSV loader + validation
- `engine/aggregated_pipeline.py` — pipeline for aggregated mode
- `generator/generate_aggregated.py` — generate demo aggregated CSVs from existing synthetic data
- `data/synthetic/aggregated/` — demo aggregated CSV files
- `frontend/src/components/upload/AggregatedUpload.tsx` — aggregated upload UI

### Modified files
- `engine/provenance.py` — minor: allow provider-level EntityDetail
- `engine/step_6_reconciliation.py` — add provider-level comparison
- `api/routes_data.py` — add aggregated upload endpoints
- `api/routes_calculate.py` — detect mode, run appropriate pipeline
- `api/routes_drilldown.py` — return provider-level drill-down in aggregated mode
- `api/main.py` — add `data_mode` to AppState
- `frontend/src/components/upload/DataUpload.tsx` — add mode toggle
- `frontend/src/components/drilldown/DrilldownView.tsx` — provider-level sidebar + detail
- `frontend/src/components/drilldown/LogicPanel.tsx` — provider-level display
- `frontend/src/api/client.ts` — new API functions

## What-If Analysis Support

In aggregated mode, the user can modify these contract parameters and see recalculated results instantly (no re-upload needed):

| Parameter | Affects | Recalculation |
|-----------|---------|---------------|
| `benchmark_pmpm` | Settlement | Re-run Step 5 only |
| `minimum_savings_rate` | Settlement | Re-run Step 5 only |
| `shared_savings_rate` | Settlement | Re-run Step 5 only |
| `quality_gate_threshold` | Settlement | Re-run Step 5 only |
| `measure_weights` | Quality composite | Re-aggregate quality rates with new weights → Step 5 |
| `cost_basis` | Cost PMPM | Only if both allowed + paid columns uploaded |

Parameters that **cannot** be changed in aggregated mode (require member-level re-run):
- `attribution_method`, `qualifying_cpt_codes`, `tiebreaker` (Step 2)
- `minimum_enrollment_months`, `exclude_esrd` (Step 1)
- `conflict_resolution` (Step 3)
- `runout_months` (Step 4, needs claim-level dates)

The UI should gray out / disable these parameters in the contract editor when in aggregated mode, with a tooltip: "Requires individual-level data to modify."

## Verification Plan

1. Generate aggregated demo data from existing synthetic data
2. Upload aggregated data → verify pipeline runs Steps 4-6
3. Compare results to individual-level pipeline (should match for Steps 5-6)
4. Test provider-level drill-down renders correctly
5. Test what-if: change benchmark → verify settlement recalculates
6. Test reconciliation: upload two different aggregated files → verify discrepancies identified per provider
7. Test mode switching: individual → aggregated → individual without state corruption
8. TypeScript compilation + frontend build
