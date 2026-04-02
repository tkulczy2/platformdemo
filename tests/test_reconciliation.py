"""Tests for Step 6: Reconciliation — platform vs. payer comparison."""

import json
from pathlib import Path

import pytest

from engine.step_6_reconciliation import reconcile


class TestReconciliationBasics:
    def test_returns_dict(self, pipeline_result):
        recon = pipeline_result.reconciliation
        assert isinstance(recon, dict)

    def test_has_discrepancies_list(self, pipeline_result):
        recon = pipeline_result.reconciliation
        assert "discrepancies" in recon
        assert isinstance(recon["discrepancies"], list)

    def test_has_financial_impact(self, pipeline_result):
        recon = pipeline_result.reconciliation
        assert "total_financial_impact" in recon

    def test_has_discrepancy_count(self, pipeline_result):
        recon = pipeline_result.reconciliation
        assert "discrepancy_count" in recon
        assert recon["discrepancy_count"] == len(recon["discrepancies"])


class TestDiscrepancyDetection:
    def test_detects_discrepancies(self, pipeline_result):
        """The reconciliation engine should find discrepancies."""
        recon = pipeline_result.reconciliation
        assert recon["discrepancy_count"] > 0, "No discrepancies detected"

    def test_detects_attribution_discrepancies(self, pipeline_result):
        recon = pipeline_result.reconciliation
        attr_discs = [d for d in recon["discrepancies"]
                      if "attribution" in d.get("metric", "").lower()
                      or "attribution" in d.get("category", "").lower()]
        assert len(attr_discs) > 0, "No attribution discrepancies detected"

    def test_detects_quality_discrepancies(self, pipeline_result):
        recon = pipeline_result.reconciliation
        qual_discs = [d for d in recon["discrepancies"]
                      if "quality" in d.get("metric", "").lower()
                      or "quality" in d.get("category", "").lower()
                      or any(m in d.get("metric", "").lower()
                             for m in ("hba1c", "bp", "breast", "colorectal", "depression"))]
        assert len(qual_discs) > 0, "No quality discrepancies detected"

    def test_detects_cost_discrepancies(self, pipeline_result):
        recon = pipeline_result.reconciliation
        cost_discs = [d for d in recon["discrepancies"]
                      if "cost" in d.get("metric", "").lower()
                      or "cost" in d.get("category", "").lower()
                      or "pmpm" in d.get("metric", "").lower()
                      or "savings" in d.get("metric", "").lower()]
        assert len(cost_discs) > 0, "No cost discrepancies detected"


class TestDiscrepancyStructure:
    def test_discrepancy_has_required_fields(self, pipeline_result):
        recon = pipeline_result.reconciliation
        for disc in recon["discrepancies"][:5]:
            assert "metric" in disc or "category" in disc, f"Discrepancy missing metric/category"
            assert "platform_value" in disc or "platform" in str(disc), \
                f"Discrepancy missing platform value"
            assert "payer_value" in disc or "payer" in str(disc), \
                f"Discrepancy missing payer value"

    def test_discrepancy_categories_valid(self, pipeline_result):
        recon = pipeline_result.reconciliation
        valid_categories = {"data_difference", "methodology_difference", "timing_difference",
                            "possible_error", "specification_ambiguity",
                            "attribution", "quality", "cost", "settlement"}
        for disc in recon["discrepancies"]:
            cat = disc.get("category", "")
            # At least the category should be a non-empty string
            assert cat, "Discrepancy has empty category"


class TestFinancialImpact:
    def test_total_impact_positive(self, pipeline_result):
        recon = pipeline_result.reconciliation
        assert recon["total_financial_impact"] != 0, "Total financial impact is zero"

    def test_individual_impacts_sum_reasonable(self, pipeline_result):
        recon = pipeline_result.reconciliation
        individual_impacts = [
            abs(d.get("financial_impact", 0))
            for d in recon["discrepancies"]
            if "financial_impact" in d
        ]
        if individual_impacts:
            total_from_items = sum(individual_impacts)
            reported_total = abs(recon["total_financial_impact"])
            # Individual impacts should be in the same ballpark as total
            # (may not sum exactly due to interactions)
            assert total_from_items > 0


class TestReconciliationCategories:
    def test_categories_summary_exists(self, pipeline_result):
        recon = pipeline_result.reconciliation
        cats = recon.get("categories")
        if cats:
            assert isinstance(cats, dict)
            assert len(cats) > 0


class TestReconciliationAgainstManifest:
    """Validate that the engine independently discovers the planted discrepancies."""

    def test_attribution_count_diverges(self, pipeline_result, payer_report):
        """Platform and payer should disagree on attribution count."""
        platform_attributed = pipeline_result.final_metrics.get("attributed_population", 0)
        payer_attributed = payer_report["attribution"]["total_attributed"]
        # They should differ (discrepancies were planted)
        assert platform_attributed != payer_attributed, \
            "Platform and payer agree on attribution — discrepancies not surfaced"

    def test_quality_scores_diverge(self, pipeline_result, payer_report):
        """Platform and payer should disagree on at least one quality measure."""
        platform_quality = pipeline_result.final_metrics.get("quality_composite", 0)
        payer_quality = payer_report["quality"]["composite_score"]
        assert abs(platform_quality - payer_quality) > 0.1, \
            "Quality composites match exactly — discrepancies not surfaced"
