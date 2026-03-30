# VBC Transparent Calculation Demo Tool

## What This Is

A fully interactive demo tool that embodies the core thesis of a VBC Performance Intelligence Platform: **once payer and provider agree on a set of data inputs and contract language, a neutral calculation layer can transparently compute performance metrics — and every number can be traced back to its source data, governing contract language, and executing code.**

Users upload data (claims, eligibility, clinical records, provider rosters) and contract language (attribution rules, quality measure specs, benchmark parameters). The tool runs a transparent calculation pipeline and produces performance metrics with full provenance. A pre-built payer settlement report with intentional discrepancies enables a reconciliation walkthrough.

The primary audience is potential provider customers (VPs of Population Health, CFOs, VBC Contract Analysts). This must feel like a working tool, not a mockup.

---

## Key Architectural Principle

**Provenance is not a feature — it IS the product.**

Every calculation step must produce a `StepResult` (defined in `engine/provenance.py`) containing:
- `contract_clauses`: The contract language excerpt(s) governing this calculation
- `code_references`: The module, function, and line range that executed the logic
- `logic_summary`: Plain-English explanation of how the contract clause was interpreted
- `member_details`: Per-member outcome with the specific data rows that drove the decision
- `data_quality_flags`: Issues encountered (missing data, conflicts, duplicates)

**If a number can't be traced to its source, the implementation is wrong.** No calculation function should return raw values — everything goes through the `StepResult` provenance wrapper.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data generation | Python 3.11+ | Faker, numpy, pandas |
| Calculation engine | Python 3.11+ | pandas for data ops |
| Provenance tracking | Python dataclasses + JSON | Serializable, inspectable |
| API | FastAPI | localhost:8000 |
| Frontend | React 18 + TypeScript | Vite dev server on localhost:5173 |
| Styling | Tailwind CSS | |
| Charts | Recharts | |
| Code display | react-syntax-highlighter | For the code panel in drill-down view |
| Data format | CSV (input), JSON (API/provenance) | Human-inspectable at every layer |

**No database.** All data held in-memory from CSV files. No cloud services. No Docker. Everything runs on a personal laptop.

---

## Running Locally

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Generate synthetic data (first time only)
python -m generator.generate

# Start backend
uvicorn api.main:app --reload --port 8000 &

# Start frontend
cd frontend && npm run dev &
```

API docs: http://localhost:8000/docs
UI: http://localhost:5173

---

## Project Structure

```
vbc-demo/
├── CLAUDE.md                          # This file
├── README.md
├── requirements.txt
├── start.sh                           # Startup script
│
├── data/
│   ├── synthetic/                     # Generated demo data (9 CSVs + 2 JSONs)
│   ├── contracts/                     # Contract language templates
│   └── uploads/                       # User-uploaded data lands here
│
├── generator/                         # Phase 1: Synthetic data generation
│   ├── config.py                      # GenerationConfig dataclass
│   ├── generate.py                    # Orchestrator — run this
│   ├── members.py                     # 1,000 synthetic Medicare beneficiaries
│   ├── providers.py                   # 50 ACO providers (20 PCP, 30 specialist)
│   ├── eligibility.py                 # Enrollment periods with gaps
│   ├── claims.py                      # Professional, facility, pharmacy claims
│   ├── clinical.py                    # Labs, screenings, vitals from EHR
│   ├── settlement.py                  # Fake payer settlement report
│   └── discrepancies.py              # Plants intentional discrepancies
│
├── engine/                            # Phase 2: Calculation engine
│   ├── pipeline.py                    # Orchestrates steps 1-6
│   ├── provenance.py                  # StepResult, DataReference, etc.
│   ├── data_loader.py                 # CSV → pandas + validation
│   ├── data_quality.py                # Completeness scoring
│   ├── step_1_eligibility.py
│   ├── step_2_attribution.py
│   ├── step_3_quality.py
│   ├── step_4_cost.py
│   ├── step_5_settlement.py
│   ├── step_6_reconciliation.py
│   └── measures/                      # Quality measure implementations
│       ├── base.py                    # BaseMeasure abstract class
│       ├── hba1c_control.py
│       ├── blood_pressure.py
│       ├── breast_cancer_screening.py
│       ├── colorectal_screening.py
│       └── depression_screening.py
│
├── api/                               # Phase 3: FastAPI backend
│   ├── main.py                        # App + CORS config
│   ├── routes_data.py                 # Upload + validation
│   ├── routes_contract.py             # Contract configuration
│   ├── routes_calculate.py            # Run pipeline
│   ├── routes_drilldown.py            # Provenance drill-down
│   └── routes_reconciliation.py       # Reconciliation endpoints
│
├── frontend/                          # Phase 3: React UI
│   └── src/
│       ├── components/
│       │   ├── upload/                # Screen 1: Data upload + validation
│       │   ├── contract/              # Screen 2: Contract configuration
│       │   ├── dashboard/             # Screen 3: Results dashboard
│       │   ├── drilldown/             # Screen 4: Three-panel provenance view
│       │   └── reconciliation/        # Screen 5: Payer comparison
│       ├── hooks/
│       ├── types/
│       └── utils/
│
└── tests/
```

---

## Build Order

**Strict sequential dependencies — do not skip ahead.**

### Phase 1: Synthetic Data Generator (must complete first)

Build order within phase:
1. `generator/config.py` — GenerationConfig dataclass with all parameters
2. `generator/members.py` — Member roster (no dependencies)
3. `generator/providers.py` — Provider roster (no dependencies)
4. `generator/eligibility.py` — Enrollment records (depends on members)
5. `generator/claims.py` — All claim types (depends on members, providers, eligibility)
6. `generator/clinical.py` — Labs, screenings, vitals (depends on members, providers)
7. `generator/discrepancies.py` — Modify generated data to plant discrepancies
8. `generator/settlement.py` — Fake payer report (depends on all above)
9. `generator/generate.py` — Orchestrator that runs everything in order

**Validation:** After running `python -m generator.generate`, verify:
- `data/synthetic/` contains 9 CSV files and 2 JSON files
- `members.csv` has 1,000 rows
- `claims_professional.csv` has ~45,000-55,000 rows
- `discrepancy_manifest.json` documents all planted discrepancies
- All member_ids in claims/clinical/eligibility exist in members.csv
- All NPIs in claims exist in providers.csv

### Phase 2: Calculation Engine

Build order within phase:
1. `engine/provenance.py` — DataReference, ContractClause, CodeReference, MemberDetail, StepResult, PipelineResult dataclasses
2. `engine/data_loader.py` — Load CSVs into pandas DataFrames, parse dates, validate schemas
3. `engine/data_quality.py` — Completeness scoring per file
4. `engine/step_1_eligibility.py` — Enrollment continuity + exclusions
5. `engine/step_2_attribution.py` — MSSP two-step plurality attribution
6. `engine/measures/base.py` — BaseMeasure abstract class
7. `engine/measures/hba1c_control.py` — First measure implementation (establishes the pattern)
8. `engine/measures/` — Remaining 4 measures (follow the same pattern)
9. `engine/step_3_quality.py` — Orchestrates all measures, computes composite
10. `engine/step_4_cost.py` — PMPM calculation with maturity adjustments
11. `engine/step_5_settlement.py` — Benchmark comparison, gates, savings
12. `engine/step_6_reconciliation.py` — Platform vs. payer comparison
13. `engine/pipeline.py` — Orchestrator that runs steps 1-6

**Validation:** Run `python -c "from engine.pipeline import CalculationPipeline; ..."` to verify the full pipeline produces a PipelineResult with all 6 steps populated.

### Phase 3: API + Frontend

1. `api/main.py` + all route modules (thin wrappers over engine)
2. Frontend: upload screen → contract config → dashboard → drill-down → reconciliation

### Phase 4: Polish

Guided demo mode, PDF export, edge case handling.

---

## Critical Rules

### Data Rules
- All synthetic data uses the member_id format `MBR-XXXXXX` (6 digits, zero-padded)
- All provider NPIs are 10-digit strings starting with `1`
- Claim IDs: `CLM-P-XXXXXXXX` (professional), `CLM-F-XXXXXXXX` (facility), `CLM-RX-XXXXXXXX` (pharmacy)
- All dates are `YYYY-MM-DD` format in CSVs
- **Never generate or store real PHI — everything is synthetic**
- The random seed (default 42) must produce deterministic, reproducible data

### Calculation Engine Rules
- Every calculation function returns a `StepResult`, never raw values
- Every `StepResult` must include `contract_clauses` linking to the governing contract language
- Every `MemberDetail` must include `data_references` pointing to specific source file rows
- The pipeline is stateless — given the same data + contract, it produces identical output
- Claims maturity adjustments must be visible (confidence bands), not hidden
- Quality measure rates must match standard HEDIS calculation methodology (denominator - exclusions = eligible; numerator / eligible = rate)

### Discrepancy Rules
- The generator plants exactly these discrepancies (configurable in `config.py`):
  - 23 attribution discrepancies (12 platform-only, 7 payer-only, 4 different-provider)
  - 15 quality measure discrepancies (8 EHR-only data, 4 payer exclusions, 3 screening conflicts)
  - 8 cost discrepancies (5 run-out timing, 3 amount differences)
- All discrepancies are documented in `data/synthetic/discrepancy_manifest.json`
- The reconciliation engine (step 6) must independently discover ALL planted discrepancies
- The manifest file is for validation only — the engine must not read it

### UI Rules
- The **three-panel drill-down** (contract language | interpretation + data | code) is the signature UX — every metric on the dashboard must support it
- Every number on the dashboard is clickable → drill-down
- Maturity-adjusted numbers always show confidence bands
- The reconciliation view must show the total financial impact of all discrepancies
- "Load Demo Data" and "Load Sample Contract" buttons must be prominent — this is a demo tool

### Performance Rules
- Full pipeline execution: < 10 seconds for 1,000 members
- API response times: < 500ms for all endpoints
- Total memory footprint: < 500MB
- No external network calls — everything local

---

## Domain Glossary

Terms used throughout the codebase:

| Term | Meaning |
|------|---------|
| **ACO** | Accountable Care Organization — a group of providers that shares financial risk |
| **Attribution** | The process of assigning a patient to a specific provider/ACO based on utilization patterns |
| **Plurality** | The attribution method where the provider with the most qualifying visits gets the patient |
| **PMPM** | Per Member Per Month — standard unit for cost measurement (total cost / member-months) |
| **Member-months** | Sum of months each member was enrolled (1,000 members × 12 months = 12,000 member-months if all enrolled full year) |
| **HEDIS** | Healthcare Effectiveness Data and Information Set — standard quality measures |
| **Numerator** | Members who satisfied a quality measure (e.g., got their screening done) |
| **Denominator** | Members eligible for a quality measure (e.g., right age/sex/diagnosis) |
| **Exclusion** | Members removed from a measure's denominator (e.g., hospice patients) |
| **Shared savings** | The portion of cost savings that the ACO receives when it beats its benchmark |
| **Benchmark** | The expected PMPM cost level set by CMS, based on historical costs |
| **Minimum savings rate (MSR)** | The threshold the ACO must exceed before earning any savings (e.g., 2%) |
| **Quality gate** | Minimum quality score required to be eligible for shared savings |
| **Claims run-out** | The lag between when a service occurs and when the claim appears in data |
| **Maturity adjustment** | Statistical adjustment to estimate "complete" costs for months with incomplete claims |
| **Settlement** | The final financial reconciliation between payer and provider for a performance year |
| **Reconciliation** | Comparing the platform's calculation to the payer's settlement report |
| **HCC risk score** | CMS Hierarchical Condition Category risk score — predicts expected cost |
| **E&M codes** | Evaluation & Management CPT codes (99201-99215) — office visit billing codes |
| **NPI** | National Provider Identifier — unique 10-digit provider ID |
| **TIN** | Tax Identification Number — identifies the billing entity |
| **MSSP** | Medicare Shared Savings Program — CMS's primary ACO program |
| **FHIR** | Fast Healthcare Interoperability Resources — healthcare data exchange standard |
| **PHI** | Protected Health Information — health data subject to HIPAA |

---

## Contract Parameter Reference

These are the editable parameters in the contract configuration. When a user changes one, the pipeline must re-run the affected steps.

| Parameter | Default | Affects Step | Example Values |
|-----------|---------|-------------|----------------|
| `attribution_method` | `plurality` | 2 | `plurality`, `voluntary_alignment`, `hybrid` |
| `qualifying_cpt_codes` | 99201-99215, 99381-99397, G0438-G0439 | 2 | Any valid CPT codes |
| `tiebreaker` | `most_recent_visit` | 2 | `most_recent_visit`, `alphabetical_npi`, `highest_cost` |
| `provider_filter_step1` | `pcp_only` | 2 | `pcp_only`, `all_aco_participants` |
| `minimum_enrollment_months` | `1` | 1 | `1` through `12` |
| `exclude_esrd` | `true` | 1 | `true`, `false` |
| `measures` | all 5 enabled | 3 | any subset of the 5 measures |
| `measure_weights` | equal (0.20 each) | 3 | any weights summing to 1.0 |
| `conflict_resolution` | `most_recent_clinical` | 3 | `most_recent_clinical`, `claims_only`, `ehr_only` |
| `cost_basis` | `allowed_amount` | 4 | `allowed_amount`, `paid_amount` |
| `include_pharmacy` | `false` | 4 | `true`, `false` |
| `runout_months` | `3` | 4 | `3`, `6`, `12` |
| `benchmark_pmpm` | `1187.00` | 5 | any dollar amount |
| `minimum_savings_rate` | `0.02` | 5 | `0.01` through `0.05` |
| `shared_savings_rate` | `0.50` | 5 | `0.40` through `0.75` |
| `quality_gate_threshold` | `0.40` | 5 | `0.25` through `0.70` |

---

## API Endpoint Reference

```
POST   /api/data/upload              Upload CSV data files
GET    /api/data/status              Data validation + quality scores
POST   /api/data/load-demo           Load synthetic demo data

GET    /api/contract                 Current contract configuration
PUT    /api/contract                 Update contract parameters
POST   /api/contract/load-demo       Load sample MSSP contract

POST   /api/calculate                Run the full pipeline, return summary
GET    /api/results/summary          Top-level metrics with drill-down URLs
GET    /api/results/step/{n}         Full StepResult for step n (1-6)

GET    /api/drilldown/member/{id}               Member detail across all steps
GET    /api/drilldown/step/{n}/member/{id}       Member detail for one step
GET    /api/drilldown/step/{n}/members           Paginated member list for a step
GET    /api/drilldown/metric/{name}              Drill into a specific metric

POST   /api/reconciliation/upload    Upload payer settlement report
GET    /api/reconciliation/summary   Discrepancy summary
GET    /api/reconciliation/detail/{category}     Discrepancy detail by category

GET    /api/code/{module}/{function}  Return source code of a calculation function
```

---

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_attribution.py -v

# Run generator and validate output
python -m generator.generate
python -c "
import pandas as pd
m = pd.read_csv('data/synthetic/members.csv')
c = pd.read_csv('data/synthetic/claims_professional.csv')
print(f'Members: {len(m)}, Claims: {len(c)}')
assert len(m) == 1000
assert len(c) > 40000
print('Basic validation passed')
"

# Run full pipeline and check output
python -c "
from engine.pipeline import CalculationPipeline
from engine.data_loader import load_demo_data
from engine.provenance import PipelineResult
import json

data = load_demo_data()
contract = json.load(open('data/contracts/sample_mssp_contract.json'))
payer_report = json.load(open('data/synthetic/payer_settlement_report.json'))

pipeline = CalculationPipeline()
result = pipeline.run(data, contract, payer_report)

print(f'Steps completed: {len(result.steps)}')
print(f'Attributed: {result.final_metrics[\"attributed_population\"]}')
print(f'Quality composite: {result.final_metrics[\"quality_composite\"]}')
print(f'PMPM: {result.final_metrics[\"actual_pmpm\"]}')
print(f'Discrepancies found: {len(result.reconciliation[\"discrepancies\"])}')
print(f'Execution time: {result.total_execution_time_ms}ms')
"
```
