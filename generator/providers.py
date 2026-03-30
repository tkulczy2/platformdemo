"""Generate 50 ACO provider records: 20 PCPs + 30 specialists.

NPI format: 10-digit string starting with "1".
All providers are ACO participants; 2-3 have termination dates mid-year 2025.
2-3 providers use ambiguous taxonomy codes (NP in primary-care setting).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

from generator.config import GenerationConfig

# ---------------------------------------------------------------------------
# NUCC taxonomy reference
# ---------------------------------------------------------------------------

# Each entry: (taxonomy_code, specialty_label, is_pcp)
PCP_TAXONOMIES: list[tuple[str, str, bool]] = [
    ("207Q00000X", "Family Medicine", True),
    ("207R00000X", "Internal Medicine", True),
    ("207RG0300X", "Geriatrics", True),
]

SPECIALIST_TAXONOMIES: dict[str, tuple[str, bool]] = {
    "Cardiology":      ("207RC0000X", False),
    "Endocrinology":   ("207RE0101X", False),
    "Orthopedics":     ("207X00000X", False),
    "Pulmonology":     ("207RP1001X", False),
    "General Surgery": ("208600000X", False),
    "Nephrology":      ("207RN0300X", False),
    "Neurology":       ("2084N0400X", False),
    "Psychiatry":      ("2084P0800X", False),
}

# Ambiguous NP taxonomy — nurse practitioner, primary-care setting.
# These providers are assigned a PCP practice site but their taxonomy is not a
# traditional physician code, creating attribution edge cases.
AMBIGUOUS_TAXONOMY = ("363L00000X", "Nurse Practitioner", True)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _generate_npi(rng: np.random.Generator, used: set[str]) -> str:
    """Return a unique 10-digit NPI string starting with '1'."""
    while True:
        # Digits 2-10 are random (9 random digits)
        suffix = rng.integers(100_000_000, 999_999_999)
        npi = f"1{suffix}"
        if npi not in used:
            used.add(npi)
            return npi


def _provider_name(fake: Faker) -> str:
    """Return 'LastName, FirstName MI' format."""
    last = fake.last_name()
    first = fake.first_name()
    middle_initial = fake.lexify("?", letters="ABCDEFGHJKLMNPRSTW").upper()
    return f"{last}, {first} {middle_initial}"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_providers(config: GenerationConfig) -> pd.DataFrame:
    """Generate and return a DataFrame of 50 ACO providers."""

    rng = np.random.default_rng(config.seed)
    fake = Faker()
    Faker.seed(config.seed)

    sites = config.practice_sites          # list of dicts with id/name/tin
    num_sites = len(sites)

    used_npis: set[str] = set()
    rows: list[dict] = []

    # -----------------------------------------------------------------------
    # Build PCP list (20 providers)
    # Distribute evenly across the 3 PCP taxonomy types, then fill remainder.
    # We designate 2 of the 20 PCP slots as ambiguous (NP).
    # -----------------------------------------------------------------------
    num_ambiguous = 2                      # creates 2 attribution edge cases
    num_true_pcp = config.num_pcp_providers - num_ambiguous  # 18 true PCPs

    pcp_taxonomy_pool = PCP_TAXONOMIES * (num_true_pcp // len(PCP_TAXONOMIES) + 1)
    pcp_taxonomy_assignments = pcp_taxonomy_pool[:num_true_pcp]
    # Shuffle deterministically
    pcp_indices = rng.permutation(len(pcp_taxonomy_assignments))
    pcp_taxonomy_assignments = [pcp_taxonomy_assignments[i] for i in pcp_indices]

    # PCP sites: sites 0, 1, 2 are primary-care oriented
    pcp_site_pool = sites[:3]

    for i in range(num_true_pcp):
        site = pcp_site_pool[i % len(pcp_site_pool)]
        taxonomy_code, specialty, is_pcp = pcp_taxonomy_assignments[i]
        rows.append({
            "npi":                    _generate_npi(rng, used_npis),
            "provider_name":          _provider_name(fake),
            "taxonomy_code":          taxonomy_code,
            "specialty":              specialty,
            "is_pcp":                 is_pcp,
            "practice_location_id":   site["id"],
            "practice_location_name": site["name"],
            "tin":                    site["tin"],
            "aco_participant":        True,
            "_provider_class":        "pcp",
        })

    # Ambiguous NP providers — assigned to PCP sites but non-physician taxonomy
    for i in range(num_ambiguous):
        site = pcp_site_pool[i % len(pcp_site_pool)]
        taxonomy_code, specialty, is_pcp = AMBIGUOUS_TAXONOMY
        rows.append({
            "npi":                    _generate_npi(rng, used_npis),
            "provider_name":          _provider_name(fake),
            "taxonomy_code":          taxonomy_code,
            "specialty":              specialty,
            "is_pcp":                 is_pcp,   # True — NP in PCP setting
            "practice_location_id":   site["id"],
            "practice_location_name": site["name"],
            "tin":                    site["tin"],
            "aco_participant":        True,
            "_provider_class":        "ambiguous_np",
        })

    # -----------------------------------------------------------------------
    # Build specialist list (30 providers)
    # -----------------------------------------------------------------------
    specialist_site_pool = sites[3:]  # sites 3 and 4 are specialty-oriented
    if not specialist_site_pool:
        specialist_site_pool = sites  # fallback: all sites

    specialist_order: list[tuple[str, str, bool]] = []
    for specialty_name, count in config.specialist_distribution.items():
        taxonomy_code, is_pcp = SPECIALIST_TAXONOMIES[specialty_name]
        for _ in range(count):
            specialist_order.append((taxonomy_code, specialty_name, is_pcp))

    # Confirm count matches config
    assert len(specialist_order) == config.num_specialist_providers, (
        f"Specialist distribution sums to {len(specialist_order)}, "
        f"expected {config.num_specialist_providers}"
    )

    for i, (taxonomy_code, specialty, is_pcp) in enumerate(specialist_order):
        site = specialist_site_pool[i % len(specialist_site_pool)]
        rows.append({
            "npi":                    _generate_npi(rng, used_npis),
            "provider_name":          _provider_name(fake),
            "taxonomy_code":          taxonomy_code,
            "specialty":              specialty,
            "is_pcp":                 is_pcp,
            "practice_location_id":   site["id"],
            "practice_location_name": site["name"],
            "tin":                    site["tin"],
            "aco_participant":        True,
            "_provider_class":        "specialist",
        })

    df = pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # Assign effective dates (date each provider joined the ACO)
    # All joined before the performance year; spread across 2022-2024.
    # -----------------------------------------------------------------------
    effective_years = rng.choice([2022, 2023, 2024], size=len(df))
    effective_months = rng.integers(1, 13, size=len(df))
    effective_days = rng.integers(1, 29, size=len(df))  # safe upper bound

    effective_dates = [
        f"{y:04d}-{m:02d}-{d:02d}"
        for y, m, d in zip(effective_years, effective_months, effective_days)
    ]
    df["effective_date"] = effective_dates

    # -----------------------------------------------------------------------
    # Assign termination dates: 2-3 providers terminated mid-year 2025.
    # Pick from non-ambiguous providers so edge-case NPs stay active.
    # -----------------------------------------------------------------------
    eligible_for_termination = df[df["_provider_class"] != "ambiguous_np"].index.tolist()
    num_terminated = int(rng.integers(2, 4))  # 2 or 3
    terminated_indices = rng.choice(
        eligible_for_termination, size=num_terminated, replace=False
    )

    df["termination_date"] = None

    term_months = rng.integers(4, 10, size=num_terminated)  # April–September 2025
    term_days = rng.integers(1, 29, size=num_terminated)
    for idx, month, day in zip(terminated_indices, term_months, term_days):
        df.at[idx, "termination_date"] = f"2025-{month:02d}-{day:02d}"

    # -----------------------------------------------------------------------
    # Drop internal helper column, reorder columns to match spec
    # -----------------------------------------------------------------------
    df = df.drop(columns=["_provider_class"])

    column_order = [
        "npi",
        "provider_name",
        "taxonomy_code",
        "specialty",
        "is_pcp",
        "practice_location_id",
        "practice_location_name",
        "tin",
        "aco_participant",
        "effective_date",
        "termination_date",
    ]
    df = df[column_order].reset_index(drop=True)

    return df
