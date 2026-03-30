"""Export routes — PDF, CSV, and JSON exports of pipeline results."""

import csv
import io
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from api.main import state, _fix_values

router = APIRouter(prefix="/api/export", tags=["export"])

BRAND_COLOR = colors.HexColor("#2563eb")


@router.get("/reconciliation-pdf")
def export_reconciliation_pdf():
    """Generate a PDF reconciliation report."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    result = state.pipeline_result
    recon = result.reconciliation
    metrics = result.final_metrics

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        textColor=BRAND_COLOR,
        fontSize=20,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        textColor=BRAND_COLOR,
        spaceAfter=10,
        spaceBefore=16,
    )

    header_table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ])

    elements = []

    # Title
    elements.append(Paragraph("VBC Performance Reconciliation Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Performance Summary
    elements.append(Paragraph("Performance Summary", heading_style))
    summary_data = [
        ["Metric", "Value"],
        ["Attributed Population", str(metrics.get("attributed_population", "N/A"))],
        ["Quality Composite", f"{metrics.get('quality_composite', 0):.4f}" if isinstance(metrics.get("quality_composite"), (int, float)) else str(metrics.get("quality_composite", "N/A"))],
        ["Actual PMPM", f"${metrics.get('actual_pmpm', 0):,.2f}" if isinstance(metrics.get("actual_pmpm"), (int, float)) else str(metrics.get("actual_pmpm", "N/A"))],
        ["Benchmark PMPM", f"${metrics.get('benchmark_pmpm', 0):,.2f}" if isinstance(metrics.get("benchmark_pmpm"), (int, float)) else str(metrics.get("benchmark_pmpm", "N/A"))],
    ]
    t = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    t.setStyle(header_table_style)
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Reconciliation Overview
    elements.append(Paragraph("Reconciliation Overview", heading_style))
    if recon:
        disc_count = recon.get("discrepancy_count", 0)
        total_impact = recon.get("total_financial_impact", 0)
        overview_data = [
            ["Metric", "Value"],
            ["Discrepancy Count", str(disc_count)],
            ["Total Financial Impact", f"${total_impact:,.2f}" if isinstance(total_impact, (int, float)) else str(total_impact)],
        ]
        t = Table(overview_data, colWidths=[3 * inch, 3 * inch])
        t.setStyle(header_table_style)
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Category Breakdown
        categories = recon.get("categories", {})
        if categories:
            elements.append(Paragraph("Category Breakdown", heading_style))
            cat_data = [["Category", "Count", "Financial Impact"]]
            for cat_name, cat_info in categories.items():
                if isinstance(cat_info, dict):
                    cat_data.append([
                        cat_name,
                        str(cat_info.get("count", 0)),
                        f"${cat_info.get('financial_impact', 0):,.2f}" if isinstance(cat_info.get("financial_impact"), (int, float)) else str(cat_info.get("financial_impact", "N/A")),
                    ])
                else:
                    cat_data.append([cat_name, str(cat_info), "N/A"])
            t = Table(cat_data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
            t.setStyle(header_table_style)
            elements.append(t)
            elements.append(Spacer(1, 12))

        # Discrepancy Details (capped at 100)
        discrepancies = recon.get("discrepancies", [])
        if discrepancies:
            elements.append(Paragraph(f"Discrepancy Details (showing {min(len(discrepancies), 100)} of {len(discrepancies)})", heading_style))
            detail_data = [["Member ID", "Category", "Type", "Financial Impact"]]
            for d in discrepancies[:100]:
                detail_data.append([
                    str(d.get("member_id", "N/A")),
                    str(d.get("category", "N/A")),
                    str(d.get("type", d.get("discrepancy_type", "N/A"))),
                    f"${d.get('financial_impact', 0):,.2f}" if isinstance(d.get("financial_impact"), (int, float)) else str(d.get("financial_impact", "N/A")),
                ])
            t = Table(detail_data, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch, 1.5 * inch])
            t.setStyle(header_table_style)
            elements.append(t)
    else:
        elements.append(Paragraph("No reconciliation data available.", styles["Normal"]))

    doc.build(elements)
    buf.seek(0)

    filename = f"reconciliation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/csv/{table_name}")
def export_csv(table_name: str):
    """Export data tables as CSV."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    result = state.pipeline_result
    rows: list[dict] = []

    if table_name == "discrepancies":
        recon = result.reconciliation
        if recon is None:
            raise HTTPException(status_code=404, detail="No reconciliation data available.")
        rows = [_fix_values(d) if isinstance(d, dict) else d for d in recon.get("discrepancies", [])]

    elif table_name == "members":
        # From step 2 (attribution) member_details
        step2 = next((s for s in result.steps if s.step_number == 2), None)
        if step2 is None:
            raise HTTPException(status_code=404, detail="Step 2 (attribution) not found in pipeline results.")
        rows = [
            {
                "member_id": md.member_id,
                "outcome": md.outcome,
                "reason": md.reason,
                **{k: _fix_values(v) for k, v in md.intermediate_values.items()},
            }
            for md in step2.member_details
        ]

    elif table_name == "quality_measures":
        # From step 3 aggregate_metrics
        step3 = next((s for s in result.steps if s.step_number == 3), None)
        if step3 is None:
            raise HTTPException(status_code=404, detail="Step 3 (quality) not found in pipeline results.")
        agg = step3.summary if hasattr(step3, "summary") else {}
        # aggregate_metrics may be nested; flatten measure-level data
        if isinstance(agg, dict):
            measures = agg.get("measures", agg.get("measure_results", {}))
            if isinstance(measures, dict):
                for measure_name, measure_data in measures.items():
                    if isinstance(measure_data, dict):
                        rows.append({"measure": measure_name, **_fix_values(measure_data)})
                    else:
                        rows.append({"measure": measure_name, "value": measure_data})
            if not rows:
                # Fallback: treat the whole summary as a single row
                rows = [_fix_values(agg)]
        else:
            rows = [{"value": agg}]

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table name '{table_name}'. Supported tables: discrepancies, members, quality_measures",
        )

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for table '{table_name}'.")

    # Flatten any nested dicts in rows for CSV output
    flat_rows = []
    for row in rows:
        if isinstance(row, dict):
            flat = {}
            for k, v in row.items():
                if isinstance(v, (dict, list)):
                    flat[k] = str(v)
                else:
                    flat[k] = v
            flat_rows.append(flat)
        else:
            flat_rows.append({"value": str(row)})

    # Collect all keys across all rows
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in flat_rows:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=all_keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(flat_rows)
    buf.seek(0)

    filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pipeline-json")
def export_pipeline_json():
    """Export the full PipelineResult as JSON."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    import json

    data = _fix_values(asdict(state.pipeline_result))
    content = json.dumps(data, indent=2, default=str)

    filename = f"pipeline_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
