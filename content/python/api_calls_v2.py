import pandas as pd
import requests

API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/functions/postgisftw.wcrp_habitat_connectivity_status_v2/items.json"
STRUCTURE_COUNT_API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/functions/postgisftw.get_structure_count_spp/items.json"
COMBINED_OUTPUT_API_URL = "https://cabd-pro.cwf-fcf.org/bcfishpass/collections/wcrp_bowr_ques_carr.combined_output_table_vw/items.json"


def get_connectivity(watershed_group_code=None, habitat_type=None, species_code=None):
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


def get_metric_value(
    watershed_group_code,
    metric_name,
    habitat_type="ALL",
    species_code=None,
    digits=2,
):
    df = get_connectivity(
        watershed_group_code=watershed_group_code,
        habitat_type=habitat_type,
        species_code=species_code,
    )

    df = df.loc[df["watershed_group_code"] == watershed_group_code]

    metric_row = df.loc[
        df["habitat_connectivity_type"] == metric_name,
        "habitat_connectivity_value",
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


def get_combined_output():
    response = requests.get(COMBINED_OUTPUT_API_URL)
    response.raise_for_status()

    data = response.json()
    rows = [feature.get("properties", {}) for feature in data.get("features", [])]
    return pd.DataFrame(rows)


def count_completed_assessments():
    df = get_combined_output()

    if "assessment_type_completed" not in df.columns:
        raise KeyError("Metric 'assessment_type_completed' was not found.")

    values = df["assessment_type_completed"].fillna("").astype(str).str.strip()
    return int(((values.ne("")) & (values.str.lower().ne("null"))).sum())


def count_assessment_type(assessment_type):
    df = get_combined_output()

    if "assessment_type_completed" not in df.columns:
        raise KeyError("Metric 'assessment_type_completed' was not found.")

    values = df["assessment_type_completed"].fillna("").astype(str).str.strip()
    return int(values.str.lower().eq(assessment_type.strip().lower()).sum())
