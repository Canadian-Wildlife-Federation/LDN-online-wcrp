import requests
import pandas as pd

API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/functions/postgisftw.wcrp_habitat_connectivity_status_v2/items.json"
STRUCTURE_COUNT_API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/functions/postgisftw.get_structure_count_spp/items.json"
COMBINED_OUTPUT_API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/collections/wcrp_lnic.combined_output_table_vw/items.json"


def get_connectivity(
    watershed_group_code=None,
    habitat_type=None,
    species_code=None
):
    params = {}

    if watershed_group_code:
        params["watershed_group_code"] = watershed_group_code

    if habitat_type:
        params["habitat_type"] = habitat_type

    if species_code:
        params["species_code"] = species_code

    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    return pd.DataFrame(data)


def get_value(df, column, row=0, digits=2):
    value = df.loc[row, column]

    if isinstance(value, float):
        return round(value, digits)

    return value


def get_metric_value(
    watershed_group_code,
    metric_name,
    habitat_type="ALL",
    species_code=None,
    digits=2
):
    df = get_connectivity(
        watershed_group_code=watershed_group_code,
        habitat_type=habitat_type,
        species_code=species_code
    )

    df = df.loc[df["watershed_group_code"] == watershed_group_code]

    metric_row = df.loc[
        df["habitat_connectivity_type"] == metric_name,
        "habitat_connectivity_value"
    ]

    if metric_row.empty:
        raise KeyError(
            f"Metric '{metric_name}' was not found for watershed "
            f"'{watershed_group_code}'."
        )

    return round(float(metric_row.iloc[0]), digits)


def get_structure_count(wcrp=None, spp=None):
    params = {}

    if wcrp:
        params["wcrp"] = wcrp

    if spp:
        params["spp"] = spp

    response = requests.get(STRUCTURE_COUNT_API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    return pd.DataFrame(data)


def get_structure_count_value(wcrp, spp, metric_name):
    df = get_structure_count(wcrp=wcrp, spp=spp)

    if df.empty:
        raise KeyError(
            f"No structure count data was returned for wcrp '{wcrp}' "
            f"and spp '{spp}'."
        )

    if metric_name not in df.columns:
        raise KeyError(
            f"Metric '{metric_name}' was not found for wcrp '{wcrp}' "
            f"and spp '{spp}'."
        )

    return int(df.loc[0, metric_name])


def get_combined_output(structure_list_status=None):
    params = {}

    if structure_list_status:
        params["structure_list_status"] = structure_list_status

    response = requests.get(COMBINED_OUTPUT_API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict) and "features" in data:
        rows = [feature.get("properties", {}) for feature in data["features"]]
    elif isinstance(data, dict) and "items" in data:
        rows = data["items"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    return pd.DataFrame(rows)


def get_priority_barriers_table():
    df = get_combined_output(structure_list_status="Priority barrier").copy()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "barrier_id",
                "internal_name",
                "watershed_group_code",
                "structure_owner",
                "structure_type",
                "partial_passability",
                "partial_passability_notes",
                "num_barriers_set",
                "all_spawningrearing_belowupstrbarriers_km",
                "next_steps",
            ]
        )

    table_df = pd.DataFrame(
        {
            "barrier_id": df["barrier_id"].fillna(""),
            "internal_name": df["internal_name"].fillna(""),
            "watershed_group_code": df["watershed_group_code"].fillna(""),
            "structure_owner": df["structure_owner"].fillna(""),
            "structure_type": df["structure_type"].fillna(""),
            "partial_passability": df["partial_passability"].fillna(""),
            "partial_passability_notes": df["partial_passability_notes"].fillna(""),
            "num_barriers_set": df["all_spawningrearing_num_barriers_set"].fillna(0).astype(int),
            "all_spawningrearing_belowupstrbarriers_km": df["all_spawningrearing_belowupstrbarriers_km"].fillna(0).round(2),
            "next_steps": df["next_steps"].fillna(""),
        }
    )

    return table_df


def build_structure_status_table(structure_list_status, column_map):
    df = get_combined_output(structure_list_status=structure_list_status).copy()

    if df.empty:
        return pd.DataFrame(columns=list(column_map.values()))

    table_df = pd.DataFrame()

    for source_col, target_col in column_map.items():
        if source_col in df.columns:
            table_df[target_col] = df[source_col].fillna("")
        else:
            table_df[target_col] = ""

    return table_df


def get_non_actionable_barriers_table():
    return build_structure_status_table(
        "Non-actionable barrier",
        {
            "barrier_id": "Barrier ID",
            "internal_name": "Site Name",
            "watershed_group_code": "Watershed Name",
            "structure_type": "Structure Type",
            "assessment_type_completed": "Assessment Step Completed",
            "next_steps": "Next Steps",
            "notes": "Notes",
            "supporting_links": "Supporting Links",
        },
    )


def get_data_deficient_barriers_table():
    return build_structure_status_table(
        "Data-deficient barrier",
        {
            "barrier_id": "Barrier ID",
            "internal_name": "Site Name",
            "structure_type": "Structure Type",
            "assessment_type_completed": "Assessment Step Completed",
            "next_steps": "Next Steps",
            "notes": "Notes",
            "supporting_links": "Supporting Links",
        },
    )


def get_excluded_structures_table():
    return build_structure_status_table(
        "Excluded structure",
        {
            "barrier_id": "Barrier ID",
            "internal_name": "Site Name",
            "structure_type": "Structure Type",
            "assessment_type_completed": "Assessment Step Completed",
            "reason_for_exclusion": "Reason for Exclusion",
            "notes": "Notes",
            "supporting_links": "Supporting Links",
        },
    )


def count_completed_assessments():
    df = get_combined_output()

    if "assessment_type_completed" not in df.columns:
        raise KeyError("Metric 'assessment_type_completed' was not found.")

    values = df["assessment_type_completed"]
    return int((
        values.notna()
        & values.astype(str).str.strip().ne("")
        & values.astype(str).str.lower().ne("null")
    ).sum())


def count_assessment_type(assessment_type):
    df = get_combined_output()

    if "assessment_type_completed" not in df.columns:
        raise KeyError("Metric 'assessment_type_completed' was not found.")

    values = df["assessment_type_completed"].fillna("").astype(str).str.strip()
    return int(values.str.lower().eq(assessment_type.strip().lower()).sum())


def count_structure_list_status(structure_list_status):
    df = get_combined_output(structure_list_status=structure_list_status)
    return int(len(df))


def sum_structure_list_status_metric(structure_list_status, metric_name, digits=2):
    df = get_combined_output(structure_list_status=structure_list_status)

    if df.empty:
        return 0

    if metric_name not in df.columns:
        raise KeyError(
            f"Metric '{metric_name}' was not found for structure list "
            f"status '{structure_list_status}'."
        )

    return round(float(df[metric_name].fillna(0).sum()), digits)
