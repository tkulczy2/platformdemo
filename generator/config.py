"""Generation configuration — all parameters for synthetic data generation."""

from dataclasses import dataclass, field


@dataclass
class GenerationConfig:
    # Population
    num_members: int = 1000
    num_providers: int = 50
    num_pcp_providers: int = 20
    num_specialist_providers: int = 30

    # Time
    performance_year: int = 2025
    performance_period_start: str = "2025-01-01"
    performance_period_end: str = "2025-12-31"
    historical_months: int = 36
    data_as_of_date: str = "2025-10-15"

    # Claims volume (per member per month)
    avg_professional_claims_pmpm: float = 4.5
    avg_facility_claims_pmpm: float = 0.8
    avg_pharmacy_claims_pmpm: float = 3.0

    # Data quality issues to inject
    pct_missing_npi: float = 0.02
    pct_duplicate_claims: float = 0.01
    pct_enrollment_gaps: float = 0.08
    pct_conflicting_clinical: float = 0.05

    # Discrepancies to plant (for reconciliation demo)
    num_attribution_discrepancies: int = 23
    num_quality_discrepancies: int = 15
    num_cost_discrepancies: int = 8

    # Random seed for reproducibility
    seed: int = 42

    # ACO service area zip codes (3-4 geographic zones)
    service_area_zips: list[str] = field(default_factory=lambda: [
        # Zone 1 — Urban core
        "30301", "30302", "30303", "30304", "30305",
        "30306", "30307", "30308", "30309", "30310",
        # Zone 2 — Suburban
        "30318", "30319", "30324", "30326", "30327",
        "30328", "30329", "30331", "30332", "30334",
        # Zone 3 — Exurban
        "30340", "30341", "30342", "30344", "30345",
        "30346", "30349", "30350", "30354", "30360",
        # Zone 4 — Rural fringe
        "30004", "30005", "30009", "30022", "30024",
    ])

    # E&M codes that drive attribution
    qualifying_em_codes: list[str] = field(default_factory=lambda: [
        "99201", "99202", "99203", "99204", "99205",
        "99211", "99212", "99213", "99214", "99215",
        "99381", "99382", "99383", "99384", "99385",
        "99386", "99387", "99391", "99392", "99393",
        "99394", "99395", "99396", "99397",
        "G0438", "G0439",
    ])

    # Practice site names
    practice_sites: list[dict] = field(default_factory=lambda: [
        {"id": "SITE-001", "name": "Peachtree Primary Care", "tin": "123456789"},
        {"id": "SITE-002", "name": "Midtown Medical Group", "tin": "234567890"},
        {"id": "SITE-003", "name": "Northside Family Medicine", "tin": "345678901"},
        {"id": "SITE-004", "name": "Buckhead Specialty Clinic", "tin": "456789012"},
        {"id": "SITE-005", "name": "Southside Health Partners", "tin": "567890123"},
    ])

    # Specialist types and counts
    specialist_distribution: dict = field(default_factory=lambda: {
        "Cardiology": 5,
        "Endocrinology": 4,
        "Orthopedics": 4,
        "Pulmonology": 3,
        "General Surgery": 4,
        "Nephrology": 3,
        "Neurology": 3,
        "Psychiatry": 4,
    })
