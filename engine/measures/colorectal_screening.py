"""Colorectal Cancer Screening (NQF-0034).

Denominator: Attributed members age 45-75
Exclusions: Total colectomy, hospice, colorectal cancer diagnosis
Numerator: Colonoscopy in past 10 years OR FIT/FOBT in past year OR CT colonography in past 5 years
"""

import pandas as pd

from engine.data_loader import LoadedData
from engine.measures.base import BaseMeasure
from engine.provenance import DataReference, MemberDetail


class ColorectalScreening(BaseMeasure):
    measure_id = "NQF-0034"
    measure_name = "Colorectal Cancer Screening"
    measure_description = (
        "Percentage of adults 45-75 who had appropriate screening for "
        "colorectal cancer (colonoscopy, FIT/FOBT, or CT colonography)."
    )
    data_sources_used = ["claims_professional.csv", "clinical_screenings.csv"]
    is_inverse = False

    COLONOSCOPY_CPT = {"45378", "45380", "45381", "45384", "45385", "G0105", "G0121"}
    FIT_FOBT_CPT = {"82270", "82274", "G0328"}
    CT_COLONOGRAPHY_CPT = {"74263"}
    COLECTOMY_CODES = {"Z90.49"}
    CRC_PREFIXES = ("C18", "C19", "C20")
    HOSPICE_CODES = {"Z51.5"}

    def identify_denominator(self, data, attributed_members, members_df):
        perf_year_end = pd.Timestamp("2025-12-31")
        attributed_set = set(attributed_members)

        eligible = members_df[
            (members_df["member_id"].isin(attributed_set)) &
            (members_df["date_of_birth"].notna())
        ].copy()
        eligible["age"] = ((perf_year_end - eligible["date_of_birth"]).dt.days // 365)
        eligible = eligible[(eligible["age"] >= 45) & (eligible["age"] <= 75)]

        return [
            MemberDetail(
                member_id=row["member_id"],
                outcome="in_denominator",
                reason=f"Age {int(row['age'])} (45-75)",
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
        claims = data.claims_professional
        member_ids = [m.member_id for m in denominator_members]
        member_claims = claims[claims["member_id"].isin(member_ids)]

        dx_cols = ["diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3", "diagnosis_code_4"]
        excluded_set = set()
        for col in dx_cols:
            if col not in member_claims.columns:
                continue
            excl = member_claims[member_claims[col].isin(self.COLECTOMY_CODES | self.HOSPICE_CODES)]
            excluded_set.update(excl["member_id"].unique())
            for prefix in self.CRC_PREFIXES:
                crc = member_claims[member_claims[col].str.startswith(prefix, na=False)]
                excluded_set.update(crc["member_id"].unique())

        eligible = []
        excluded = []
        for m in denominator_members:
            if m.member_id in excluded_set:
                m.reason = "Excluded: colectomy, CRC, or hospice"
                excluded.append(m)
            else:
                eligible.append(m)
        return eligible, excluded

    def evaluate_numerator(self, eligible_members, data):
        """Check for colonoscopy (10yr), FIT/FOBT (1yr), or CT colonography (5yr)."""
        screenings = data.clinical_screenings
        claims = data.claims_professional
        perf_year_end = pd.Timestamp("2025-12-31")
        member_ids = [m.member_id for m in eligible_members]

        # EHR colonoscopy (10yr)
        colon_ehr = screenings[
            (screenings["member_id"].isin(member_ids)) &
            (screenings["screening_type"] == "colonoscopy") &
            (screenings["screening_date"] >= perf_year_end - pd.DateOffset(years=10))
        ]
        colon_ehr_set = set(colon_ehr["member_id"].unique())

        # Claims colonoscopy (10yr)
        colon_claims = claims[
            (claims["member_id"].isin(member_ids)) &
            (claims["procedure_code"].isin(self.COLONOSCOPY_CPT)) &
            (claims["service_date"] >= perf_year_end - pd.DateOffset(years=10))
        ]
        colon_claims_set = set(colon_claims["member_id"].unique())

        # FIT/FOBT (1yr)
        fit_claims = claims[
            (claims["member_id"].isin(member_ids)) &
            (claims["procedure_code"].isin(self.FIT_FOBT_CPT)) &
            (claims["service_date"] >= perf_year_end - pd.DateOffset(years=1))
        ]
        fit_set = set(fit_claims["member_id"].unique())

        # CT colonography (5yr)
        ct_claims = claims[
            (claims["member_id"].isin(member_ids)) &
            (claims["procedure_code"].isin(self.CT_COLONOGRAPHY_CPT)) &
            (claims["service_date"] >= perf_year_end - pd.DateOffset(years=5))
        ]
        ct_set = set(ct_claims["member_id"].unique())

        screened = colon_ehr_set | colon_claims_set | fit_set | ct_set

        in_numerator = []
        not_in_numerator = []
        for m in eligible_members:
            if m.member_id in screened:
                m.reason = "Colorectal screening completed"
                m.intermediate_values["screening_found"] = True
                in_numerator.append(m)
            else:
                m.reason = "No qualifying colorectal screening found"
                m.intermediate_values["screening_found"] = False
                not_in_numerator.append(m)
        return in_numerator, not_in_numerator
