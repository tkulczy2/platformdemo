"""Tests for synthetic data generator output.

Validates that generated data matches configured population size, referential
integrity, ID formats, and injected data quality issues.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import SYNTHETIC_DIR


# ---------------------------------------------------------------------------
# File existence and row counts
# ---------------------------------------------------------------------------

EXPECTED_CSV_FILES = [
    "members.csv",
    "providers.csv",
    "eligibility.csv",
    "claims_professional.csv",
    "claims_facility.csv",
    "claims_pharmacy.csv",
    "clinical_labs.csv",
    "clinical_screenings.csv",
    "clinical_vitals.csv",
]

EXPECTED_JSON_FILES = [
    "discrepancy_manifest.json",
    "payer_settlement_report.json",
]


class TestFileExistence:
    @pytest.mark.parametrize("filename", EXPECTED_CSV_FILES)
    def test_csv_file_exists(self, filename):
        assert (SYNTHETIC_DIR / filename).is_file(), f"Missing {filename}"

    @pytest.mark.parametrize("filename", EXPECTED_JSON_FILES)
    def test_json_file_exists(self, filename):
        assert (SYNTHETIC_DIR / filename).is_file(), f"Missing {filename}"

    def test_total_file_count(self):
        csv_count = len(list(SYNTHETIC_DIR.glob("*.csv")))
        json_count = len(list(SYNTHETIC_DIR.glob("*.json")))
        assert csv_count == 9
        assert json_count == 2


class TestPopulationSize:
    def test_member_count(self, demo_data):
        assert len(demo_data.members) == 1000

    def test_provider_count(self, demo_data):
        assert len(demo_data.providers) == 50

    def test_pcp_count(self, demo_data):
        pcps = demo_data.providers[demo_data.providers["is_pcp"] == True]
        assert len(pcps) >= 20

    def test_specialist_count(self, demo_data):
        specs = demo_data.providers[demo_data.providers["is_pcp"] == False]
        assert len(specs) >= 25

    def test_professional_claims_volume(self, demo_data):
        n = len(demo_data.claims_professional)
        assert 40_000 <= n <= 60_000, f"Professional claims count {n} outside expected range"


# ---------------------------------------------------------------------------
# ID format validation
# ---------------------------------------------------------------------------

class TestIDFormats:
    def test_member_id_format(self, demo_data):
        pattern = r"^MBR-\d{6}$"
        assert demo_data.members["member_id"].str.match(pattern).all()

    def test_member_ids_unique(self, demo_data):
        assert demo_data.members["member_id"].is_unique

    def test_provider_npi_format(self, demo_data):
        npis = demo_data.providers["npi"].astype(str)
        assert npis.str.match(r"^1\d{9}$").all(), "NPIs must be 10 digits starting with 1"

    def test_provider_npis_unique(self, demo_data):
        assert demo_data.providers["npi"].is_unique

    def test_professional_claim_id_format(self, demo_data):
        sample = demo_data.claims_professional["claim_id"].head(1000)
        assert sample.str.match(r"^CLM-P-\d{8}$").all()

    def test_facility_claim_id_format(self, demo_data):
        sample = demo_data.claims_facility["claim_id"].head(500)
        assert sample.str.match(r"^CLM-F-\d{8}$").all()

    def test_pharmacy_claim_id_format(self, demo_data):
        sample = demo_data.claims_pharmacy["claim_id"].head(500)
        assert sample.str.match(r"^CLM-RX-\d{8}$").all()


# ---------------------------------------------------------------------------
# Referential integrity
# ---------------------------------------------------------------------------

class TestReferentialIntegrity:
    def test_claims_reference_valid_members(self, demo_data):
        member_ids = set(demo_data.members["member_id"])
        claim_member_ids = set(demo_data.claims_professional["member_id"])
        orphans = claim_member_ids - member_ids
        assert len(orphans) == 0, f"Claims reference {len(orphans)} non-existent member IDs"

    def test_eligibility_references_valid_members(self, demo_data):
        member_ids = set(demo_data.members["member_id"])
        elig_member_ids = set(demo_data.eligibility["member_id"])
        orphans = elig_member_ids - member_ids
        assert len(orphans) == 0

    def test_clinical_labs_reference_valid_members(self, demo_data):
        member_ids = set(demo_data.members["member_id"])
        lab_member_ids = set(demo_data.clinical_labs["member_id"])
        orphans = lab_member_ids - member_ids
        assert len(orphans) == 0

    def test_claims_reference_valid_providers(self, demo_data):
        provider_npis = set(demo_data.providers["npi"].astype(str))
        claim_npis = demo_data.claims_professional["rendering_npi"].dropna().astype(str)
        valid_npis = set(claim_npis)
        orphans = valid_npis - provider_npis
        # Some claims may have NPIs from outside the ACO (realistic), but the
        # vast majority should reference ACO providers.
        orphan_pct = len(orphans) / len(valid_npis) if len(valid_npis) > 0 else 0
        assert orphan_pct < 0.15, f"{orphan_pct:.0%} of claim NPIs not in provider roster"


# ---------------------------------------------------------------------------
# Injected data quality issues
# ---------------------------------------------------------------------------

class TestDataQualityIssues:
    def test_missing_npi_rate(self, demo_data, config):
        claims = demo_data.claims_professional
        missing = claims["rendering_npi"].isna().sum()
        total = len(claims)
        rate = missing / total
        expected = config.pct_missing_npi
        assert rate > expected * 0.3, f"Missing NPI rate {rate:.3f} too low (expected ~{expected})"
        assert rate < expected * 3.0, f"Missing NPI rate {rate:.3f} too high (expected ~{expected})"

    def test_duplicate_claims_exist(self, demo_data):
        claims = demo_data.claims_professional
        dup_count = claims["claim_id"].duplicated().sum()
        assert dup_count > 0, "Expected some duplicate claim IDs"

    def test_enrollment_gaps_exist(self, demo_data):
        elig = demo_data.eligibility
        members_with_multiple_spans = elig.groupby("member_id").size()
        members_with_gaps = (members_with_multiple_spans > 1).sum()
        assert members_with_gaps > 0, "Expected some members with enrollment gaps"


# ---------------------------------------------------------------------------
# Discrepancy manifest
# ---------------------------------------------------------------------------

class TestDiscrepancyManifest:
    def test_attribution_discrepancy_count(self, discrepancy_manifest, config):
        attr_discs = discrepancy_manifest.get("attribution_discrepancies", [])
        assert len(attr_discs) == config.num_attribution_discrepancies

    def test_quality_discrepancy_count(self, discrepancy_manifest, config):
        qual_discs = discrepancy_manifest.get("quality_discrepancies", [])
        assert len(qual_discs) == config.num_quality_discrepancies

    def test_cost_discrepancy_count(self, discrepancy_manifest, config):
        cost_discs = discrepancy_manifest.get("cost_discrepancies", [])
        assert len(cost_discs) == config.num_cost_discrepancies

    def test_manifest_has_summary(self, discrepancy_manifest):
        assert "summary" in discrepancy_manifest
        summary = discrepancy_manifest["summary"]
        assert "total_attribution_discrepancies" in summary
        assert "estimated_total_financial_impact" in summary


# ---------------------------------------------------------------------------
# Payer settlement report structure
# ---------------------------------------------------------------------------

class TestPayerSettlementReport:
    def test_has_required_sections(self, payer_report):
        assert "attribution" in payer_report
        assert "quality" in payer_report
        assert "cost" in payer_report

    def test_quality_measures_present(self, payer_report):
        measures = payer_report["quality"]["measures"]
        expected = {"hba1c_poor_control", "controlling_bp", "breast_cancer_screening",
                    "colorectal_screening", "depression_screening"}
        assert set(measures.keys()) == expected

    def test_cost_values_positive(self, payer_report):
        cost = payer_report["cost"]
        assert cost["benchmark_pmpm"] > 0
        assert cost["actual_pmpm"] > 0
