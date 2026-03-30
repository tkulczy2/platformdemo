"""Generate enrollment/eligibility records for all members.

~92% continuous full-year enrollment, ~5% with gaps, ~3% terminated mid-year.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.config import GenerationConfig


def generate_eligibility(
    config: GenerationConfig,
    members_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate eligibility/enrollment records.

    Most members get a single row covering the full performance year.
    Members with gaps get two rows (before + after gap).  Terminated
    members get one row with an enrollment_end_date.
    """
    rng = np.random.default_rng(config.seed + 1)  # offset seed for this module

    perf_start = pd.Timestamp(config.performance_period_start)
    perf_end = pd.Timestamp(config.performance_period_end)
    data_as_of = pd.Timestamp(config.data_as_of_date)

    n = len(members_df)
    rows: list[dict] = []

    # Decide member enrollment categories
    pct_gap = config.pct_enrollment_gaps   # 8%
    pct_terminated = 0.03                   # 3%
    pct_continuous = 1.0 - pct_gap - pct_terminated  # ~89%

    categories = rng.choice(
        ["continuous", "gap", "terminated"],
        size=n,
        p=[pct_continuous, pct_gap, pct_terminated],
    )

    # Override: deceased members are terminated on their deceased_date
    for i, row in members_df.iterrows():
        if pd.notna(row.get("deceased_date")) and row["deceased_date"]:
            categories[i] = "deceased"

    for i, member_row in members_df.iterrows():
        member_id = member_row["member_id"]

        cat = categories[i]

        if cat == "continuous":
            rows.append({
                "member_id": member_id,
                "payer_id": "PAYER-001",
                "contract_id": "CONTRACT-MSSP-2025",
                "product_type": "Medicare FFS",
                "enrollment_start_date": perf_start.strftime("%Y-%m-%d"),
                "enrollment_end_date": None,
                "attribution_eligible": True,
            })

        elif cat == "gap":
            # Gap: 1-3 months somewhere in the year
            gap_duration_months = int(rng.integers(1, 4))
            # Gap starts between month 2 and month 9 to allow pre/post segments
            gap_start_month = int(rng.integers(2, 10))
            gap_start = pd.Timestamp(year=config.performance_year, month=gap_start_month, day=1)
            gap_end_month = min(gap_start_month + gap_duration_months, 12)
            gap_end = pd.Timestamp(year=config.performance_year, month=gap_end_month, day=1)

            # Pre-gap enrollment
            rows.append({
                "member_id": member_id,
                "payer_id": "PAYER-001",
                "contract_id": "CONTRACT-MSSP-2025",
                "product_type": "Medicare FFS",
                "enrollment_start_date": perf_start.strftime("%Y-%m-%d"),
                "enrollment_end_date": (gap_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "attribution_eligible": True,
            })

            # Post-gap re-enrollment (only if gap ends before year end)
            if gap_end_month < 12:
                rows.append({
                    "member_id": member_id,
                    "payer_id": "PAYER-001",
                    "contract_id": "CONTRACT-MSSP-2025",
                    "product_type": "Medicare FFS",
                    "enrollment_start_date": gap_end.strftime("%Y-%m-%d"),
                    "enrollment_end_date": None,
                    "attribution_eligible": True,
                })

        elif cat == "terminated":
            # Terminated mid-year: enrollment ends between month 3 and month 10
            end_month = int(rng.integers(3, 11))
            end_day = int(rng.integers(1, 29))
            end_date = pd.Timestamp(
                year=config.performance_year, month=end_month, day=end_day
            )
            rows.append({
                "member_id": member_id,
                "payer_id": "PAYER-001",
                "contract_id": "CONTRACT-MSSP-2025",
                "product_type": "Medicare FFS",
                "enrollment_start_date": perf_start.strftime("%Y-%m-%d"),
                "enrollment_end_date": end_date.strftime("%Y-%m-%d"),
                "attribution_eligible": True,
            })

        elif cat == "deceased":
            deceased_date = member_row["deceased_date"]
            rows.append({
                "member_id": member_id,
                "payer_id": "PAYER-001",
                "contract_id": "CONTRACT-MSSP-2025",
                "product_type": "Medicare FFS",
                "enrollment_start_date": perf_start.strftime("%Y-%m-%d"),
                "enrollment_end_date": deceased_date,
                "attribution_eligible": True,
            })

    df = pd.DataFrame(rows)
    return df
