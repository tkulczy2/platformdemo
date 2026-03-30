# VBC Transparent Calculation Demo Tool — Implementation Plan

## For Claude Code Implementation on a Personal Laptop

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Technology Stack](#2-architecture--technology-stack)
3. [Project Structure](#3-project-structure)
4. [Phase 1: Synthetic Data Generator](#4-phase-1-synthetic-data-generator)
5. [Phase 2: Calculation Engine with Provenance](#5-phase-2-calculation-engine-with-provenance)
6. [Phase 3: Interactive UI](#6-phase-3-interactive-ui)
7. [Phase 4: Demo Narrative & Polish](#7-phase-4-demo-narrative--polish)
8. [Data Schemas](#8-data-schemas)
9. [Provenance Data Model](#9-provenance-data-model)
10. [Contract Language Specification](#10-contract-language-specification)
11. [Testing Strategy](#11-testing-strategy)
12. [Resource Constraints & Performance](#12-resource-constraints--performance)

---

## 1. Project Overview

### What This Tool Is

A fully interactive demo that embodies the core thesis of a VBC Performance Intelligence Platform: **once payer and provider agree on a set of data inputs and contract language, a neutral calculation layer can transparently compute performance metrics — and every number can be traced back to its source data, governing contract language, and executing logic.**

The tool accepts data uploads (claims, eligibility, clinical data, provider rosters) and contract language (attribution rules, quality measure specs, benchmark parameters), then runs a transparent calculation pipeline that produces performance metrics with full provenance. Every output number links back to:

1. **The specific data rows** that fed the calculation
2. **The specific contract language** that governed the logic
3. **The specific code function** that executed the logic

A pre-built "payer settlement report" with intentional discrepancies is included, enabling a reconciliation walkthrough that demonstrates the tool's value proposition.

### Primary Audience

Potential provider customers (VPs of Population Health, CFOs, VBC Contract Analysts). The demo must feel like a working tool, not a mockup.

### Key Design Principles

- **Nothing is a black box.** Every number is drillable to its source.
- **Data messiness is a feature.** The synthetic data includes real-world issues (enrollment gaps, missing fields, duplicate claims, conflicting data sources) because handling these transparently is the point.
- **Contract language is first-class.** The tool shows the contract excerpt, the platform's interpretation, and the code — side by side.
- **Lightweight and local.** Everything runs on a personal laptop. No cloud services, no databases, no Docker. Python + a local web UI.

---

## 2. Architecture & Technology Stack

### Constraints

- Runs entirely on a personal laptop (macOS assumed, but should work on Linux)
- No external databases — all data held in-memory or as flat files
- No cloud services or API keys required
- Total synthetic dataset fits comfortably in RAM (~50MB)
- Calculations complete in seconds, not minutes

### Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Synthetic data generation | Python 3.11+ | Faker, numpy, pandas for realistic data |
| Calculation engine | Python 3.11+ | Readable code is a product requirement; pandas for data manipulation |
| Provenance tracking | Python dataclasses + JSON | Lightweight, serializable, inspectable |
| API layer | FastAPI | Lightweight, async, auto-generates OpenAPI docs |
| Frontend | React 18 + TypeScript | Component-based drill-down UI |
| Styling | Tailwind CSS | Fast iteration, clean defaults |
| Build tooling | Vite | Fast dev server, minimal config |
| Data format | CSV (input), JSON (provenance/API) | Human-inspectable at every layer |

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      React Frontend                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  Upload  │ │ Contract │ │ Results  │ │  Drill-    │  │
│  │  Screen  │ │  Config  │ │Dashboard │ │  Down View │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────┴────────────────────────────────┐
│                   FastAPI Backend                         │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Calculation Pipeline                  │    │
│  │  ┌─────────┐ ┌─────────┐ ┌──────┐ ┌───────────┐ │    │
│  │  │Eligibil.│→│Attrib.  │→│Qual. │→│Cost/PMPM  │ │    │
│  │  └─────────┘ └─────────┘ └──────┘ └───────────┘ │    │
│  │       │           │          │          │         │    │
│  │       └───────────┴──────────┴──────────┘         │    │
│  │                Provenance Collector                │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │           Data Loader (CSV → pandas)              │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
vbc-demo/
├── CLAUDE.md                          # Project context for Claude Code
├── README.md                          # Setup and run instructions
├── requirements.txt                   # Python dependencies
│
├── data/                              # All data lives here
│   ├── synthetic/                     # Generated demo data
│   │   ├── members.csv
│   │   ├── providers.csv
│   │   ├── claims_professional.csv
│   │   ├── claims_facility.csv
│   │   ├── claims_pharmacy.csv
│   │   ├── eligibility.csv
│   │   ├── clinical_labs.csv
│   │   ├── clinical_screenings.csv
│   │   ├── clinical_vitals.csv
│   │   └── payer_settlement_report.json
│   ├── contracts/                     # Contract language templates
│   │   └── sample_mssp_contract.json
│   └── uploads/                       # User-uploaded data lands here
│
├── generator/                         # Phase 1: Synthetic data generation
│   ├── __init__.py
│   ├── generate.py                    # Main entry point
│   ├── config.py                      # Generation parameters
│   ├── members.py                     # Member/patient generation
│   ├── providers.py                   # Provider roster generation
│   ├── claims.py                      # Claims generation (all types)
│   ├── clinical.py                    # Lab results, screenings, vitals
│   ├── eligibility.py                 # Enrollment/eligibility periods
│   ├── settlement.py                  # Fake payer settlement report
│   └── discrepancies.py              # Planted discrepancy logic
│
├── engine/                            # Phase 2: Calculation engine
│   ├── __init__.py
│   ├── pipeline.py                    # Orchestrates all steps
│   ├── provenance.py                  # Provenance tracking dataclasses
│   ├── data_loader.py                 # CSV parsing + validation
│   ├── data_quality.py                # Completeness scoring + flagging
│   ├── step_1_eligibility.py          # Enrollment continuity check
│   ├── step_2_attribution.py          # Attribution assignment
│   ├── step_3_quality.py              # Quality measure calculation
│   ├── step_4_cost.py                 # PMPM + cost analytics
│   ├── step_5_settlement.py           # Benchmark comparison + savings
│   ├── step_6_reconciliation.py       # Platform vs. payer comparison
│   └── measures/                      # Individual quality measure specs
│       ├── __init__.py
│       ├── base.py                    # Abstract measure class
│       ├── hba1c_control.py           # Diabetes: HbA1c Poor Control
│       ├── blood_pressure.py          # Controlling High Blood Pressure
│       ├── breast_cancer_screening.py # Breast Cancer Screening
│       ├── colorectal_screening.py    # Colorectal Cancer Screening
│       └── depression_screening.py    # Depression Screening & Follow-up
│
├── api/                               # Phase 3: FastAPI backend
│   ├── __init__.py
│   ├── main.py                        # FastAPI app + CORS
│   ├── routes_data.py                 # Data upload + validation endpoints
│   ├── routes_contract.py             # Contract config endpoints
│   ├── routes_calculate.py            # Run pipeline + return results
│   ├── routes_drilldown.py            # Provenance drill-down endpoints
│   └── routes_reconciliation.py       # Reconciliation endpoints
│
├── frontend/                          # Phase 3: React UI
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx                    # Router + layout
│       ├── main.tsx                   # Entry point
│       ├── api/                       # API client
│       │   └── client.ts
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx       # Top nav + sidebar
│       │   │   └── StepIndicator.tsx  # Progress through screens
│       │   ├── upload/
│       │   │   ├── DataUpload.tsx     # File upload + validation display
│       │   │   └── DataQualityCard.tsx
│       │   ├── contract/
│       │   │   ├── ContractEditor.tsx  # Contract language + params
│       │   │   └── ClauseCard.tsx      # Individual contract clause
│       │   ├── dashboard/
│       │   │   ├── ResultsDashboard.tsx
│       │   │   ├── MetricCard.tsx      # Clickable metric tile
│       │   │   ├── QualityScorecard.tsx
│       │   │   └── CostChart.tsx
│       │   ├── drilldown/
│       │   │   ├── DrilldownView.tsx   # Three-panel provenance view
│       │   │   ├── ContractPanel.tsx   # Left: contract language
│       │   │   ├── LogicPanel.tsx      # Center: interpretation + data
│       │   │   └── CodePanel.tsx       # Right: code snippet
│       │   └── reconciliation/
│       │       ├── ReconciliationView.tsx
│       │       ├── DiscrepancyTable.tsx
│       │       └── DiscrepancyDetail.tsx
│       ├── hooks/
│       │   ├── useCalculation.ts
│       │   └── useDrilldown.ts
│       ├── types/
│       │   └── index.ts              # TypeScript types matching API
│       └── utils/
│           └── formatters.ts          # Currency, percentage, etc.
│
└── tests/
    ├── test_generator.py
    ├── test_eligibility.py
    ├── test_attribution.py
    ├── test_quality_measures.py
    ├── test_cost.py
    ├── test_settlement.py
    └── test_reconciliation.py
```

---

## 4. Phase 1: Synthetic Data Generator

### Goal

Generate a realistic, internally consistent synthetic dataset representing one performance year of a mid-size ACO operating under an MSSP-style contract. The data must be messy enough to be credible and must include planted discrepancies that the reconciliation engine will surface.

### Generation Parameters (config.py)

```python
@dataclass
class GenerationConfig:
    # Population
    num_members: int = 1000
    num_providers: int = 50
    num_pcp_providers: int = 20          # Subset that are PCPs
    num_specialist_providers: int = 30

    # Time
    performance_year: int = 2025
    performance_period_start: str = "2025-01-01"
    performance_period_end: str = "2025-12-31"
    historical_months: int = 36          # For baseline establishment
    data_as_of_date: str = "2025-10-15"  # Simulates mid-year snapshot

    # Claims volume
    avg_professional_claims_pmpm: float = 4.5
    avg_facility_claims_pmpm: float = 0.8
    avg_pharmacy_claims_pmpm: float = 3.0

    # Data quality issues to inject
    pct_missing_npi: float = 0.02        # 2% of claims missing rendering NPI
    pct_duplicate_claims: float = 0.01   # 1% duplicate claim lines
    pct_enrollment_gaps: float = 0.08    # 8% of members have enrollment gaps
    pct_conflicting_clinical: float = 0.05  # 5% have EHR/claims conflicts

    # Discrepancies to plant (for reconciliation demo)
    num_attribution_discrepancies: int = 23
    num_quality_discrepancies: int = 15
    num_cost_discrepancies: int = 8

    # Random seed for reproducibility
    seed: int = 42
```

### Member Generation (members.py)

Generate 1,000 synthetic members with realistic demographics for a Medicare ACO population.

**Fields:**
- `member_id`: Unique identifier (format: `MBR-{6 digits}`)
- `date_of_birth`: Weighted toward age 65-85 for Medicare population
- `sex`: M/F, roughly equal distribution
- `race_ethnicity`: Distribution matching national Medicare demographics
- `zip_code`: Concentrated in 3-4 geographic areas (simulates a regional ACO)
- `dual_eligible`: Boolean, ~20% of population
- `hcc_risk_score`: Float, range 0.5-4.0, log-normal distribution centered around 1.2
- `pcp_npi`: Assigned PCP from provider roster (plurality assignment will be calculated, this is the "panel" assignment)
- `deceased_date`: Null for most; ~2% have a death date within the performance year

**Realism requirements:**
- Age distribution should reflect Medicare beneficiaries (skewed 65-85, tail to 100)
- Risk scores should correlate with age (older = generally higher risk)
- Dual eligibility should correlate with higher risk scores
- Zip codes should cluster into 3-4 geographic zones representing the ACO's service area
- ~30 members should have characteristics that create attribution edge cases (see Discrepancies section)

### Provider Generation (providers.py)

Generate 50 providers representing the ACO's participating provider roster.

**Fields:**
- `npi`: 10-digit NPI (use realistic format, start with 1)
- `provider_name`: Generated name (Last, First MI format)
- `taxonomy_code`: Valid NUCC taxonomy code
- `specialty`: Derived from taxonomy (Family Medicine, Internal Medicine, Cardiology, etc.)
- `is_pcp`: Boolean, true for Family Medicine, Internal Medicine, Geriatrics
- `practice_location_id`: One of 4-5 practice sites
- `practice_location_name`: Site name
- `tin`: Tax ID number (9 digits), grouped by practice site
- `aco_participant`: Boolean (all true for v1, but field exists for future use)
- `effective_date`: Date provider joined the ACO roster
- `termination_date`: Null for active; 2-3 providers terminated mid-year

**Realism requirements:**
- 20 PCPs, 30 specialists across Cardiology, Endocrinology, Orthopedics, Pulmonology, General Surgery, Nephrology, Neurology, Psychiatry
- 2-3 providers should have taxonomy codes that are ambiguous for PCP classification (e.g., Nurse Practitioner in a primary care setting) — this creates attribution methodology edge cases
- 2-3 providers should have terminated mid-year, creating a scenario where attributed patients may need reassignment

### Eligibility Generation (eligibility.py)

Generate enrollment/eligibility records for all members.

**Fields:**
- `member_id`: FK to members
- `payer_id`: `PAYER-001` for the MSSP contract (single payer for v1)
- `contract_id`: `CONTRACT-MSSP-2025`
- `product_type`: "Medicare FFS" for MSSP
- `enrollment_start_date`: Most members enrolled before the performance year
- `enrollment_end_date`: Null for currently enrolled, date for terminated
- `attribution_eligible`: Boolean (derived from enrollment continuity rules)

**Realism requirements:**
- ~92% of members have continuous enrollment for the full performance year
- ~5% have a gap (disenrolled then re-enrolled) — these are the cases where the contract's enrollment continuity rule matters
- ~3% have enrollment ending mid-year (death, moved, switched plans)
- Enrollment gaps should be realistic: 1-3 months, not arbitrary
- Some members should have multiple eligibility records (one per enrollment span)

### Claims Generation (claims.py)

Generate professional, facility, and pharmacy claims. This is the largest and most complex dataset.

**Professional Claims (claims_professional.csv):**
- `claim_id`: Unique identifier (format: `CLM-P-{8 digits}`)
- `member_id`: FK to members
- `service_date`: Within the performance year (or look-back period for historical)
- `rendering_npi`: Provider who performed the service
- `billing_npi`: May differ from rendering (group billing)
- `place_of_service`: 2-digit POS code (11=Office, 21=Inpatient, 23=ED, etc.)
- `procedure_code`: CPT code
- `procedure_description`: Human-readable description
- `modifier`: CPT modifier if applicable
- `diagnosis_code_1` through `diagnosis_code_4`: ICD-10-CM codes
- `diagnosis_description_1`: Human-readable for primary diagnosis
- `allowed_amount`: Payer-allowed amount
- `paid_amount`: Amount payer actually paid
- `patient_responsibility`: Copay + deductible + coinsurance
- `claim_status`: "paid", "denied", "adjusted"
- `adjudication_date`: Date claim was processed (service_date + lag)
- `data_source`: "payer_claims_feed"

**Claim generation logic:**
- Each member generates ~4.5 professional claims per month
- PCP visits: CPT 99211-99215 (E&M codes), 2-4 per year per member. CRITICAL: These are the claims that drive attribution. Distribute them across PCPs to create plurality patterns.
- Specialist visits: Relevant CPT codes by specialty, frequency driven by diagnoses
- Lab orders: CPT 80000-89999, tied to clinical conditions
- Claims maturity: Apply a realistic run-out curve. For the `data_as_of_date` of Oct 15, 2025:
  - Jan-Jun claims: ~98% complete
  - Jul-Aug claims: ~92% complete
  - Sep claims: ~80% complete
  - Oct claims: ~40% complete (partial month)

**Facility Claims (claims_facility.csv):**
- Similar fields but with `facility_npi`, `admission_date`, `discharge_date`, `drg_code`, `revenue_code`
- Volume: ~0.8 per member per month
- Include 15-20 inpatient admissions, 50-60 ED visits, 100+ outpatient facility claims
- 5-8 30-day readmissions (for avoidable utilization flagging)

**Pharmacy Claims (claims_pharmacy.csv):**
- `claim_id`, `member_id`, `fill_date`, `ndc_code`, `drug_name`, `drug_class`, `days_supply`, `quantity`, `allowed_amount`, `paid_amount`
- Volume: ~3.0 per member per month
- Include statins, diabetes medications, antihypertensives, antidepressants (these feed quality measures like PDC/medication adherence)
- Include gaps in fills for some members (feeds medication adherence calculations)

**Data quality issues to inject across all claim types:**
- 2% of claims: `rendering_npi` is null or invalid
- 1% of claims: Duplicate `claim_id` with identical data (exact duplicates)
- 0.5% of claims: Duplicate `claim_id` with slightly different data (adjusted claims)
- 1% of claims: `service_date` outside the member's enrollment period
- 0.5% of claims: `procedure_code` is invalid or deprecated
- A handful of claims with `allowed_amount` of $0 or negative values

### Clinical Data Generation (clinical.py)

Generate EHR-sourced clinical data that feeds quality measures. This data may conflict with claims data in some cases — which is intentional and important for the demo.

**Lab Results (clinical_labs.csv):**
- `member_id`, `lab_date`, `loinc_code`, `lab_name`, `result_value`, `result_unit`, `reference_range`, `abnormal_flag`, `ordering_npi`, `data_source` ("ehr")
- Key labs: HbA1c (LOINC 4548-4), LDL Cholesterol (LOINC 2089-1), eGFR, Creatinine
- For diabetic members (~15% of population): Generate 1-3 HbA1c results per year
  - ~60% with most recent HbA1c < 8% (controlled)
  - ~25% with most recent HbA1c 8-9% (borderline)
  - ~15% with most recent HbA1c > 9% (poorly controlled)

**Screening Records (clinical_screenings.csv):**
- `member_id`, `screening_date`, `screening_type`, `cpt_code`, `result`, `ordering_npi`, `data_source` ("ehr")
- Types: colonoscopy, mammogram, depression_screening (PHQ-9), tobacco_screening
- For quality measure targets:
  - Colorectal screening (age 45-75): ~65% completion rate
  - Breast cancer screening (female, age 50-74): ~70% completion rate
  - Depression screening (all adults): ~55% completion rate

**Vital Signs (clinical_vitals.csv):**
- `member_id`, `vital_date`, `vital_type`, `value`, `unit`, `provider_npi`, `data_source` ("ehr")
- Types: systolic_bp, diastolic_bp, bmi, weight
- For hypertensive members (~40% of population): Generate 2-4 BP readings per year
  - ~65% with most recent BP < 140/90 (controlled)
  - ~35% with most recent BP >= 140/90 (uncontrolled)

**Planted EHR/Claims conflicts (for reconciliation):**
- 5% of screening records: EHR shows a completed screening (e.g., colonoscopy in clinical_screenings.csv) but there is NO corresponding CPT code in claims. This simulates the common scenario where a screening was performed but the claim was submitted under a different code, or the claim was denied, or the data didn't flow from EHR to payer.
- 3% of lab results: Claims show a lab CPT code was billed, but no result appears in the EHR lab data. Simulates orders that were placed but results not received or not documented.

### Payer Settlement Report Generation (settlement.py)

Generate a fake payer settlement report that the reconciliation engine will compare against. This report represents "what the payer calculated" — and it intentionally diverges from what the platform will calculate.

**File: payer_settlement_report.json**

```json
{
  "report_metadata": {
    "payer": "CMS / Medicare Shared Savings Program",
    "contract_id": "CONTRACT-MSSP-2025",
    "performance_year": 2025,
    "report_date": "2026-03-15",
    "report_type": "preliminary_settlement"
  },
  "attribution": {
    "total_attributed": 871,
    "attributed_by_step1": 743,
    "attributed_by_step2": 128
  },
  "quality": {
    "composite_score": 81.2,
    "measures": {
      "hba1c_poor_control": { "rate": 22.3, "numerator": 38, "denominator": 170 },
      "controlling_bp": { "rate": 64.8, "numerator": 257, "denominator": 396 },
      "breast_cancer_screening": { "rate": 71.4, "numerator": 130, "denominator": 182 },
      "colorectal_screening": { "rate": 63.2, "numerator": 198, "denominator": 313 },
      "depression_screening": { "rate": 52.1, "numerator": 421, "denominator": 808 }
    }
  },
  "cost": {
    "benchmark_pmpm": 1187.00,
    "actual_pmpm": 1142.00,
    "total_benchmark": 12410000,
    "total_actual": 11940000,
    "gross_savings": 470000,
    "minimum_savings_rate": 0.02,
    "savings_rate_achieved": 0.038,
    "shared_savings_rate": 0.50,
    "shared_savings_amount": 235000
  }
}
```

### Discrepancy Planting Strategy (discrepancies.py)

The discrepancies are the stars of the demo. They must be specific, traceable, and realistic.

**Attribution Discrepancies (23 members):**
- **12 members:** Platform attributes them to the ACO; payer does not. Reason: The payer used a different claims run-out window, excluding late-arriving claims that established plurality. The platform's calculation includes these claims because it has access to the provider's EHR encounter data confirming the visits occurred.
- **7 members:** Payer attributes them; platform does not. Reason: The payer included claims from a provider whose ACO participation terminated mid-year. Under the contract's attribution rules, services rendered after the provider's termination date should not count toward plurality.
- **4 members:** Both attribute, but to different providers within the ACO. Reason: Plurality tie between two PCPs, broken differently by the payer (alphabetical by NPI) vs. the platform (most recent visit date). The contract language is ambiguous on tiebreaker methodology.

**Quality Measure Discrepancies (15 instances):**
- **8 members:** Platform counts them in a quality measure numerator; payer does not. Reason: Platform uses EHR lab results (e.g., HbA1c value from clinical_labs.csv) that the payer doesn't have — the payer only sees the CPT code for the lab order, not the result value.
- **4 members:** Payer excludes them from a measure denominator; platform includes them. Reason: The payer applied a denominator exclusion (e.g., hospice enrollment) based on a claims record that doesn't appear in the platform's data feed.
- **3 members:** Disagreement on screening completion. Platform has an EHR screening record; payer has no corresponding claim.

**Cost Discrepancies (8 instances — these aggregate to ~$47K impact):**
- **5 high-cost claims:** Present in the platform's data but not in the payer settlement's cost calculation. Likely reason: claims run-out timing. These claims were adjudicated after the payer's settlement calculation cutoff.
- **3 claims:** Different allowed amounts between the platform's claims feed and the payer's settlement. Likely reason: claims were reprocessed/adjusted after the platform received its data extract.

**CRITICAL: Track all planted discrepancies in a manifest file (`data/synthetic/discrepancy_manifest.json`) that documents exactly what was planted, why, and the expected financial impact. The reconciliation engine should independently discover these — the manifest is for validation only.**

### Generator Entry Point (generate.py)

```python
"""
Run: python -m generator.generate

Generates all synthetic data files to data/synthetic/.
Parameterized via GenerationConfig — modify config.py to change population
size, data quality issues, or discrepancy counts.

The generator is deterministic: same seed produces identical data.
"""
```

**Implementation order within Phase 1:**
1. `config.py` — dataclass with all parameters
2. `members.py` — member roster (no dependencies)
3. `providers.py` — provider roster (no dependencies)
4. `eligibility.py` — enrollment records (depends on members)
5. `claims.py` — all claims types (depends on members, providers, eligibility)
6. `clinical.py` — labs, screenings, vitals (depends on members, providers)
7. `discrepancies.py` — modify generated data to plant discrepancies
8. `settlement.py` — fake payer report (depends on all above + discrepancy decisions)
9. `generate.py` — orchestrator that runs everything in order

---

## 5. Phase 2: Calculation Engine with Provenance

### Goal

Build a calculation pipeline where every step produces not just results, but a complete provenance record. The provenance is not an afterthought — it IS the product.

### Provenance Data Model (provenance.py)

Every calculation step produces a `StepResult` object:

```python
@dataclass
class DataReference:
    """Points to specific rows in a specific source file."""
    source_file: str                    # e.g., "claims_professional.csv"
    row_indices: list[int]              # Specific rows used
    columns_used: list[str]            # Which columns were relevant
    description: str                    # Human-readable: "3 E&M claims from Dr. Smith"

@dataclass
class ContractClause:
    """The contract language governing this calculation step."""
    clause_id: str                      # e.g., "ATTR-1.1"
    clause_text: str                    # The actual contract language
    interpretation: str                 # How the platform interpreted it
    parameters_extracted: dict          # Key-value parameters derived from clause

@dataclass
class CodeReference:
    """Points to the code that executed this logic."""
    module: str                         # e.g., "step_2_attribution"
    function: str                       # e.g., "assign_by_plurality"
    line_range: tuple[int, int]         # Start and end line numbers
    logic_summary: str                  # Plain English: "Count qualifying E&M visits..."

@dataclass
class MemberDetail:
    """Per-member detail for drill-down."""
    member_id: str
    outcome: str                        # e.g., "attributed", "excluded", "in_numerator"
    reason: str                         # Human-readable explanation
    data_references: list[DataReference]  # Source data for this member's outcome
    intermediate_values: dict           # e.g., {"visit_count_provider_A": 3, "visit_count_provider_B": 2}

@dataclass
class StepResult:
    """Complete output of one pipeline step."""
    step_name: str                      # e.g., "attribution"
    step_number: int
    contract_clauses: list[ContractClause]
    code_references: list[CodeReference]
    summary: dict                       # Top-level metrics (e.g., {"attributed_count": 847})
    member_details: list[MemberDetail]  # Per-member provenance
    data_quality_flags: list[dict]      # Issues encountered during this step
    execution_time_ms: int
    timestamp: str                      # ISO 8601

@dataclass
class PipelineResult:
    """Complete output of the full pipeline."""
    steps: list[StepResult]
    final_metrics: dict                 # Aggregated top-level metrics
    reconciliation: dict | None         # Comparison to payer report, if provided
    total_execution_time_ms: int
```

### Pipeline Orchestrator (pipeline.py)

```python
class CalculationPipeline:
    """
    Orchestrates the five-step calculation pipeline.

    Each step receives:
    - The loaded data (DataFrames)
    - The contract configuration
    - Results from prior steps (for dependencies)

    Each step returns a StepResult with full provenance.
    """

    def run(self, data: LoadedData, contract: ContractConfig,
            payer_report: dict | None = None) -> PipelineResult:
        steps = []

        # Step 1: Eligibility
        eligibility_result = determine_eligibility(data, contract)
        steps.append(eligibility_result)

        # Step 2: Attribution (depends on eligibility)
        attribution_result = assign_attribution(
            data, contract, eligibility_result)
        steps.append(attribution_result)

        # Step 3: Quality Measures (depends on attribution)
        quality_result = calculate_quality_measures(
            data, contract, attribution_result)
        steps.append(quality_result)

        # Step 4: Cost / PMPM (depends on attribution)
        cost_result = calculate_cost(
            data, contract, attribution_result)
        steps.append(cost_result)

        # Step 5: Settlement (depends on quality + cost)
        settlement_result = calculate_settlement(
            contract, quality_result, cost_result)
        steps.append(settlement_result)

        # Step 6: Reconciliation (optional, if payer report provided)
        reconciliation = None
        if payer_report:
            reconciliation = reconcile(
                steps, payer_report, data)

        return PipelineResult(
            steps=steps,
            final_metrics=self._aggregate_metrics(steps),
            reconciliation=reconciliation,
            total_execution_time_ms=sum(s.execution_time_ms for s in steps)
        )
```

### Step 1: Eligibility Determination (step_1_eligibility.py)

**Contract clause it implements:**

> "Beneficiaries must have at least one month of enrollment during the performance year and must not be enrolled in a Medicare Advantage plan, have end-stage renal disease, or reside outside the ACO's service area to be eligible for attribution."

**Logic:**
1. Load eligibility records
2. For each member, determine months of continuous enrollment during the performance year
3. Apply exclusion criteria from contract: MA enrollment, ESRD flag (check diagnosis codes for N18.6), service area (check zip codes against ACO service area list)
4. Output: List of eligible members with enrollment months, list of excluded members with reason

**Provenance to capture:**
- For each excluded member: which exclusion criterion triggered, the specific data element (e.g., "ICD-10 code N18.6 on claim CLM-P-00012345 dated 2025-03-14"), the contract clause that requires the exclusion

### Step 2: Attribution (step_2_attribution.py)

**Contract clauses it implements:**

> "Step 1: Assign each eligible beneficiary to the ACO participant (TIN/NPI) that provided the plurality of primary care services, as defined by CPT codes 99201–99215, 99381–99397, and G0438–G0439, during the most recent 12-month period."

> "Step 2: For beneficiaries not assigned in Step 1, assign based on the plurality of primary care services provided by any ACO participant, including specialists who rendered qualifying primary care codes."

> "In the event of a tie in service counts, the beneficiary shall be assigned to the provider whose most recent qualifying service was most recent in time."

**Logic:**
1. Filter claims to qualifying CPT codes (the E&M and wellness visit codes listed in the contract)
2. For each eligible member, count qualifying claims by rendering NPI
3. Group NPIs by TIN (organizational attribution)
4. Step 1: Find plurality provider among PCP-taxonomy providers. If found, attribute.
5. Step 2: For unattributed members, find plurality among ALL ACO providers. If found, attribute.
6. Tiebreaker: If plurality is tied, use most recent service date.
7. Output: Attributed population with assignment details

**Provenance to capture (this is the most critical step for the demo):**
- For each attributed member: the full table of qualifying visits by provider, the plurality calculation, which step (1 or 2) assigned them, the specific claims that drove the assignment
- For each unattributed member: why (no qualifying visits, no ACO provider rendered services, excluded in Step 1)
- For tie cases: the tiebreaker data and resolution
- Flag the 23 members where the platform's attribution differs from the payer report

### Step 3: Quality Measure Calculation (step_3_quality.py)

Implement 5 quality measures. Each measure follows the same pattern: identify denominator → apply exclusions → evaluate numerator → calculate rate.

**Each measure is a class in engine/measures/ that inherits from BaseMeasure:**

```python
class BaseMeasure:
    """Abstract base class for quality measures."""

    measure_id: str                     # e.g., "NQF-0059"
    measure_name: str                   # e.g., "Diabetes: HbA1c Poor Control"
    measure_description: str
    contract_clause: ContractClause     # Contract language for this measure
    data_sources_used: list[str]        # Which CSVs this measure reads from

    def identify_denominator(self, data, attributed_members) -> list[MemberDetail]:
        """Who is eligible for this measure?"""
        raise NotImplementedError

    def apply_exclusions(self, denominator_members, data) -> list[MemberDetail]:
        """Who is excluded and why?"""
        raise NotImplementedError

    def evaluate_numerator(self, eligible_members, data) -> list[MemberDetail]:
        """Who satisfies the measure?"""
        raise NotImplementedError

    def calculate(self, data, attributed_members) -> StepResult:
        """Full calculation with provenance."""
        denominator = self.identify_denominator(data, attributed_members)
        after_exclusions = self.apply_exclusions(denominator, data)
        numerator = self.evaluate_numerator(after_exclusions, data)
        rate = len(numerator) / len(after_exclusions) if after_exclusions else 0
        # ... build StepResult with full provenance
```

**Measures to implement:**

1. **Diabetes: HbA1c Poor Control (NQF-0059 / inverse measure)**
   - Denominator: Attributed members age 18-75 with diabetes diagnosis (ICD-10: E11.x)
   - Exclusions: Hospice, ESRD, pregnancy
   - Numerator: Members whose most recent HbA1c > 9% OR with no HbA1c test during the measurement year
   - Data sources: claims (for diabetes dx), clinical_labs (for HbA1c values)
   - NOTE: This is an inverse measure — LOWER is better. The "rate" is the % with poor control.

2. **Controlling High Blood Pressure (NQF-0018)**
   - Denominator: Attributed members age 18-85 with hypertension diagnosis (ICD-10: I10-I15.x)
   - Exclusions: ESRD, pregnancy, hospice, dialysis, kidney transplant
   - Numerator: Members with most recent BP reading < 140/90
   - Data sources: claims (for hypertension dx), clinical_vitals (for BP readings)

3. **Breast Cancer Screening (NQF-2372)**
   - Denominator: Attributed female members age 50-74
   - Exclusions: Bilateral mastectomy, hospice
   - Numerator: Members with mammogram in the past 27 months
   - Data sources: claims (for mammography CPT codes), clinical_screenings

4. **Colorectal Cancer Screening (NQF-0034)**
   - Denominator: Attributed members age 45-75
   - Exclusions: Total colectomy, hospice, colorectal cancer diagnosis
   - Numerator: Members with colonoscopy in past 10 years OR FIT/FOBT in past year OR CT colonography in past 5 years
   - Data sources: claims (for procedure codes), clinical_screenings

5. **Depression Screening and Follow-Up (NQF-0418)**
   - Denominator: Attributed members age 12+
   - Exclusions: Existing depression/bipolar diagnosis with active treatment
   - Numerator: Members with documented depression screening (PHQ-2 or PHQ-9)
   - Data sources: claims (for screening CPT codes), clinical_screenings

**Quality composite score:**
- Average of the 5 individual measure performance rates (using the contract-specified weighting, default equal weight)
- Apply the CMS quality scoring gates: composite must exceed minimum threshold for the ACO to be eligible for shared savings

### Step 4: Cost and PMPM Calculation (step_4_cost.py)

**Contract clause:**

> "Total cost of care shall be calculated as the sum of all Parts A and B allowed charges for attributed beneficiaries during the performance year, divided by the number of attributed beneficiary-months, expressed as a per-member-per-month (PMPM) amount. Claims with service dates within the performance year that are adjudicated within 3 months of the performance year end shall be included."

**Logic:**
1. Filter claims to attributed members only
2. Categorize claims by service type: inpatient, outpatient, professional, post-acute, pharmacy, other
3. Sum allowed amounts by category
4. Calculate member-months (from eligibility data — each month a member is enrolled counts as 1 member-month)
5. Calculate raw PMPM = total allowed / member-months
6. Apply claims maturity adjustment: since `data_as_of_date` is Oct 15, 2025, claims for recent months are incomplete. Apply the maturity curve to estimate the "complete" cost for months with incomplete claims.
7. Calculate adjusted PMPM with confidence interval based on maturity uncertainty

**Claims maturity model (built into this step):**

```python
# Empirical run-out curve: fraction of claims received by months after service
RUNOUT_CURVE = {
    0: 0.40,   # 40% of claims for current month received
    1: 0.82,   # 82% received within 1 month
    2: 0.92,   # 92% within 2 months
    3: 0.96,   # 96% within 3 months
    6: 0.99,   # 99% within 6 months
    12: 1.00   # 100% within 12 months
}

# For each month's claims:
#   adjusted_cost = raw_cost / maturity_fraction
#   confidence_band = ± (1 - maturity_fraction) * raw_cost
```

**Provenance to capture:**
- PMPM by service category with the claims that feed each category
- Maturity adjustment factor applied to each month
- Confidence band for in-progress months
- Identification of top-cost members with contributing claims

### Step 5: Settlement Calculation (step_5_settlement.py)

**Contract clauses:**

> "The ACO's benchmark shall be $1,187.00 PMPM, as established by CMS based on the ACO's historical cost baseline trended forward."

> "If the ACO's actual PMPM is below the benchmark by more than the minimum savings rate of 2.0%, the ACO shall receive 50% of the gross savings, subject to quality performance gates."

> "The quality performance gate requires a minimum composite quality score of 40% for the ACO to be eligible for any shared savings."

**Logic:**
1. Compare actual PMPM (from Step 4) to benchmark PMPM (from contract)
2. Calculate gross savings = (benchmark - actual) × member-months
3. Check minimum savings rate: (benchmark - actual) / benchmark > 2.0%?
4. Check quality gate: composite quality score > 40%?
5. If both gates passed: shared savings = gross savings × 50%
6. Output: settlement amount with full breakdown

**Provenance to capture:**
- Each component of the settlement calculation with the source (Step 4 output, contract parameter, quality composite from Step 3)
- Clear indication of whether gates were passed/failed and the margin
- The exact contract language for each parameter used

### Step 6: Reconciliation (step_6_reconciliation.py)

**Logic:**
1. Load the payer settlement report JSON
2. For each metric category (attribution, quality measures, cost, settlement):
   - Compare the platform's calculated value to the payer's reported value
   - Calculate the difference (absolute and percentage)
   - Categorize the discrepancy type
   - For member-level metrics (attribution, quality), produce a member-level comparison showing exactly which members differ and why
3. Calculate the total financial impact of all discrepancies
4. Generate a discrepancy summary

**Discrepancy categories:**
- `data_difference`: The platform and payer used different underlying data (e.g., claims that one party has and the other doesn't)
- `methodology_difference`: Both parties have the same data but applied different logic (e.g., different tiebreaker rules)
- `timing_difference`: Discrepancy caused by different claims run-out windows
- `possible_error`: A discrepancy that doesn't have an obvious explanation and may indicate a calculation error
- `specification_ambiguity`: The contract language is ambiguous, and both interpretations are defensible

**Output structure:**

```python
@dataclass
class Discrepancy:
    category: str                       # One of the categories above
    metric: str                         # e.g., "attribution_count", "hba1c_rate"
    platform_value: float
    payer_value: float
    difference: float
    financial_impact: float             # Estimated dollar impact
    affected_members: list[str]         # Member IDs involved
    explanation: str                    # Human-readable explanation
    data_references: list[DataReference]  # Source data supporting platform's position
    contract_clause: ContractClause     # Relevant contract language
    resolution_recommendation: str      # What to do about it
```

---

## 6. Phase 3: Interactive UI

### Goal

Build a React frontend that makes the provenance chain tangible and navigable. The signature interaction is the **three-panel drill-down view**: contract language | interpretation + data | code.

### API Endpoints (FastAPI)

```
POST   /api/data/upload              Upload CSV files
GET    /api/data/status              Data validation status + quality scores
POST   /api/data/load-demo           Load pre-built synthetic data

GET    /api/contract                 Get current contract config
PUT    /api/contract                 Update contract parameters
POST   /api/contract/load-demo       Load sample MSSP contract

POST   /api/calculate                Run the full pipeline
GET    /api/results/summary          Top-level metrics
GET    /api/results/step/{step_num}  Full StepResult for a specific step

GET    /api/drilldown/member/{member_id}         Member-level detail across all steps
GET    /api/drilldown/step/{step_num}/member/{member_id}   Member detail for one step
GET    /api/drilldown/metric/{metric_name}       Drill into a specific metric

POST   /api/reconciliation/upload    Upload payer settlement report
GET    /api/reconciliation/summary   Discrepancy summary
GET    /api/reconciliation/detail/{discrepancy_id}  Full discrepancy detail

GET    /api/code/{module}/{function}  Return the source code of a calculation function
```

### Screen-by-Screen UI Specification

#### Screen 1: Data Upload & Validation

**Layout:** Full-width, card-based

**Components:**
- **File upload zone:** Drag-and-drop area accepting CSV files. Show expected file types with a checklist: Members ☐, Providers ☐, Eligibility ☐, Professional Claims ☐, Facility Claims ☐, Pharmacy Claims ☐, Lab Results ☐, Screenings ☐, Vitals ☐
- **"Load Demo Data" button:** One-click load of synthetic data (prominent, primary action for demo purposes)
- **Data quality dashboard:** After upload, show per-file validation:
  - Row count
  - Date range covered
  - Completeness score (% of expected fields populated)
  - Flagged issues (missing NPIs, invalid codes, duplicates, dates outside enrollment)
  - Visual indicator: green/yellow/red per file

**Behavior:**
- Validation runs immediately on upload
- User can proceed to next step even with yellow flags (with warning)
- Red flags (e.g., missing required file, zero rows) block progression

#### Screen 2: Contract Configuration

**Layout:** Two-column. Left column: contract language (prose). Right column: extracted parameters (editable form fields).

**Components:**
- **Contract clause cards:** Each card shows:
  - The clause text (styled as document prose, with a subtle left border)
  - Below the text: the parameters extracted from this clause, as form fields
  - A "Linked to" indicator showing which calculation step this clause governs
- **Clause categories:** Attribution Rules, Quality Measure Specifications, Cost Calculation Rules, Settlement Terms, Eligibility Criteria
- **"Load Sample Contract" button:** Populates with the demo MSSP contract
- **Edit behavior:** When a user changes a parameter (e.g., changes tiebreaker from "most_recent_visit" to "alphabetical_npi"), the clause card highlights the change and a "Recalculate" banner appears at the top

**Contract parameter fields:**
- Attribution method: dropdown (plurality, voluntary_alignment, hybrid)
- Qualifying CPT codes: multi-select or text input
- Tiebreaker rule: dropdown (most_recent_visit, alphabetical_npi, highest_cost)
- Enrollment continuity: number input (minimum months)
- Benchmark PMPM: currency input
- Minimum savings rate: percentage input
- Shared savings rate: percentage input
- Quality gate threshold: percentage input
- Performance period: date range picker
- Quality measures: checkbox list of available measures

#### Screen 3: Results Dashboard

**Layout:** Metrics grid at top, detail panels below

**Components:**
- **Metric cards (top row):** 4-5 large cards showing key metrics. Each card is CLICKABLE (this is critical — clicking enters drill-down):
  - **Attributed Population:** "847 members" (with delta from payer report if reconciliation loaded: "Payer reports: 871 | Δ: -24")
  - **Quality Composite:** "78.4%" (with individual measure mini-bars)
  - **Actual PMPM:** "$1,142" (with benchmark line and maturity confidence band)
  - **Projected Savings:** "$312,000" (with range based on maturity uncertainty)
  - **Settlement Amount:** "$156,000" (with gate status indicators)

- **Quality Scorecard (below metrics):** Table with one row per measure. Columns: Measure Name, Current Rate, Target, Gap, Denominator Size, Numerator Count, Trend indicator. Each row clickable for drill-down.

- **Cost Breakdown (below scorecard):** Horizontal stacked bar or small multiples showing PMPM by service category. Each category clickable.

- **Reconciliation Banner (if payer report loaded):** A prominent banner at the top: "Reconciliation: 3 attribution discrepancies ($47K impact), 2 quality discrepancies, 1 cost discrepancy. View details →"

**Visual design:**
- Metric cards should use the color coding: green (favorable), yellow (neutral/uncertain), red (unfavorable) based on benchmark comparison
- Maturity-adjusted numbers should have a subtle dashed underline or confidence band indicator
- Clickable elements should have a subtle hover state with a "drill down" affordance

#### Screen 4: Drill-Down View (Three-Panel)

**This is the signature interaction of the demo.**

**Layout:** Three vertical panels, resizable

**Left Panel — Contract Language:**
- Shows the contract clause(s) governing the number the user drilled into
- Contract text is styled as prose
- Key parameters are highlighted inline
- If the user modified any parameters on the Contract Configuration screen, the modifications are shown as tracked changes (strikethrough old, highlight new)

**Center Panel — Interpretation & Data:**
- **Logic explanation (top):** A plain-English paragraph explaining how the contract clause was interpreted and applied. Example: "The platform identified all professional claims with CPT codes 99201-99215 rendered by ACO-participating providers during the performance year. For member MBR-001234, Provider A (NPI: 1234567890) rendered 3 qualifying visits and Provider B (NPI: 0987654321) rendered 2 qualifying visits. Member attributed to Provider A based on plurality."
- **Data table (bottom):** The actual data rows that fed this calculation. For an attribution drill-down, this might be a table of qualifying E&M claims for the selected member. Columns should match the source CSV structure. Each row should show the source file name.
- **Intermediate values:** Key intermediate calculations displayed as a small summary table (e.g., "Provider A visits: 3 | Provider B visits: 2 | Plurality winner: Provider A")

**Right Panel — Code:**
- Shows the actual Python function that executed this logic
- Syntax-highlighted
- Key lines highlighted (the lines that implement the specific contract parameter being viewed)
- Function name and module path shown at top
- A note: "This is the actual calculation code. The same code runs for every member."

**Navigation:**
- Breadcrumb at top: Dashboard > Attribution > Member MBR-001234
- "Next/Previous member" arrows for stepping through the population
- "Back to Dashboard" button

#### Screen 5: Reconciliation View

**Layout:** Split-screen comparison + discrepancy list

**Components:**
- **Upload zone (if no payer report loaded):** "Upload payer settlement report (JSON, CSV, or Excel)"
- **"Load Demo Payer Report" button**
- **Summary metrics:** Side-by-side comparison cards:
  - Platform vs. Payer: Attribution count, Quality composite, PMPM, Settlement amount
  - Each pair shows the delta with color coding (green = platform favorable, red = platform unfavorable)
- **Discrepancy table:** Sortable, filterable list of all identified discrepancies:
  - Category (data, methodology, timing, error, ambiguity)
  - Metric affected
  - Platform value vs. Payer value
  - Financial impact
  - "View Detail" button per row
- **Discrepancy detail view:** Clicking a discrepancy row expands to show:
  - The affected members
  - The specific data supporting the platform's calculation
  - The likely reason for the difference
  - The relevant contract language
  - A recommended resolution pathway

**Financial impact summary:** A prominent total: "Total identified discrepancy impact: $47,200. If resolved in the provider's favor, this would increase the shared savings amount from $156,000 to $179,600."

---

## 7. Phase 4: Demo Narrative & Polish

### Guided Demo Mode

Add an optional guided walkthrough overlay that steps through the demo narrative:

1. **"Welcome"** — Brief explanation of the tool's purpose (2 sentences)
2. **"Load the data"** — Click "Load Demo Data" → watch validation results appear
3. **"Review the contract"** — Walk through the MSSP contract terms, highlighting key parameters
4. **"Run the calculation"** — Click Calculate → watch metrics populate
5. **"Explore a number"** — Click on "847 attributed members" → see the three-panel drill-down for a specific member
6. **"Load the payer's report"** — Click "Load Demo Payer Report" → reconciliation banner appears
7. **"Find the discrepancy"** — Navigate to reconciliation → drill into the $47K attribution discrepancy → see the 23 members, the specific claims, the contract ambiguity
8. **"What if we change the rules?"** — Go to Contract Configuration → change the tiebreaker rule → recalculate → see how the numbers shift

### Export Capabilities

- **Reconciliation PDF:** Export the full reconciliation report as a downloadable PDF. This is what a provider would bring to a payer meeting.
- **CSV exports:** Any data table in the UI should be exportable as CSV
- **Provenance JSON:** Full pipeline result exportable as JSON for technical audiences

### Error Handling & Edge Cases

- If a user uploads a file with the wrong schema, show specific field mapping errors
- If a calculation step encounters data it can't process, flag it in the data quality panel but continue the pipeline (graceful degradation)
- If the user tries to calculate without required data, show a clear message about what's missing
- All loading states should have progress indicators

---

## 8. Data Schemas

### members.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| member_id | string | Unique member identifier (MBR-XXXXXX) | Yes |
| date_of_birth | date (YYYY-MM-DD) | Member date of birth | Yes |
| sex | string | M or F | Yes |
| race_ethnicity | string | Self-reported race/ethnicity | No |
| zip_code | string | 5-digit ZIP code | Yes |
| dual_eligible | boolean | Medicare-Medicaid dual eligible | Yes |
| hcc_risk_score | float | CMS-HCC risk score | Yes |
| pcp_npi | string | Assigned PCP NPI | No |
| deceased_date | date | Date of death, null if alive | No |

### providers.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| npi | string | 10-digit National Provider Identifier | Yes |
| provider_name | string | Last, First MI | Yes |
| taxonomy_code | string | NUCC taxonomy code | Yes |
| specialty | string | Derived from taxonomy | Yes |
| is_pcp | boolean | Primary care provider flag | Yes |
| practice_location_id | string | Practice site identifier | Yes |
| practice_location_name | string | Practice site name | Yes |
| tin | string | Tax Identification Number | Yes |
| aco_participant | boolean | Currently participating in ACO | Yes |
| effective_date | date | ACO participation start date | Yes |
| termination_date | date | ACO participation end date, null if active | No |

### eligibility.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| member_id | string | FK to members | Yes |
| payer_id | string | Payer identifier | Yes |
| contract_id | string | VBC contract identifier | Yes |
| product_type | string | Insurance product type | Yes |
| enrollment_start_date | date | Enrollment period start | Yes |
| enrollment_end_date | date | Enrollment period end, null if active | No |
| attribution_eligible | boolean | Eligible for attribution | Yes |

### claims_professional.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| claim_id | string | Unique claim identifier | Yes |
| member_id | string | FK to members | Yes |
| service_date | date | Date of service | Yes |
| rendering_npi | string | Rendering provider NPI | Yes* |
| billing_npi | string | Billing provider NPI | No |
| place_of_service | string | 2-digit POS code | Yes |
| procedure_code | string | CPT/HCPCS code | Yes |
| procedure_description | string | Human-readable description | No |
| modifier | string | CPT modifier | No |
| diagnosis_code_1 | string | Primary ICD-10-CM | Yes |
| diagnosis_code_2 | string | Secondary ICD-10-CM | No |
| diagnosis_code_3 | string | Tertiary ICD-10-CM | No |
| diagnosis_code_4 | string | Quaternary ICD-10-CM | No |
| diagnosis_description_1 | string | Primary dx description | No |
| allowed_amount | float | Payer-allowed amount | Yes |
| paid_amount | float | Amount payer paid | Yes |
| patient_responsibility | float | Patient cost share | No |
| claim_status | string | paid, denied, adjusted | Yes |
| adjudication_date | date | Date claim processed | Yes |
| data_source | string | Origin of this record | Yes |

*Required but may be missing in 2% of records (injected data quality issue)

### claims_facility.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| claim_id | string | Unique claim identifier | Yes |
| member_id | string | FK to members | Yes |
| admission_date | date | Admission date | Yes |
| discharge_date | date | Discharge date | No |
| facility_npi | string | Facility NPI | Yes |
| facility_name | string | Facility name | No |
| claim_type | string | inpatient, outpatient, ed | Yes |
| drg_code | string | DRG code (inpatient only) | No |
| revenue_code | string | Revenue code | No |
| procedure_code | string | CPT/HCPCS | No |
| diagnosis_code_1 | string | Primary ICD-10-CM | Yes |
| diagnosis_code_2 | string | Secondary ICD-10-CM | No |
| allowed_amount | float | Payer-allowed amount | Yes |
| paid_amount | float | Amount payer paid | Yes |
| claim_status | string | paid, denied, adjusted | Yes |
| adjudication_date | date | Date claim processed | Yes |
| data_source | string | Origin of this record | Yes |

### claims_pharmacy.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| claim_id | string | Unique claim identifier | Yes |
| member_id | string | FK to members | Yes |
| fill_date | date | Prescription fill date | Yes |
| ndc_code | string | National Drug Code | Yes |
| drug_name | string | Drug name | Yes |
| drug_class | string | Therapeutic class | Yes |
| days_supply | int | Days of medication supplied | Yes |
| quantity | float | Quantity dispensed | Yes |
| prescriber_npi | string | Prescribing provider NPI | No |
| allowed_amount | float | Payer-allowed amount | Yes |
| paid_amount | float | Amount payer paid | Yes |
| claim_status | string | paid, denied, adjusted | Yes |
| data_source | string | Origin of this record | Yes |

### clinical_labs.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| member_id | string | FK to members | Yes |
| lab_date | date | Date of lab test | Yes |
| loinc_code | string | LOINC code | Yes |
| lab_name | string | Human-readable lab name | Yes |
| result_value | float | Numeric result | Yes |
| result_unit | string | Unit of measurement | Yes |
| reference_range | string | Normal range | No |
| abnormal_flag | string | H, L, N, or null | No |
| ordering_npi | string | Ordering provider NPI | No |
| data_source | string | Always "ehr" | Yes |

### clinical_screenings.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| member_id | string | FK to members | Yes |
| screening_date | date | Date of screening | Yes |
| screening_type | string | colonoscopy, mammogram, depression_screening, tobacco_screening | Yes |
| cpt_code | string | Associated CPT code | No |
| result | string | Screening result/score | No |
| ordering_npi | string | Ordering provider NPI | No |
| data_source | string | Always "ehr" | Yes |

### clinical_vitals.csv
| Column | Type | Description | Required |
|--------|------|-------------|----------|
| member_id | string | FK to members | Yes |
| vital_date | date | Date of measurement | Yes |
| vital_type | string | systolic_bp, diastolic_bp, bmi, weight | Yes |
| value | float | Measured value | Yes |
| unit | string | Unit (mmHg, kg/m2, lbs) | Yes |
| provider_npi | string | Measuring provider NPI | No |
| data_source | string | Always "ehr" | Yes |

---

## 9. Provenance Data Model

The provenance model is the core innovation. Every API response for drill-down queries returns data structured as follows:

### Top-Level Metrics Response (`/api/results/summary`)

```json
{
  "metrics": {
    "attributed_population": {
      "value": 847,
      "label": "Attributed Members",
      "step": 2,
      "drilldown_url": "/api/drilldown/metric/attributed_population",
      "comparison": {
        "payer_value": 871,
        "difference": -24,
        "has_discrepancy": true
      },
      "data_confidence": "high",
      "maturity_adjusted": false
    },
    "quality_composite": {
      "value": 78.4,
      "label": "Quality Composite Score (%)",
      "step": 3,
      "drilldown_url": "/api/drilldown/metric/quality_composite",
      "comparison": {
        "payer_value": 81.2,
        "difference": -2.8,
        "has_discrepancy": true
      },
      "sub_metrics": {
        "hba1c_poor_control": { "value": 20.1, "target": 22.0, "direction": "lower_is_better" },
        "controlling_bp": { "value": 66.2, "target": 60.0, "direction": "higher_is_better" },
        "breast_cancer_screening": { "value": 72.1, "target": 70.0, "direction": "higher_is_better" },
        "colorectal_screening": { "value": 64.5, "target": 60.0, "direction": "higher_is_better" },
        "depression_screening": { "value": 54.8, "target": 50.0, "direction": "higher_is_better" }
      }
    },
    "actual_pmpm": {
      "value": 1142.00,
      "label": "Actual PMPM ($)",
      "step": 4,
      "drilldown_url": "/api/drilldown/metric/actual_pmpm",
      "comparison": {
        "payer_value": 1142.00,
        "difference": 0,
        "has_discrepancy": false
      },
      "data_confidence": "medium",
      "maturity_adjusted": true,
      "confidence_band": { "low": 1098.00, "high": 1186.00 }
    },
    "projected_savings": {
      "value": 312000,
      "label": "Projected Gross Savings ($)",
      "step": 5,
      "drilldown_url": "/api/drilldown/metric/projected_savings"
    },
    "settlement_amount": {
      "value": 156000,
      "label": "Shared Savings Amount ($)",
      "step": 5,
      "drilldown_url": "/api/drilldown/metric/settlement_amount",
      "gates": {
        "minimum_savings_rate": { "required": 0.02, "actual": 0.038, "passed": true },
        "quality_gate": { "required": 0.40, "actual": 0.784, "passed": true }
      }
    }
  },
  "pipeline_execution_time_ms": 2340,
  "data_as_of": "2025-10-15"
}
```

### Drill-Down Response (`/api/drilldown/metric/attributed_population`)

```json
{
  "metric": "attributed_population",
  "value": 847,
  "step": {
    "step_number": 2,
    "step_name": "Attribution",
    "contract_clauses": [
      {
        "clause_id": "ATTR-1.1",
        "clause_text": "Assign each eligible beneficiary to the ACO participant that provided the plurality of primary care services, as defined by CPT codes 99201–99215, 99381–99397, and G0438–G0439, during the most recent 12-month period.",
        "interpretation": "The platform counts all professional claims with the listed CPT codes, rendered by providers on the ACO participant roster, with service dates within the performance year. Claims are grouped by rendering NPI and then by TIN. The TIN with the highest total qualifying visit count receives the attribution.",
        "parameters": {
          "qualifying_cpt_codes": ["99201", "99202", "99203", "99204", "99205", "99211", "99212", "99213", "99214", "99215", "99381", "99382", "99383", "99384", "99385", "99386", "99387", "99391", "99392", "99393", "99394", "99395", "99396", "99397", "G0438", "G0439"],
          "attribution_method": "plurality",
          "lookback_period_months": 12
        }
      },
      {
        "clause_id": "ATTR-1.3",
        "clause_text": "In the event of a tie in service counts, the beneficiary shall be assigned to the provider whose most recent qualifying service was most recent in time.",
        "interpretation": "When two or more providers have identical qualifying visit counts, the provider with the most recent service date among qualifying visits is selected.",
        "parameters": {
          "tiebreaker": "most_recent_visit"
        }
      }
    ],
    "code_reference": {
      "module": "engine/step_2_attribution.py",
      "function": "assign_by_plurality",
      "source_code": "def assign_by_plurality(eligible_members, claims, providers, config):\n    ...",
      "logic_summary": "For each eligible member, count qualifying E&M visits by rendering NPI during the performance year. Group by TIN. Assign to TIN with highest count. Break ties by most recent visit date."
    }
  },
  "summary": {
    "total_eligible": 962,
    "attributed_step_1": 718,
    "attributed_step_2": 129,
    "not_attributed": 115,
    "not_attributed_reasons": {
      "no_qualifying_visits": 87,
      "qualifying_visits_non_aco_providers_only": 28
    }
  },
  "member_list_url": "/api/drilldown/step/2/members?page=1&per_page=50",
  "discrepancies": {
    "count": 24,
    "detail_url": "/api/reconciliation/detail/attribution"
  }
}
```

### Member-Level Detail (`/api/drilldown/step/2/member/MBR-001234`)

```json
{
  "member_id": "MBR-001234",
  "step": "attribution",
  "outcome": "attributed",
  "assigned_provider_npi": "1234567890",
  "assigned_provider_name": "Smith, John A",
  "assignment_step": 1,
  "reason": "Provider 1234567890 (Smith, John A) had the plurality of qualifying primary care visits (3 visits) among ACO PCP providers during the performance year.",
  "intermediate_values": {
    "qualifying_visits_by_provider": [
      { "npi": "1234567890", "name": "Smith, John A", "taxonomy": "207Q00000X", "is_pcp": true, "visit_count": 3, "most_recent_visit": "2025-07-22" },
      { "npi": "0987654321", "name": "Jones, Mary B", "taxonomy": "207Q00000X", "is_pcp": true, "visit_count": 2, "most_recent_visit": "2025-09-10" }
    ],
    "plurality_winner": "1234567890",
    "tie_occurred": false
  },
  "source_data": [
    {
      "source_file": "claims_professional.csv",
      "description": "Qualifying E&M claims for member MBR-001234",
      "rows": [
        { "row_index": 4521, "claim_id": "CLM-P-00045210", "service_date": "2025-02-14", "rendering_npi": "1234567890", "procedure_code": "99214", "procedure_description": "Office visit, established patient, moderate complexity", "allowed_amount": 142.00 },
        { "row_index": 8903, "claim_id": "CLM-P-00089030", "service_date": "2025-05-03", "rendering_npi": "1234567890", "procedure_code": "99213", "procedure_description": "Office visit, established patient, low complexity", "allowed_amount": 98.00 },
        { "row_index": 15234, "claim_id": "CLM-P-00152340", "service_date": "2025-07-22", "rendering_npi": "1234567890", "procedure_code": "99214", "procedure_description": "Office visit, established patient, moderate complexity", "allowed_amount": 142.00 },
        { "row_index": 22156, "claim_id": "CLM-P-00221560", "service_date": "2025-04-18", "rendering_npi": "0987654321", "procedure_code": "99213", "procedure_description": "Office visit, established patient, low complexity", "allowed_amount": 98.00 },
        { "row_index": 31042, "claim_id": "CLM-P-00310420", "service_date": "2025-09-10", "rendering_npi": "0987654321", "procedure_code": "99214", "procedure_description": "Office visit, established patient, moderate complexity", "allowed_amount": 142.00 }
      ]
    }
  ],
  "payer_comparison": {
    "payer_attributed": true,
    "payer_assigned_provider": "1234567890",
    "agrees": true
  }
}
```

---

## 10. Contract Language Specification

The contract configuration is stored as a JSON document that maps natural-language clauses to machine-readable parameters.

### Sample Contract: `sample_mssp_contract.json`

```json
{
  "contract_id": "CONTRACT-MSSP-2025",
  "contract_name": "Medicare Shared Savings Program — Performance Year 2025",
  "payer": "CMS / Medicare",
  "performance_period": {
    "start": "2025-01-01",
    "end": "2025-12-31"
  },
  "clauses": {
    "eligibility": {
      "ELIG-1.1": {
        "text": "Beneficiaries must have at least one month of Medicare FFS enrollment during the performance year to be eligible for attribution.",
        "parameters": {
          "minimum_enrollment_months": 1,
          "required_product_types": ["Medicare FFS"]
        }
      },
      "ELIG-1.2": {
        "text": "Beneficiaries enrolled in a Medicare Advantage plan at any point during the performance year shall be excluded from the eligible population.",
        "parameters": {
          "exclude_ma_enrolled": true
        }
      },
      "ELIG-1.3": {
        "text": "Beneficiaries with a diagnosis of end-stage renal disease (ICD-10: N18.6) shall be excluded from the eligible population.",
        "parameters": {
          "exclude_esrd": true,
          "esrd_icd10_codes": ["N18.6"]
        }
      }
    },
    "attribution": {
      "ATTR-1.1": {
        "text": "Step 1: Assign each eligible beneficiary to the ACO participant (TIN/NPI) that provided the plurality of primary care services, as defined by CPT codes 99201–99215, 99381–99397, and G0438–G0439, during the performance year.",
        "parameters": {
          "step": 1,
          "method": "plurality",
          "qualifying_cpt_codes": ["99201","99202","99203","99204","99205","99211","99212","99213","99214","99215","99381","99382","99383","99384","99385","99386","99387","99391","99392","99393","99394","99395","99396","99397","G0438","G0439"],
          "provider_filter": "pcp_only",
          "lookback_months": 12
        }
      },
      "ATTR-1.2": {
        "text": "Step 2: For beneficiaries not assigned in Step 1, assign based on the plurality of primary care services provided by any ACO participant, including specialists who rendered qualifying primary care codes.",
        "parameters": {
          "step": 2,
          "method": "plurality",
          "provider_filter": "all_aco_participants",
          "lookback_months": 12
        }
      },
      "ATTR-1.3": {
        "text": "In the event of a tie in service counts, the beneficiary shall be assigned to the provider whose most recent qualifying service was most recent in time.",
        "parameters": {
          "tiebreaker": "most_recent_visit"
        }
      }
    },
    "quality_measures": {
      "QUAL-1.1": {
        "text": "The ACO's quality performance shall be assessed on the following measures: (1) Diabetes: Hemoglobin A1c Poor Control (>9%), (2) Controlling High Blood Pressure, (3) Breast Cancer Screening, (4) Colorectal Cancer Screening, (5) Depression Screening and Follow-Up.",
        "parameters": {
          "measures": ["hba1c_poor_control", "controlling_bp", "breast_cancer_screening", "colorectal_screening", "depression_screening"],
          "weights": [0.20, 0.20, 0.20, 0.20, 0.20]
        }
      },
      "QUAL-1.2": {
        "text": "Quality measure calculations shall use clinical data from the ACO's electronic health record and claims data from the Medicare claims feed. In the event of conflicting data between sources, the clinical data source with the most recent date shall take precedence.",
        "parameters": {
          "data_sources": ["ehr", "claims"],
          "conflict_resolution": "most_recent_clinical"
        }
      }
    },
    "cost": {
      "COST-1.1": {
        "text": "Total cost of care shall be calculated as the sum of all Parts A and B allowed charges for attributed beneficiaries during the performance year, divided by the total attributed beneficiary-months, expressed as a per-member-per-month (PMPM) amount.",
        "parameters": {
          "cost_basis": "allowed_amount",
          "claim_types": ["professional", "facility"],
          "include_pharmacy": false
        }
      },
      "COST-1.2": {
        "text": "Claims with service dates within the performance year that are adjudicated within 3 months of the performance year end (i.e., by March 31 of the following year) shall be included in the cost calculation.",
        "parameters": {
          "runout_months": 3
        }
      }
    },
    "settlement": {
      "SETT-1.1": {
        "text": "The ACO's benchmark shall be $1,187.00 PMPM, as established by CMS based on the ACO's historical cost baseline trended forward.",
        "parameters": {
          "benchmark_pmpm": 1187.00
        }
      },
      "SETT-1.2": {
        "text": "If the ACO's actual PMPM is below the benchmark by more than the minimum savings rate of 2.0%, the ACO shall receive 50% of the gross savings.",
        "parameters": {
          "minimum_savings_rate": 0.02,
          "shared_savings_rate": 0.50
        }
      },
      "SETT-1.3": {
        "text": "The quality performance gate requires a minimum composite quality score of 40% for the ACO to be eligible for any shared savings distribution.",
        "parameters": {
          "quality_gate_threshold": 0.40
        }
      }
    }
  }
}
```

---

## 11. Testing Strategy

### Unit Tests

**Generator tests (test_generator.py):**
- Generated data matches configured population size
- All member IDs are unique
- All provider NPIs are valid 10-digit format
- Claims reference valid member IDs and provider NPIs
- Enrollment dates are chronologically valid
- Injected data quality issues match configured percentages (within tolerance)
- Discrepancy manifest matches actual planted discrepancies

**Calculation engine tests (per step):**

**test_eligibility.py:**
- Members with continuous enrollment are marked eligible
- Members with enrollment gaps below threshold are handled per contract rules
- ESRD exclusion correctly identifies members with N18.6 diagnosis
- Deceased members are handled correctly (included through date of death)

**test_attribution.py:**
- Plurality assignment works correctly with clear majority
- Tiebreaker logic resolves ties per contract specification
- Step 1 / Step 2 cascade works (Step 2 only runs for unattributed members)
- Terminated providers are excluded from attribution after termination date
- Provenance records include correct claim references for each attributed member
- Edge case: member with zero qualifying visits → not attributed

**test_quality_measures.py (per measure):**
- Denominator correctly identifies eligible population by age, sex, diagnosis
- Exclusions are applied correctly
- Numerator correctly evaluates clinical data (lab values, screening dates, BP readings)
- EHR/claims conflict resolution follows contract rules
- Inverse measures (HbA1c poor control) are calculated correctly (lower is better)
- Edge case: member in denominator with no data → numerator not met (not excluded)

**test_cost.py:**
- PMPM calculation is mathematically correct (total cost / member-months)
- Service category breakdown sums to total
- Claims maturity adjustment is applied correctly for each month
- Confidence band widens for more recent months
- Only claims for attributed members are included

**test_settlement.py:**
- Gross savings = (benchmark - actual) × member-months
- Minimum savings rate gate functions correctly
- Quality gate functions correctly
- Shared savings = gross savings × shared savings rate (when gates pass)
- Settlement = $0 when either gate fails

**test_reconciliation.py:**
- All planted discrepancies are detected
- Discrepancies are categorized correctly
- Financial impact is calculated correctly
- Member-level comparison correctly identifies members present in one calculation but not the other

### Integration Tests

- Full pipeline runs end-to-end on synthetic data without errors
- Pipeline results are deterministic (same data + same contract → same output)
- Changing a contract parameter and re-running produces different results
- All drill-down URLs return valid, well-formed responses
- Reconciliation against payer report produces expected discrepancy count

### Performance Tests

- Full pipeline completes in < 10 seconds for 1,000-member population on a laptop
- API response times < 500ms for all endpoints
- Frontend renders dashboard in < 2 seconds after API response

---

## 12. Resource Constraints & Performance

### Laptop Optimization Guidelines

**Memory:**
- The full synthetic dataset (~100K claims + 1K members + supporting tables) should fit in ~50-100MB of RAM as pandas DataFrames
- The provenance data (member-level detail for all steps) is the largest in-memory object. For 1,000 members × 5 steps, expect ~20-50MB as Python dicts/dataclasses.
- Total application memory footprint should stay under 500MB

**CPU:**
- All calculations are pandas operations (vectorized where possible). No ML models, no heavy computation.
- The attribution step involves a groupby-aggregate pattern. For 100K claims, this completes in milliseconds.
- Quality measures involve filtering and joining. Sub-second per measure.
- The full pipeline should complete in 2-5 seconds.

**Disk:**
- Synthetic data files: ~50MB total
- Provenance JSON (serialized pipeline results): ~30-50MB
- Application code: < 5MB
- Node modules (frontend): ~200MB (standard for React/Vite)
- Total: < 400MB

**Network:**
- The application runs 100% locally. No external API calls.
- FastAPI serves on localhost:8000
- Vite dev server serves on localhost:5173

### Development Dependencies

```
# requirements.txt
fastapi>=0.110.0
uvicorn>=0.27.0
pandas>=2.2.0
numpy>=1.26.0
faker>=22.0.0
pydantic>=2.6.0
python-multipart>=0.0.6    # For file upload handling
orjson>=3.9.0              # Fast JSON serialization

# Optional but recommended
pytest>=8.0.0
httpx>=0.27.0              # For testing FastAPI endpoints
```

```json
// package.json (key dependencies)
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "axios": "^1.6.0",
    "recharts": "^2.12.0",
    "react-syntax-highlighter": "^15.5.0",
    "@tailwindcss/typography": "^0.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### Startup Script

```bash
#!/bin/bash
# start.sh — Run the full application locally

# Generate synthetic data (if not already generated)
if [ ! -f data/synthetic/members.csv ]; then
    echo "Generating synthetic data..."
    python -m generator.generate
fi

# Start FastAPI backend
echo "Starting API server on http://localhost:8000"
uvicorn api.main:app --reload --port 8000 &

# Start React frontend
echo "Starting UI on http://localhost:5173"
cd frontend && npm run dev &

echo "Application ready."
echo "  API:  http://localhost:8000"
echo "  UI:   http://localhost:5173"
echo "  Docs: http://localhost:8000/docs"
```

---

## CLAUDE.md — Project Context File

Save this as `CLAUDE.md` in the project root for Claude Code to reference:

```markdown
# VBC Transparent Calculation Demo Tool

## What This Is
A demo tool showing how a neutral VBC calculation layer works. Users upload
data (claims, eligibility, clinical) and contract language, and the tool
transparently calculates performance metrics with full provenance — every
number traces back to its source data, governing contract language, and
executing code.

## Key Architectural Principle
**Provenance is not a feature — it IS the product.** Every calculation step
must produce a StepResult with: contract clauses, code references, member-
level detail, and source data references. If a number can't be traced to its
source, the implementation is wrong.

## Tech Stack
- Python 3.11+ (backend, data generation, calculation engine)
- FastAPI (API layer)
- React 18 + TypeScript (frontend)
- Tailwind CSS (styling)
- Vite (build)
- pandas (data manipulation)
- No database — all data in-memory from CSV files

## Running Locally
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
./start.sh
```

## Project Structure
- `generator/` — Synthetic data generation (run once)
- `engine/` — Calculation pipeline with provenance tracking
- `api/` — FastAPI endpoints
- `frontend/` — React UI with drill-down views
- `data/` — Synthetic datasets and contract templates
- `tests/` — Unit and integration tests

## Build Order
1. generator/ (data must exist before anything else)
2. engine/ (calculation pipeline — start with provenance.py, then steps 1-6)
3. api/ (thin layer over engine)
4. frontend/ (UI consuming API)

## Critical Rules
- All synthetic data must use the member_id format MBR-XXXXXX
- Never generate or store real PHI — everything is synthetic
- Every calculation function must return a StepResult, not raw values
- The three-panel drill-down (contract | interpretation | code) is the
  signature UX — every metric must support it
- Claims maturity adjustments must be visible in the UI (confidence bands)
- The 23 attribution discrepancies, 15 quality discrepancies, and 8 cost
  discrepancies are planted intentionally — the reconciliation engine must
  independently discover all of them
```

---

## Implementation Sequence Summary

| Phase | Duration | Deliverable | Dependencies |
|-------|----------|-------------|--------------|
| Phase 1 | Week 1-2 | Synthetic data generator + all CSV files + payer settlement report + discrepancy manifest | None |
| Phase 2a | Week 3 | Provenance data model + pipeline orchestrator + Step 1 (eligibility) + Step 2 (attribution) | Phase 1 |
| Phase 2b | Week 4 | Step 3 (quality measures — all 5) + Step 4 (cost/PMPM) | Phase 2a |
| Phase 2c | Week 5 | Step 5 (settlement) + Step 6 (reconciliation) + all unit tests passing | Phase 2b |
| Phase 3a | Week 6 | FastAPI endpoints + data upload/validation | Phase 2c |
| Phase 3b | Week 7 | React UI — upload screen, contract config, results dashboard | Phase 3a |
| Phase 3c | Week 8 | React UI — three-panel drill-down view + reconciliation view | Phase 3b |
| Phase 4 | Week 9-10 | Guided demo mode, PDF export, polish, edge cases | Phase 3c |
