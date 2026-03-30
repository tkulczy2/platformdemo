"""Generate 1,000 synthetic Medicare beneficiaries.

All data is fully synthetic — no real PHI is generated or stored.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

from generator.config import GenerationConfig


# ---------------------------------------------------------------------------
# National Medicare race/ethnicity distribution (approximate CMS data)
# ---------------------------------------------------------------------------
_RACE_ETHNICITY_LABELS = [
    "Non-Hispanic White",
    "Non-Hispanic Black",
    "Hispanic",
    "Asian/Pacific Islander",
    "American Indian/Alaska Native",
    "Other/Unknown",
]
_RACE_ETHNICITY_WEIGHTS = [0.77, 0.09, 0.07, 0.04, 0.01, 0.02]

# ---------------------------------------------------------------------------
# Zone weights — urban core gets more members than rural fringe
# ---------------------------------------------------------------------------
_ZONE_WEIGHTS = [0.40, 0.30, 0.20, 0.10]  # zones 1-4

# Number of zips per zone (must match config.service_area_zips layout)
_ZIPS_PER_ZONE = [10, 10, 10, 5]


def _assign_zips_by_zone(
    rng: np.random.Generator,
    service_area_zips: list[str],
    n: int,
) -> list[str]:
    """Sample zip codes with geographic clustering across the four zones."""
    zones = [
        service_area_zips[0:10],    # Zone 1 — Urban core
        service_area_zips[10:20],   # Zone 2 — Suburban
        service_area_zips[20:30],   # Zone 3 — Exurban
        service_area_zips[30:35],   # Zone 4 — Rural fringe
    ]

    # For each member, first pick a zone then pick a zip within that zone
    zone_choices = rng.choice(len(zones), size=n, p=_ZONE_WEIGHTS)
    zips: list[str] = []
    for zone_idx in zone_choices:
        zone_zips = zones[zone_idx]
        zips.append(rng.choice(zone_zips))
    return zips


def _generate_age(rng: np.random.Generator, n: int) -> np.ndarray:
    """Return ages skewed toward 65-85 with a tail to 100.

    Uses a shifted log-normal so the bulk of mass sits between 65 and 85
    while a realistic tail extends to ~100.  Values are clipped to [65, 100].
    """
    # Log-normal with loc=65, scale ≈ 8, log-sigma ≈ 0.18 gives median ~73
    base = rng.lognormal(mean=np.log(8), sigma=0.35, size=n)
    ages = 65 + base
    return np.clip(ages, 65, 100).astype(int)


def _generate_hcc_risk_scores(
    rng: np.random.Generator,
    ages: np.ndarray,
    dual_eligible: np.ndarray,
) -> np.ndarray:
    """Generate HCC risk scores (0.5–4.0, log-normal, centered ~1.2).

    Older age and dual eligibility both nudge the score upward.
    """
    n = len(ages)

    # Base log-normal: median ~1.2, right tail to 4+
    base_scores = rng.lognormal(mean=np.log(1.2), sigma=0.45, size=n)

    # Age adjustment: each decade over 65 adds ~0.04 to the score
    age_bonus = ((ages - 65) / 10) * 0.04

    # Dual-eligibility adjustment
    dual_bonus = dual_eligible * rng.uniform(0.10, 0.30, size=n)

    scores = base_scores + age_bonus + dual_bonus
    return np.clip(scores, 0.5, 4.0).round(4)


def _generate_dual_eligible(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """~20% dual-eligible flag."""
    return rng.random(n) < 0.20


def generate_members(
    config: GenerationConfig,
    providers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the member roster.

    Parameters
    ----------
    config:
        GenerationConfig controlling counts, seed, service area, etc.
    providers_df:
        Provider roster produced by ``generator.providers``.  Only PCP rows
        (``provider_type == 'PCP'``) are used here.

    Returns
    -------
    pd.DataFrame with one row per member.
    """
    rng = np.random.default_rng(config.seed)
    fake = Faker("en_US")
    Faker.seed(config.seed)

    n = config.num_members
    perf_start = pd.Timestamp(config.performance_period_start)
    perf_end = pd.Timestamp(config.performance_period_end)
    data_as_of = pd.Timestamp(config.data_as_of_date)

    # ------------------------------------------------------------------
    # 1. Member IDs
    # ------------------------------------------------------------------
    member_ids = [f"MBR-{i:06d}" for i in range(1, n + 1)]

    # ------------------------------------------------------------------
    # 2. Demographics
    # ------------------------------------------------------------------
    ages = _generate_age(rng, n)
    sexes = rng.choice(["M", "F"], size=n, p=[0.49, 0.51])  # slight female majority in Medicare

    race_ethnicities = rng.choice(
        _RACE_ETHNICITY_LABELS,
        size=n,
        p=_RACE_ETHNICITY_WEIGHTS,
    ).tolist()

    # ------------------------------------------------------------------
    # 3. Date of birth — derive from age as of performance year start
    # ------------------------------------------------------------------
    # Birth year = perf_start.year - age, month/day random
    birth_years = perf_start.year - ages
    birth_months = rng.integers(1, 13, size=n)
    birth_days_max = [28] * n  # Safe upper bound for all months
    birth_days = rng.integers(1, 29, size=n)  # 1-28 safe for all months

    dobs: list[str] = []
    for yr, mo, dy in zip(birth_years, birth_months, birth_days):
        try:
            dob = pd.Timestamp(year=int(yr), month=int(mo), day=int(dy))
        except ValueError:
            dob = pd.Timestamp(year=int(yr), month=int(mo), day=28)
        dobs.append(dob.strftime("%Y-%m-%d"))

    # ------------------------------------------------------------------
    # 4. Geographic distribution
    # ------------------------------------------------------------------
    zip_codes = _assign_zips_by_zone(rng, config.service_area_zips, n)

    # ------------------------------------------------------------------
    # 5. Dual eligibility (~20%)
    # ------------------------------------------------------------------
    dual_eligible_arr = _generate_dual_eligible(rng, n)

    # ------------------------------------------------------------------
    # 6. HCC risk scores
    # ------------------------------------------------------------------
    hcc_risk_scores = _generate_hcc_risk_scores(rng, ages, dual_eligible_arr)

    # ------------------------------------------------------------------
    # 7. PCP assignment
    # ------------------------------------------------------------------
    pcp_df = providers_df[providers_df["is_pcp"] == True].copy()
    if pcp_df.empty:
        raise ValueError("providers_df contains no PCP rows — cannot assign PCPs to members.")

    pcp_npis = pcp_df["npi"].tolist()

    # Assign members to PCPs with realistic panel-size variation:
    # weight each PCP by a random panel capacity draw so panels aren't equal.
    pcp_weights_raw = rng.dirichlet(np.ones(len(pcp_npis)) * 2.0)
    pcp_assignments = rng.choice(pcp_npis, size=n, p=pcp_weights_raw).tolist()

    # ------------------------------------------------------------------
    # 8. Deceased members (~2% within the performance year)
    # ------------------------------------------------------------------
    deceased_mask = rng.random(n) < 0.02
    deceased_dates: list[str | None] = []
    for is_deceased in deceased_mask:
        if is_deceased:
            # Random date within the performance year, before data_as_of
            days_range = (min(perf_end, data_as_of) - perf_start).days
            offset = rng.integers(0, max(days_range, 1))
            deceased_dt = perf_start + pd.Timedelta(days=int(offset))
            deceased_dates.append(deceased_dt.strftime("%Y-%m-%d"))
        else:
            deceased_dates.append(None)

    # ------------------------------------------------------------------
    # 9. Attribution edge-case members (~30 members)
    #    These members have their home PCP deliberately set to a different
    #    provider than their most-visited PCP — so the attribution engine
    #    must resolve a true plurality conflict.
    #    We track them with a flag so the claims generator can spread their
    #    visits across multiple PCPs.
    # ------------------------------------------------------------------
    edge_case_indices = rng.choice(n, size=30, replace=False)
    attribution_edge_case = np.zeros(n, dtype=bool)
    attribution_edge_case[edge_case_indices] = True

    # For edge-case members, shuffle their PCP assignment to a *different* PCP
    # so claims can later be generated visiting multiple PCPs equally.
    for idx in edge_case_indices:
        current = pcp_assignments[idx]
        alternatives = [p for p in pcp_npis if p != current]
        if alternatives:
            pcp_assignments[idx] = rng.choice(alternatives)

    # ------------------------------------------------------------------
    # 10. Assemble DataFrame
    # ------------------------------------------------------------------
    df = pd.DataFrame(
        {
            "member_id": member_ids,
            "date_of_birth": dobs,
            "age": ages,
            "sex": sexes,
            "race_ethnicity": race_ethnicities,
            "zip_code": zip_codes,
            "dual_eligible": dual_eligible_arr,
            "hcc_risk_score": hcc_risk_scores,
            "pcp_npi": pcp_assignments,
            "deceased_date": deceased_dates,
            "attribution_edge_case": attribution_edge_case,
        }
    )

    # Enforce date column dtypes (string for CSV round-trip)
    df["date_of_birth"] = df["date_of_birth"].astype(str)
    df["dual_eligible"] = df["dual_eligible"].astype(bool)
    df["attribution_edge_case"] = df["attribution_edge_case"].astype(bool)

    return df
