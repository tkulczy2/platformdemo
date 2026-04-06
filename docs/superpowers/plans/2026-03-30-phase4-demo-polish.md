# Phase 4: Demo Narrative & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add guided demo walkthrough, export capabilities (PDF/CSV/JSON), and improved error handling to the VBC Demo Tool.

**Architecture:** Three independent features added to the existing FastAPI + React app. Backend gets a new `api/routes_export.py` with 3 endpoints for PDF/CSV/JSON exports. Frontend gets a new `GuidedDemo` component rendered as a floating overlay in `AppShell`, plus export buttons wired into existing views. `reportlab` is added for PDF generation — no other new dependencies.

**Tech Stack:** Python (FastAPI, reportlab, csv/io), React 18 + TypeScript, Tailwind CSS

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `api/routes_export.py` | PDF, CSV, and JSON export endpoints |
| Create | `frontend/src/components/demo/GuidedDemo.tsx` | Guided walkthrough overlay with 8 steps |
| Modify | `api/main.py` | Register export router |
| Modify | `frontend/src/api/client.ts` | Add export API functions |
| Modify | `frontend/src/components/layout/AppShell.tsx` | Add "Start Demo" button + render GuidedDemo |
| Modify | `frontend/src/components/reconciliation/ReconciliationView.tsx` | Add export buttons (PDF, CSV) |
| Modify | `frontend/src/components/dashboard/ResultsDashboard.tsx` | Add JSON export button |
| Modify | `requirements.txt` | Add `reportlab` dependency |

---

## Task 1: Backend Export Endpoints

**Files:**
- Create: `api/routes_export.py`
- Modify: `api/main.py:89-102`
- Modify: `requirements.txt`

- [ ] **Step 1: Add reportlab to requirements.txt**

```
# Append to requirements.txt
reportlab>=4.0.0
```

- [ ] **Step 2: Install the dependency**

Run: `pip install reportlab>=4.0.0`
Expected: Successfully installed reportlab

- [ ] **Step 3: Create `api/routes_export.py` with all three endpoints**

```python
"""Export routes — PDF reconciliation report, CSV data tables, JSON pipeline result."""

import csv
import io
import json
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.main import state, _fix_values

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/reconciliation-pdf")
def export_reconciliation_pdf():
    """Generate a PDF reconciliation report for payer meetings."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results. Run /api/calculate first.")

    recon = state.pipeline_result.reconciliation
    if recon is None:
        raise HTTPException(status_code=404, detail="No reconciliation data. Load a payer report and recalculate.")

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("CustomTitle", parent=styles["Title"], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=8)
    body_style = styles["Normal"]

    elements = []

    # Title
    elements.append(Paragraph("VBC Performance Intelligence", title_style))
    elements.append(Paragraph("Reconciliation Report — Platform vs. Payer Settlement", subtitle_style))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 12))

    # Summary metrics
    fm = state.pipeline_result.final_metrics
    if isinstance(fm, dict):
        elements.append(Paragraph("Performance Summary", heading_style))
        summary_data = [
            ["Metric", "Platform Value"],
            ["Attributed Population", str(fm.get("attributed_population", "N/A"))],
            ["Quality Composite", f"{fm.get('quality_composite', 'N/A')}%"],
            ["Actual PMPM", f"${fm.get('actual_pmpm', 'N/A'):,.2f}" if isinstance(fm.get("actual_pmpm"), (int, float)) else "N/A"],
            ["Benchmark PMPM", f"${fm.get('benchmark_pmpm', 'N/A'):,.2f}" if isinstance(fm.get("benchmark_pmpm"), (int, float)) else "N/A"],
        ]
        t = Table(summary_data, colWidths=[3.5 * inch, 3 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

    # Discrepancy overview
    discrepancy_count = recon.get("discrepancy_count", 0)
    total_impact = recon.get("total_financial_impact", 0)

    elements.append(Paragraph("Reconciliation Overview", heading_style))
    elements.append(Paragraph(
        f"<b>{discrepancy_count}</b> discrepancies identified with a total financial impact of "
        f"<b>${abs(total_impact):,.2f}</b>.",
        body_style,
    ))
    elements.append(Spacer(1, 8))

    # Category breakdown
    categories = recon.get("categories", {})
    if isinstance(categories, dict) and categories:
        cat_data = [["Category", "Count", "Financial Impact"]]
        for cat_name, cat_info in categories.items():
            count = cat_info.get("count", 0) if isinstance(cat_info, dict) else 0
            impact = cat_info.get("total_impact", 0) if isinstance(cat_info, dict) else 0
            cat_data.append([cat_name.title(), str(count), f"${abs(impact):,.2f}"])
        t = Table(cat_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

    # Individual discrepancies table
    discrepancies = recon.get("discrepancies", [])
    if discrepancies:
        elements.append(Paragraph("Discrepancy Details", heading_style))
        disc_data = [["Member", "Category", "Description", "Impact"]]
        for d in discrepancies[:100]:  # Cap at 100 rows for PDF readability
            disc_data.append([
                d.get("member_id", ""),
                d.get("category", ""),
                d.get("description", "")[:60],
                f"${d.get('financial_impact', 0):,.2f}",
            ])
        t = Table(disc_data, colWidths=[1.2 * inch, 1 * inch, 3 * inch, 1.3 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Generated by VBC Performance Intelligence Platform. All data is synthetic — no real PHI.",
        ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.grey),
    ))

    doc.build(elements)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reconciliation_report.pdf"},
    )


EXPORTABLE_TABLES = {
    "discrepancies": "Reconciliation discrepancies",
    "members": "Attributed member list from step 2",
    "quality_measures": "Quality measure results from step 3",
}


@router.get("/csv/{table_name}")
def export_csv(table_name: str):
    """Export a data table as CSV."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results. Run /api/calculate first.")

    if table_name not in EXPORTABLE_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table '{table_name}'. Available: {list(EXPORTABLE_TABLES.keys())}",
        )

    rows = _get_table_rows(table_name)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data available for table '{table_name}'.")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
    )


def _get_table_rows(table_name: str) -> list[dict]:
    """Extract rows for a given table name from the pipeline result."""
    result = state.pipeline_result
    if result is None:
        return []

    if table_name == "discrepancies":
        recon = result.reconciliation
        if recon is None:
            return []
        discrepancies = recon.get("discrepancies", [])
        return [
            {
                "member_id": d.get("member_id", ""),
                "category": d.get("category", ""),
                "subcategory": d.get("subcategory", ""),
                "description": d.get("description", ""),
                "platform_value": d.get("platform_value", ""),
                "payer_value": d.get("payer_value", ""),
                "financial_impact": d.get("financial_impact", 0),
                "root_cause": d.get("root_cause", ""),
            }
            for d in discrepancies
        ]

    if table_name == "members":
        # Get member details from step 2 (attribution)
        for step in result.steps:
            if step.step_number == 2:
                return [
                    {
                        "member_id": m.member_id,
                        "outcome": m.outcome,
                        "outcome_value": m.outcome_value,
                    }
                    for m in step.member_details
                ]
        return []

    if table_name == "quality_measures":
        # Get quality measure results from step 3
        for step in result.steps:
            if step.step_number == 3:
                measures = step.aggregate_metrics
                rows = []
                for key, value in measures.items():
                    if isinstance(value, dict):
                        row = {"measure": key}
                        row.update(value)
                        rows.append(row)
                    else:
                        rows.append({"measure": key, "value": value})
                return rows if rows else [{"measure": k, "value": v} for k, v in measures.items()]
        return []

    return []


@router.get("/pipeline-json")
def export_pipeline_json():
    """Export full pipeline result as JSON with provenance."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results. Run /api/calculate first.")

    data = _fix_values(asdict(state.pipeline_result))

    buf = io.BytesIO(json.dumps(data, indent=2, default=str).encode("utf-8"))

    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=pipeline_result.json"},
    )
```

- [ ] **Step 4: Register the export router in `api/main.py`**

Add after line 95 in `api/main.py`:

```python
from api.routes_export import router as export_router
```

Add after line 102 in `api/main.py`:

```python
app.include_router(export_router)
```

- [ ] **Step 5: Verify backend starts**

Run: `python -c "from api.routes_export import router; print('Export router OK')" `
Expected: `Export router OK`

- [ ] **Step 6: Commit**

```bash
git add api/routes_export.py api/main.py requirements.txt
git commit -m "feat: add export endpoints for PDF, CSV, and JSON"
```

---

## Task 2: Frontend Export API Functions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add export functions to `api/client.ts`**

Add before the closing `// Response type aliases` section (before line 139):

```typescript
// ---------------------------------------------------------------------------
// Export endpoints
// ---------------------------------------------------------------------------

export function exportReconciliationPdf() {
  window.open('/api/export/reconciliation-pdf', '_blank');
}

export function exportCsv(tableName: string) {
  window.open(`/api/export/csv/${tableName}`, '_blank');
}

export function exportPipelineJson() {
  window.open('/api/export/pipeline-json', '_blank');
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add export API functions to frontend client"
```

---

## Task 3: Export Buttons in ReconciliationView

**Files:**
- Modify: `frontend/src/components/reconciliation/ReconciliationView.tsx`

- [ ] **Step 1: Add import for export functions**

Add to the imports from `@/api/client` (line 10):

```typescript
import {
  getReconciliationSummary,
  getReconciliationDetail,
  uploadPayerReport,
  loadDemoPayerReport,
  runCalculation,
  getResultsSummary,
  exportReconciliationPdf,
  exportCsv,
} from '@/api/client';
```

- [ ] **Step 2: Add export buttons to the page header area**

Replace the header `<div>` in the loaded state (the block at lines 308-319 with "Page header") with:

```tsx
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payer Reconciliation</h1>
          <p className="mt-1 text-sm text-gray-500">
            Platform vs. payer settlement comparison with full provenance for every discrepancy.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => exportCsv('discrepancies')}
            className="btn-secondary text-xs"
            title="Export discrepancies as CSV"
          >
            <svg className="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            CSV
          </button>
          <button
            onClick={exportReconciliationPdf}
            className="btn-primary text-xs"
            title="Export reconciliation report as PDF"
          >
            <svg className="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            Export PDF
          </button>
        </div>
      </div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/reconciliation/ReconciliationView.tsx
git commit -m "feat: add PDF and CSV export buttons to reconciliation view"
```

---

## Task 4: Export Button in ResultsDashboard

**Files:**
- Modify: `frontend/src/components/dashboard/ResultsDashboard.tsx`

- [ ] **Step 1: Add import for export function**

Add `exportPipelineJson` to the imports from `@/api/client` (line 6):

```typescript
import {
  runCalculation,
  getResultsSummary,
  getReconciliationSummary,
  exportPipelineJson,
} from '@/api/client';
```

- [ ] **Step 2: Add export button next to the Recalculate button**

Replace the page header section (lines 263-276) with:

```tsx
      {/* ----- Page header ----- */}
      <div className="flex items-center justify-between">
        <div>
          <h1>Performance Results</h1>
          <p className="mt-1 text-sm text-gray-500">
            All numbers are clickable -- drill down to see the contract language, data, and code behind each calculation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={exportPipelineJson} className="btn-secondary" title="Export full pipeline result as JSON">
            <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Export JSON
          </button>
          <button onClick={calculate} className="btn-secondary">
            <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
            Recalculate
          </button>
        </div>
      </div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/ResultsDashboard.tsx
git commit -m "feat: add JSON export button to results dashboard"
```

---

## Task 5: Guided Demo Component

**Files:**
- Create: `frontend/src/components/demo/GuidedDemo.tsx`

- [ ] **Step 1: Create the GuidedDemo component**

```tsx
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { classNames } from '@/utils/formatters';

interface DemoStep {
  id: string;
  title: string;
  description: string;
  targetPath: string;
  action?: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to VBC Performance Intelligence',
    description:
      'This tool transparently computes VBC performance metrics from raw data and contract language. Every number can be traced to its source data, governing contract clause, and executing code.',
    targetPath: '/',
  },
  {
    id: 'load-data',
    title: 'Load the Data',
    description:
      'Click "Load Demo Data" below to load synthetic claims, eligibility, clinical, and provider data. Watch the validation results appear showing data quality scores for each file.',
    targetPath: '/',
    action: 'Click the "Load Demo Data" button',
  },
  {
    id: 'review-contract',
    title: 'Review the Contract',
    description:
      'The MSSP contract defines how attribution, quality measures, and cost calculations work. Each parameter links to the contract language that governs it. Try changing a parameter to see how it affects the calculation.',
    targetPath: '/contract',
    action: 'Click "Load Sample Contract" to load the demo MSSP contract',
  },
  {
    id: 'run-calculation',
    title: 'Run the Calculation',
    description:
      'The pipeline executes 6 steps: eligibility, attribution, quality measures, cost/PMPM, settlement, and reconciliation. Each step produces a provenance trail linking every output to its inputs.',
    targetPath: '/dashboard',
    action: 'The calculation runs automatically when you navigate here',
  },
  {
    id: 'explore-number',
    title: 'Explore a Number',
    description:
      'Click on any metric card above to drill down. You\'ll see the three-panel view: contract language on the left, the platform\'s interpretation and supporting data in the center, and the executing code on the right.',
    targetPath: '/dashboard',
    action: 'Click on "Attributed Population" or any other metric card',
  },
  {
    id: 'load-payer-report',
    title: 'Load the Payer\'s Report',
    description:
      'Now load the payer\'s settlement report. This pre-built report contains intentional discrepancies that mirror real-world disagreements between payers and providers.',
    targetPath: '/reconciliation',
    action: 'Click "Load Demo Payer Report"',
  },
  {
    id: 'find-discrepancy',
    title: 'Find the Discrepancies',
    description:
      'The platform has identified every discrepancy between its calculations and the payer\'s report. Each one is traced to its root cause — whether it\'s a data difference, methodology difference, or contract ambiguity.',
    targetPath: '/reconciliation',
    action: 'Click "View Detail" on any discrepancy row to see the full provenance',
  },
  {
    id: 'what-if',
    title: 'What If We Change the Rules?',
    description:
      'Go back to Contract Configuration and try changing a parameter — like the tiebreaker rule or the minimum savings rate. Recalculate to see how the numbers shift. This is the power of a transparent, parameterized calculation engine.',
    targetPath: '/contract',
    action: 'Change a contract parameter and navigate to Dashboard to recalculate',
  },
];

interface GuidedDemoProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function GuidedDemo({ isOpen, onClose }: GuidedDemoProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();

  const step = DEMO_STEPS[currentStep];

  const goToStep = useCallback(
    (index: number) => {
      setCurrentStep(index);
      const target = DEMO_STEPS[index];
      if (target && location.pathname !== target.targetPath) {
        navigate(target.targetPath);
      }
    },
    [navigate, location.pathname],
  );

  // Navigate to the correct page when the step changes
  useEffect(() => {
    if (isOpen && step && location.pathname !== step.targetPath) {
      navigate(step.targetPath);
    }
  }, [isOpen, currentStep]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isOpen || !step) return null;

  const isFirst = currentStep === 0;
  const isLast = currentStep === DEMO_STEPS.length - 1;
  const progress = ((currentStep + 1) / DEMO_STEPS.length) * 100;

  return (
    <div className="fixed bottom-6 left-1/2 z-50 w-full max-w-lg -translate-x-1/2">
      <div className="rounded-2xl border border-brand-200 bg-white shadow-2xl shadow-brand-500/10">
        {/* Progress bar */}
        <div className="h-1 overflow-hidden rounded-t-2xl bg-brand-100">
          <div
            className="h-full bg-brand-600 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="p-5">
          {/* Step counter + close */}
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium text-brand-600">
              Step {currentStep + 1} of {DEMO_STEPS.length}
            </span>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title="End demo"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <h3 className="text-base font-semibold text-gray-900">{step.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.description}</p>

          {step.action && (
            <div className="mt-3 flex items-start gap-2 rounded-lg bg-brand-50 px-3 py-2.5">
              <svg
                className="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.834.166l-1.591 1.591M20.25 10.5H18M7.757 14.743l-1.59 1.59M6 10.5H3.75m4.007-4.243l-1.59-1.59"
                />
              </svg>
              <span className="text-xs font-medium text-brand-700">{step.action}</span>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => goToStep(currentStep - 1)}
              disabled={isFirst}
              className={classNames(
                'flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                isFirst
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-600 hover:bg-gray-100',
              )}
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              Previous
            </button>

            {/* Step dots */}
            <div className="flex items-center gap-1.5">
              {DEMO_STEPS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => goToStep(i)}
                  className={classNames(
                    'h-1.5 rounded-full transition-all',
                    i === currentStep
                      ? 'w-4 bg-brand-600'
                      : i < currentStep
                        ? 'w-1.5 bg-brand-300'
                        : 'w-1.5 bg-gray-300',
                  )}
                />
              ))}
            </div>

            {isLast ? (
              <button
                onClick={onClose}
                className="flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
              >
                Finish
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </button>
            ) : (
              <button
                onClick={() => goToStep(currentStep + 1)}
                className="flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
              >
                Next
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/demo/GuidedDemo.tsx
git commit -m "feat: add guided demo walkthrough component"
```

---

## Task 6: Wire GuidedDemo into AppShell

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Add GuidedDemo imports and state to AppShell**

Replace the top of `AppShell.tsx` (lines 1-3):

```tsx
import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { classNames } from '@/utils/formatters';
import StepIndicator from './StepIndicator';
import GuidedDemo from '@/components/demo/GuidedDemo';
```

- [ ] **Step 2: Add demo state inside the component**

Add as the first line inside the `AppShell` function body (after line 12 `export default function AppShell() {`):

```tsx
  const [demoOpen, setDemoOpen] = useState(false);
```

- [ ] **Step 3: Replace the "Demo Mode" badge with a "Start Demo" button**

Replace the right-side placeholder section (lines 58-61):

```tsx
          {/* Right side — guided demo toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDemoOpen((o) => !o)}
              className={classNames(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                demoOpen
                  ? 'bg-brand-600 text-white'
                  : 'bg-brand-50 text-brand-700 hover:bg-brand-100 ring-1 ring-inset ring-brand-200',
              )}
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
              {demoOpen ? 'Demo Running' : 'Start Demo'}
            </button>
          </div>
```

- [ ] **Step 4: Add the GuidedDemo component before the closing `</div>` of the root**

Insert before the final closing `</div>` (before line 91):

```tsx
      {/* Guided demo overlay */}
      <GuidedDemo isOpen={demoOpen} onClose={() => setDemoOpen(false)} />
```

- [ ] **Step 5: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/AppShell.tsx
git commit -m "feat: wire guided demo into app shell with start button"
```

---

## Task 7: Improve Error Handling for Missing Data/Contract

**Files:**
- Modify: `frontend/src/components/dashboard/ResultsDashboard.tsx`

- [ ] **Step 1: Improve the error state to distinguish missing prerequisites from calculation failures**

Replace the error state block (lines 179-201) with:

```tsx
  // -- Error state --------------------------------------------------------
  if (phase === 'error') {
    const isMissingData = error?.includes('data') || error?.includes('Data');
    const isMissingContract = error?.includes('contract') || error?.includes('Contract');

    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6">
          <div className="flex items-start gap-3">
            <svg className="mt-0.5 h-5 w-5 text-red-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="font-semibold text-red-800">Calculation Failed</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              {(isMissingData || isMissingContract) && (
                <div className="mt-3 space-y-2">
                  <p className="text-xs font-medium text-red-800">Before calculating, you need to:</p>
                  <ul className="list-inside list-disc text-xs text-red-700 space-y-1">
                    {isMissingData && (
                      <li>
                        <button onClick={() => navigate('/')} className="underline hover:text-red-900">
                          Load or upload data files
                        </button>
                      </li>
                    )}
                    {isMissingContract && (
                      <li>
                        <button onClick={() => navigate('/contract')} className="underline hover:text-red-900">
                          Load or configure a contract
                        </button>
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
        <button onClick={calculate} className="btn-primary">
          Retry Calculation
        </button>
      </div>
    );
  }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/ResultsDashboard.tsx
git commit -m "feat: improve error handling with prerequisite guidance"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Install backend dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 2: Check frontend compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Verify backend imports**

Run: `python -c "from api.main import app; print('Routes:', [r.path for r in app.routes][:5], '...')" `

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore: phase 4 final verification fixes"
```
