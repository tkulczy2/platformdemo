# VBC Performance Intelligence Platform

**Transparent, auditable value-based care calculations — where every number traces back to its source.**

---

## The Problem

If you manage value-based contracts, you know the frustration: a payer sends a settlement report, and the numbers don't match yours. Attribution counts are off. Quality rates disagree. Shared savings differ by hundreds of thousands of dollars. And when you ask why, no one can give you a straight answer — because the calculations are locked inside black boxes on both sides.

You spend weeks in back-and-forth reconciliation, pulling claims files and re-running spreadsheets, only to discover that the discrepancy came down to a single contract clause interpreted differently by each party.

**This tool exists to eliminate that problem.**

## What This Is

A working demonstration of a VBC Performance Intelligence Platform that takes your data and your contract language, runs the full MSSP-style settlement calculation, and makes every result fully traceable. Click any number on the dashboard and see three things side by side:

1. **The contract clause** that governed the calculation
2. **The specific data and logic** that produced the result
3. **The actual code** that executed it

Then upload a payer's settlement report and watch the platform automatically surface every discrepancy — with the root cause, the governing contract language, and the dollar impact of each one.

This is not a mockup. It runs real calculations on real data structures, using standard HEDIS methodology and MSSP attribution logic.

## What It Calculates

The platform runs a six-step pipeline that mirrors a full ACO performance year settlement:

| Step | What It Does |
|------|-------------|
| **1. Eligibility** | Determines which beneficiaries qualify based on enrollment continuity and exclusion criteria |
| **2. Attribution** | Assigns members to providers using two-step plurality attribution (the same method CMS uses in MSSP) |
| **3. Quality** | Calculates five HEDIS-aligned quality measures: HbA1c control, blood pressure control, breast cancer screening, colorectal screening, and depression screening |
| **4. Cost** | Computes actual PMPM with claims maturity adjustments and confidence bands for incomplete run-out periods |
| **5. Settlement** | Applies benchmark comparison, minimum savings rate, quality gates, and shared savings calculations |
| **6. Reconciliation** | Compares platform results against the payer's settlement report and identifies every discrepancy with its root cause and financial impact |

Every step produces a complete audit trail. Every member-level result links to the source claims, clinical records, and contract clauses that drove it.

## Why It Matters

**For VPs of Population Health:** See exactly which members are attributed, which quality measures they're meeting or missing, and why — down to the individual claim or lab result.

**For CFOs:** Understand the precise dollar impact of every contract parameter. Change the minimum savings rate from 2% to 3% and instantly see how it affects your shared savings. Identify where payer discrepancies are costing you money.

**For VBC Contract Analysts:** Stop reconciling in spreadsheets. Upload the payer report and get a categorized list of every discrepancy — attribution disagreements, quality measure conflicts, cost differences — each mapped to the contract clause that applies.

## Key Capabilities

### Full Provenance on Every Number

Every metric on the dashboard is clickable. The drill-down view shows the contract language, the platform's interpretation, the member-level data, and the code — all in one screen. Nothing is hidden.

### Contract-Aware Calculations

The contract isn't just documentation. It's a live input. Change the attribution method, the qualifying CPT codes, the quality measure weights, or the benchmark PMPM, and the entire pipeline recalculates. You can model "what if we negotiated different terms" in seconds.

### Automated Reconciliation

Upload a payer settlement report and the platform identifies discrepancies across every category: attribution, quality, cost, and savings. Each discrepancy shows the root cause (e.g., "Payer used claims-only data; platform found an EHR screening record that satisfies this measure") and the financial impact.

### Data Quality Transparency

Real-world healthcare data is messy. The platform doesn't hide that — it scores data completeness, flags issues (enrollment gaps, missing fields, duplicate claims, conflicting sources), and shows how data quality affects each calculation step.

## Try It

### Live Demo

A static version of the platform with pre-computed results is available at the GitHub Pages deployment. It demonstrates the full UI — dashboard, drill-down, and reconciliation — without requiring any local setup.

### Run Locally (Full Interactive Mode)

Running locally enables data upload, contract editing, and live recalculation.

**Requirements:** Python 3.11+, Node.js 18+

```bash
# Clone the repository
git clone https://github.com/your-org/platformdemo.git
cd platformdemo

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Generate synthetic demo data (1,000 members, ~50K claims)
python -m generator.generate

# Start the platform
./start.sh
```

Then open **http://localhost:5173** in your browser.

Click **Load Demo Data** and **Load Sample Contract** to populate the platform with synthetic data modeled on a Medicare ACO contract, then run the calculation pipeline. Every number you see is fully traceable.

## What's Under the Hood

| Component | Technology |
|-----------|-----------|
| Calculation engine | Python with pandas — chosen for readability, because the code itself is part of the product |
| Quality measures | HEDIS-aligned methodology (denominator, exclusions, numerator) |
| Attribution | MSSP two-step plurality with configurable tiebreakers |
| API | FastAPI |
| Frontend | React + TypeScript + Tailwind CSS + Recharts |
| Data | CSV input, JSON provenance — human-inspectable at every layer |

No database. No cloud services. No external dependencies at runtime. Everything runs on a single laptop in under 10 seconds for 1,000 members.

## Synthetic Data

All data in this demo is synthetic, generated with deterministic seeds for reproducibility. No real patient data is used or stored. The synthetic dataset includes intentionally planted discrepancies in the payer settlement report (attribution disagreements, quality measure conflicts, and cost differences) to demonstrate the reconciliation workflow.

---

*Built to demonstrate that VBC performance calculation doesn't have to be a black box.*
