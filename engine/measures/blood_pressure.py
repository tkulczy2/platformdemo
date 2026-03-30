"""Controlling High Blood Pressure (NQF-0018).

Denominator: Attributed members age 18-85 with hypertension diagnosis (ICD-10: I10-I15.x)
Exclusions: ESRD, pregnancy, hospice, dialysis, kidney transplant
Numerator: Members with most recent BP reading < 140/90
"""

import pandas as pd

from engine.data_loader import LoadedData
from engine.measures.base import BaseMeasure
from engine.provenance import DataReference, MemberDetail


class BloodPressureControl(BaseMeasure):
    measure_id = "NQF-0018"
    measure_name = "Controlling High Blood Pressure"
    measure_description = (
        "Percentage of patients 18-85 with hypertension whose most recent "
        "blood pressure is adequately controlled (< 140/90 mmHg)."
    )
    data_sources_used = ["claims_professional.csv", "clinical_vitals.csv"]
    is_inverse = False

    HTN_PREFIXES = ("I10", "I11", "I12", "I13", "I14", "I15")
    EXCLUSION_CODES = {"N18.6", "Z51.5", "Z99.2", "Z49.31", "Z49.32", "Z94.0"}
    PREGNANCY_PREFIXES = ("O09", "Z33")

    def identify_denominator(self, data, attributed_members, members_df):
        claims = data.claims_professional
        perf_year_end = pd.Timestamp("2025-12-31")
        attributed_set = set(attributed_members)

        eligible_members = members_df[members_df["member_id"].isin(attributed_set)].copy()
        eligible_members = eligible_members[eligible_members["date_of_birth"].notna()]
        eligible_members["age"] = ((perf_year_end - eligible_members["date_of_birth"]).dt.days // 365)
        eligible_members = eligible_members[(eligible_members["age"] >= 18) & (eligible_members["age"] <= 85)]

        # Vectorized hypertension check
        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        member_claims = claims[claims["member_id"].isin(eligible_members["member_id"])]
        htn_mask = pd.Series(False, index=member_claims.index)
        for col in dx_cols:
            if col in member_claims.columns:
                for prefix in self.HTN_PREFIXES:
                    htn_mask |= member_claims[col].str.startswith(prefix, na=False)
        htn_members = set(member_claims.loc[htn_mask, "member_id"].unique())

        results = []
        for _, member in eligible_members.iterrows():
            mid = member["member_id"]
            if mid not in htn_members:
                continue
            age = int(member["age"])
            results.append(MemberDetail(
                member_id=mid,
                outcome="in_denominator",
                reason=f"Age {age}, hypertension diagnosis found",
                data_references=[DataReference(
                    source_file="claims_professional.csv",
                    row_indices=[],
                    columns_used=["diagnosis_code_1"],
                    description="Hypertension (I10-I15.x) found in claims",
                )],
                intermediate_values={"age": age},
            ))
        return results

    def apply_exclusions(self, denominator_members, data):
        claims = data.claims_professional
        member_ids = [m.member_id for m in denominator_members]
        member_claims = claims[claims["member_id"].isin(member_ids)]

        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        excluded_members = set()
        for col in dx_cols:
            if col not in member_claims.columns:
                continue
            excl = member_claims[member_claims[col].isin(self.EXCLUSION_CODES)]
            excluded_members.update(excl["member_id"].unique())
            for prefix in self.PREGNANCY_PREFIXES:
                preg = member_claims[member_claims[col].str.startswith(prefix, na=False)]
                excluded_members.update(preg["member_id"].unique())

        eligible = []
        excluded = []
        for member in denominator_members:
            if member.member_id in excluded_members:
                member.reason = "Excluded: ESRD, pregnancy, hospice, or dialysis"
                excluded.append(member)
            else:
                eligible.append(member)
        return eligible, excluded

    def evaluate_numerator(self, eligible_members, data):
        """Members with most recent BP < 140/90 (vectorized)."""
        vitals = data.clinical_vitals
        member_ids = [m.member_id for m in eligible_members]

        sys_vitals = vitals[
            (vitals["member_id"].isin(member_ids)) &
            (vitals["vital_type"] == "systolic_bp")
        ].sort_values(["member_id", "vital_date"], ascending=[True, False])
        latest_sys = sys_vitals.groupby("member_id").first()

        dia_vitals = vitals[
            (vitals["member_id"].isin(member_ids)) &
            (vitals["vital_type"] == "diastolic_bp")
        ].sort_values(["member_id", "vital_date"], ascending=[True, False])
        latest_dia = dia_vitals.groupby("member_id").first()

        in_numerator = []
        not_in_numerator = []

        for member in eligible_members:
            mid = member.member_id
            if mid not in latest_sys.index or mid not in latest_dia.index:
                member.reason = "No BP readings found"
                member.intermediate_values["bp_systolic"] = None
                member.intermediate_values["bp_diastolic"] = None
                not_in_numerator.append(member)
                continue

            systolic = float(latest_sys.loc[mid, "value"])
            diastolic = float(latest_dia.loc[mid, "value"])
            member.intermediate_values["bp_systolic"] = systolic
            member.intermediate_values["bp_diastolic"] = diastolic
            member.data_references.append(DataReference(
                source_file="clinical_vitals.csv",
                row_indices=[],
                columns_used=["member_id", "vital_type", "value", "vital_date"],
                description=f"Most recent BP: {systolic}/{diastolic} mmHg",
            ))

            if systolic < 140 and diastolic < 90:
                member.reason = f"BP {systolic}/{diastolic} < 140/90 — controlled"
                in_numerator.append(member)
            else:
                member.reason = f"BP {systolic}/{diastolic} ≥ 140/90 — uncontrolled"
                not_in_numerator.append(member)

        return in_numerator, not_in_numerator
