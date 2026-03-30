"""HbA1c Poor Control (NQF-0059) — inverse measure (lower rate = better).

Denominator: Attributed members age 18-75 with diabetes diagnosis (ICD-10: E11.x)
Exclusions: Hospice, ESRD, pregnancy
Numerator: Members whose most recent HbA1c > 9% OR no HbA1c test during measurement year
"""

import pandas as pd

from engine.data_loader import LoadedData
from engine.measures.base import BaseMeasure
from engine.provenance import DataReference, MemberDetail


class HbA1cPoorControl(BaseMeasure):
    measure_id = "NQF-0059"
    measure_name = "Diabetes: HbA1c Poor Control"
    measure_description = (
        "Percentage of patients 18-75 with diabetes whose most recent HbA1c > 9% "
        "or who had no HbA1c test. This is an INVERSE measure — lower is better."
    )
    data_sources_used = ["claims_professional.csv", "clinical_labs.csv"]
    is_inverse = True

    HBA1C_LOINC = "4548-4"
    DIABETES_PREFIX = "E11"
    HOSPICE_CODES = {"Z51.5"}
    PREGNANCY_PREFIXES = ("O09", "Z33")

    def identify_denominator(self, data, attributed_members, members_df):
        """Members age 18-75 with diabetes diagnosis (vectorized)."""
        claims = data.claims_professional
        perf_year_end = pd.Timestamp("2025-12-31")
        attributed_set = set(attributed_members)

        # Age filter
        eligible_members = members_df[members_df["member_id"].isin(attributed_set)].copy()
        eligible_members = eligible_members[eligible_members["date_of_birth"].notna()]
        eligible_members["age"] = ((perf_year_end - eligible_members["date_of_birth"]).dt.days // 365)
        eligible_members = eligible_members[(eligible_members["age"] >= 18) & (eligible_members["age"] <= 75)]

        # Find members with diabetes dx in claims (vectorized)
        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        member_claims = claims[claims["member_id"].isin(eligible_members["member_id"])]
        diabetes_mask = pd.Series(False, index=member_claims.index)
        for col in dx_cols:
            if col in member_claims.columns:
                diabetes_mask |= member_claims[col].str.startswith(self.DIABETES_PREFIX, na=False)
        diabetes_members = set(member_claims.loc[diabetes_mask, "member_id"].unique())

        results = []
        for _, member in eligible_members.iterrows():
            mid = member["member_id"]
            if mid not in diabetes_members:
                continue
            age = int(member["age"])
            results.append(MemberDetail(
                member_id=mid,
                outcome="in_denominator",
                reason=f"Age {age}, diabetes diagnosis found",
                data_references=[DataReference(
                    source_file="claims_professional.csv",
                    row_indices=[],
                    columns_used=["diagnosis_code_1"],
                    description="Diabetes (E11.x) found in claims",
                )],
                intermediate_values={"age": age},
            ))
        return results

    def apply_exclusions(self, denominator_members, data):
        """Exclude hospice, pregnancy (vectorized check)."""
        claims = data.claims_professional
        member_ids = [m.member_id for m in denominator_members]
        member_claims = claims[claims["member_id"].isin(member_ids)]

        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        excluded_members = set()
        for col in dx_cols:
            if col not in member_claims.columns:
                continue
            hospice = member_claims[member_claims[col].isin(self.HOSPICE_CODES)]
            excluded_members.update(hospice["member_id"].unique())
            for prefix in self.PREGNANCY_PREFIXES:
                preg = member_claims[member_claims[col].str.startswith(prefix, na=False)]
                excluded_members.update(preg["member_id"].unique())

        eligible = []
        excluded = []
        for member in denominator_members:
            if member.member_id in excluded_members:
                member.reason = "Excluded: hospice or pregnancy diagnosis"
                excluded.append(member)
            else:
                eligible.append(member)
        return eligible, excluded

    def evaluate_numerator(self, eligible_members, data):
        """Members with most recent HbA1c > 9% or no HbA1c test (vectorized)."""
        labs = data.clinical_labs
        member_ids = [m.member_id for m in eligible_members]

        # Get all HbA1c labs for these members
        hba1c_labs = labs[
            (labs["member_id"].isin(member_ids)) &
            (labs["loinc_code"] == self.HBA1C_LOINC)
        ].sort_values(["member_id", "lab_date"], ascending=[True, False])

        # Get most recent per member
        most_recent = hba1c_labs.groupby("member_id").first()

        in_numerator = []
        not_in_numerator = []

        for member in eligible_members:
            mid = member.member_id
            if mid in most_recent.index:
                row = most_recent.loc[mid]
                hba1c_value = row["result_value"]
                member.intermediate_values["hba1c_value"] = float(hba1c_value) if pd.notna(hba1c_value) else None
                member.data_references.append(DataReference(
                    source_file="clinical_labs.csv",
                    row_indices=[],
                    columns_used=["member_id", "loinc_code", "result_value", "lab_date"],
                    description=f"Most recent HbA1c: {hba1c_value}%",
                ))
                if pd.notna(hba1c_value) and float(hba1c_value) > 9.0:
                    member.reason = f"HbA1c {hba1c_value}% > 9% — poor control"
                    member.intermediate_values["poor_control"] = True
                    in_numerator.append(member)
                else:
                    member.reason = f"HbA1c {hba1c_value}% ≤ 9% — adequate control"
                    member.intermediate_values["poor_control"] = False
                    not_in_numerator.append(member)
            else:
                member.reason = "No HbA1c test found — counted as poor control"
                member.intermediate_values["hba1c_value"] = None
                member.intermediate_values["poor_control"] = True
                in_numerator.append(member)

        return in_numerator, not_in_numerator
