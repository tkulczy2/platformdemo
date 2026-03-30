"""Depression Screening and Follow-Up (NQF-0418).

Denominator: Attributed members age 12+
Exclusions: Existing depression/bipolar diagnosis with active treatment
Numerator: Members with documented depression screening (PHQ-2 or PHQ-9)
"""

import pandas as pd

from engine.data_loader import LoadedData
from engine.measures.base import BaseMeasure
from engine.provenance import DataReference, MemberDetail


class DepressionScreening(BaseMeasure):
    measure_id = "NQF-0418"
    measure_name = "Depression Screening and Follow-Up"
    measure_description = (
        "Percentage of patients aged 12+ who were screened for depression "
        "using a standardized tool (PHQ-2/PHQ-9) and, if positive, had a "
        "follow-up plan documented."
    )
    data_sources_used = ["claims_professional.csv", "clinical_screenings.csv"]
    is_inverse = False

    DEPRESSION_SCREENING_CPT = {"96127", "G0444"}
    DEPRESSION_PREFIXES = ("F32", "F33")
    BIPOLAR_PREFIXES = ("F31",)

    def identify_denominator(self, data, attributed_members, members_df):
        perf_year_end = pd.Timestamp("2025-12-31")
        attributed_set = set(attributed_members)

        eligible = members_df[
            (members_df["member_id"].isin(attributed_set)) &
            (members_df["date_of_birth"].notna())
        ].copy()
        eligible["age"] = ((perf_year_end - eligible["date_of_birth"]).dt.days // 365)
        eligible = eligible[eligible["age"] >= 12]

        return [
            MemberDetail(
                member_id=row["member_id"],
                outcome="in_denominator",
                reason=f"Age {int(row['age'])} (≥ 12)",
                data_references=[DataReference(
                    source_file="members.csv", row_indices=[idx],
                    columns_used=["member_id", "date_of_birth"],
                    description=f"Age {int(row['age'])}",
                )],
                intermediate_values={"age": int(row["age"])},
            )
            for idx, row in eligible.iterrows()
        ]

    def apply_exclusions(self, denominator_members, data):
        """Exclude members with existing depression/bipolar with active treatment."""
        claims = data.claims_professional
        pharmacy = data.claims_pharmacy
        member_ids = [m.member_id for m in denominator_members]

        # Find members with depression/bipolar dx
        member_claims = claims[claims["member_id"].isin(member_ids)]
        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        dx_members = set()
        for col in dx_cols:
            if col not in member_claims.columns:
                continue
            for prefix in self.DEPRESSION_PREFIXES + self.BIPOLAR_PREFIXES:
                matches = member_claims[member_claims[col].str.startswith(prefix, na=False)]
                dx_members.update(matches["member_id"].unique())

        # Find members on antidepressants
        antidepressant_classes = {"antidepressant", "ssri", "snri"}
        member_rx = pharmacy[pharmacy["member_id"].isin(member_ids)]
        on_treatment = set()
        if not member_rx.empty and "drug_class" in member_rx.columns:
            treated = member_rx[member_rx["drug_class"].str.lower().isin(antidepressant_classes)]
            on_treatment = set(treated["member_id"].unique())

        # Exclude only if both dx AND treatment
        excluded_set = dx_members & on_treatment

        eligible = []
        excluded = []
        for m in denominator_members:
            if m.member_id in excluded_set:
                m.reason = "Excluded: existing depression/bipolar with active treatment"
                excluded.append(m)
            else:
                eligible.append(m)
        return eligible, excluded

    def evaluate_numerator(self, eligible_members, data):
        """Members with documented depression screening (vectorized)."""
        screenings = data.clinical_screenings
        claims = data.claims_professional
        perf_start = pd.Timestamp("2025-01-01")
        perf_end = pd.Timestamp("2025-12-31")
        member_ids = [m.member_id for m in eligible_members]

        # EHR screenings
        ehr_dep = screenings[
            (screenings["member_id"].isin(member_ids)) &
            (screenings["screening_type"] == "depression_screening") &
            (screenings["screening_date"] >= perf_start) &
            (screenings["screening_date"] <= perf_end)
        ]
        ehr_set = set(ehr_dep["member_id"].unique())

        # Claims screenings
        claims_dep = claims[
            (claims["member_id"].isin(member_ids)) &
            (claims["procedure_code"].isin(self.DEPRESSION_SCREENING_CPT)) &
            (claims["service_date"] >= perf_start) &
            (claims["service_date"] <= perf_end)
        ]
        claims_set = set(claims_dep["member_id"].unique())
        screened = ehr_set | claims_set

        in_numerator = []
        not_in_numerator = []
        for m in eligible_members:
            if m.member_id in screened:
                m.reason = "Depression screening completed during performance year"
                m.intermediate_values["screening_found"] = True
                in_numerator.append(m)
            else:
                m.reason = "No depression screening found during performance year"
                m.intermediate_values["screening_found"] = False
                not_in_numerator.append(m)
        return in_numerator, not_in_numerator
