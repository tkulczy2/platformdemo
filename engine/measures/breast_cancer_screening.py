"""Breast Cancer Screening (NQF-2372).

Denominator: Attributed female members age 50-74
Exclusions: Bilateral mastectomy, hospice
Numerator: Members with mammogram in the past 27 months
"""

import pandas as pd

from engine.data_loader import LoadedData
from engine.measures.base import BaseMeasure
from engine.provenance import DataReference, MemberDetail


class BreastCancerScreening(BaseMeasure):
    measure_id = "NQF-2372"
    measure_name = "Breast Cancer Screening"
    measure_description = (
        "Percentage of women 50-74 who had a mammogram to screen for "
        "breast cancer in the past 27 months."
    )
    data_sources_used = ["claims_professional.csv", "clinical_screenings.csv"]
    is_inverse = False

    MAMMOGRAM_CPT = {"77067", "77066", "77065", "G0202", "G0204", "G0206"}
    MASTECTOMY_CODES = {"Z90.11", "Z90.12", "Z90.13"}
    HOSPICE_CODES = {"Z51.5"}

    def identify_denominator(self, data, attributed_members, members_df):
        perf_year_end = pd.Timestamp("2025-12-31")
        attributed_set = set(attributed_members)

        eligible = members_df[
            (members_df["member_id"].isin(attributed_set)) &
            (members_df["sex"].str.upper() == "F") &
            (members_df["date_of_birth"].notna())
        ].copy()
        eligible["age"] = ((perf_year_end - eligible["date_of_birth"]).dt.days // 365)
        eligible = eligible[(eligible["age"] >= 50) & (eligible["age"] <= 74)]

        return [
            MemberDetail(
                member_id=row["member_id"],
                outcome="in_denominator",
                reason=f"Female, age {int(row['age'])} (50-74)",
                data_references=[DataReference(
                    source_file="members.csv", row_indices=[idx],
                    columns_used=["member_id", "sex", "date_of_birth"],
                    description=f"Female, age {int(row['age'])}",
                )],
                intermediate_values={"age": int(row["age"]), "sex": "F"},
            )
            for idx, row in eligible.iterrows()
        ]

    def apply_exclusions(self, denominator_members, data):
        claims = data.claims_professional
        member_ids = [m.member_id for m in denominator_members]
        member_claims = claims[claims["member_id"].isin(member_ids)]

        exclusion_codes = self.MASTECTOMY_CODES | self.HOSPICE_CODES
        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        excluded_set = set()
        for col in dx_cols:
            if col in member_claims.columns:
                excl = member_claims[member_claims[col].isin(exclusion_codes)]
                excluded_set.update(excl["member_id"].unique())

        eligible = []
        excluded = []
        for m in denominator_members:
            if m.member_id in excluded_set:
                m.reason = "Excluded: mastectomy or hospice"
                excluded.append(m)
            else:
                eligible.append(m)
        return eligible, excluded

    def evaluate_numerator(self, eligible_members, data):
        """Members with mammogram in past 27 months (vectorized)."""
        screenings = data.clinical_screenings
        claims = data.claims_professional
        cutoff = pd.Timestamp("2025-12-31") - pd.DateOffset(months=27)
        member_ids = [m.member_id for m in eligible_members]

        # EHR mammograms
        ehr_mamm = screenings[
            (screenings["member_id"].isin(member_ids)) &
            (screenings["screening_type"] == "mammogram") &
            (screenings["screening_date"] >= cutoff)
        ]
        ehr_set = set(ehr_mamm["member_id"].unique())

        # Claims mammograms
        claims_mamm = claims[
            (claims["member_id"].isin(member_ids)) &
            (claims["procedure_code"].isin(self.MAMMOGRAM_CPT)) &
            (claims["service_date"] >= cutoff)
        ]
        claims_set = set(claims_mamm["member_id"].unique())
        screened = ehr_set | claims_set

        in_numerator = []
        not_in_numerator = []
        for m in eligible_members:
            if m.member_id in screened:
                m.reason = "Mammogram completed within 27 months"
                m.intermediate_values["screening_found"] = True
                in_numerator.append(m)
            else:
                m.reason = "No mammogram found within 27 months"
                m.intermediate_values["screening_found"] = False
                not_in_numerator.append(m)
        return in_numerator, not_in_numerator
