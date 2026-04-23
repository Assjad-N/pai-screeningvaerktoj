from pathlib import Path
import pandas as pd
import streamlit as st

st.title("Indikatordetaljer")

project_root = Path(__file__).resolve().parents[2]
scores_path = project_root / "data" / "processed" / "indicator_review_scores.csv"

df_scores = pd.read_csv(scores_path, dtype={"indicator_code": str})

priority_map = {
    "high": "Høj",
    "medium": "Middel",
    "low": "Lav",
}

extraction_map = {
    "high": "Høj",
    "medium": "Middel",
    "low": "Lav",
}

confidence_map = {
    "high": "Høj",
    "medium": "Middel",
    "low": "Lav",
}


def indicator_sort_key(code: str):
    parts = str(code).split(".")
    return tuple(int(p) if p.isdigit() else 999 for p in parts)


# ---------- Selector 1: institution ----------
institutions = sorted(df_scores["firm_name"].dropna().unique().tolist())

selected_institution = st.selectbox(
    "Vælg institution",
    options=institutions,
)

df_institution = df_scores[df_scores["firm_name"] == selected_institution].copy()

# ---------- Selector 2: indikator ----------
df_institution["indicator_sort_key"] = df_institution["indicator_code"].apply(indicator_sort_key)

df_institution = df_institution.sort_values(
    by=["indicator_sort_key", "page_num"]
)

df_institution["indicator_label"] = (
    df_institution["indicator_code"].astype(str)
    + " · "
    + df_institution["indicator_name"].astype(str)
)

indicator_options = df_institution["indicator_label"].tolist()

selected_indicator_label = st.selectbox(
    "Vælg indikator",
    options=indicator_options,
)

selected = df_institution[df_institution["indicator_label"] == selected_indicator_label].iloc[0]

review_priority_da = priority_map.get(selected["review_priority"], selected["review_priority"])
llm_priority_da = priority_map.get(selected["llm_review_priority"], selected["llm_review_priority"])
extraction_status_da = extraction_map.get(
    selected["text_extraction_status"],
    selected["text_extraction_status"],
)
confidence_da = confidence_map.get(selected["confidence"], selected["confidence"])

st.markdown("### Metadata")
st.write({
    "Selskab": selected["firm_name"],
    "Indikatorkode": selected["indicator_code"],
    "Indikatornavn": selected["indicator_name"],
    "Side": int(selected["page_num"]),
    "Samlet reviewprioritet": review_priority_da,
    "LLM's vurdering af risiko": llm_priority_da,
    "Reviewscore": int(selected["review_score"]),
    "Hovedproblem": selected["top_issue"],
    "LLM-vurderingssikkerhed": confidence_da,
    "Ekstraktionsstatus": extraction_status_da,
    "Klikdybde": int(selected["click_depth_manual"]) if pd.notna(selected["click_depth_manual"]) else None,
})

st.markdown("### Begrundelse for review")
st.write(selected["review_reason"])

st.markdown("### LLM- og regelbaserede features")

feature_cols = [
    "mentions_engagement",
    "mentions_exclusion",
    "mentions_target_year",
    "mentions_percentage_target",
    "mentions_planned_actions",
    "mentions_no_current_consideration",
    "mentions_data_coverage",
    "low_match_score",
    "actions_present",
    "planned_actions_present",
    "target_present",
    "target_measurable",
    "indicator_action_link_clear",
    "uses_generic_policy_reference_only",
    "low_data_coverage_flag",
]

feature_names = {
    "mentions_engagement": "Omtaler aktivt ejerskab/dialog",
    "mentions_exclusion": "Omtaler eksklusion",
    "mentions_target_year": "Omtaler målår",
    "mentions_percentage_target": "Omtaler procentmål",
    "mentions_planned_actions": "Omtaler planlagte tiltag",
    "mentions_no_current_consideration": "Omtaler at påvirkning ikke aktuelt indgår",
    "mentions_data_coverage": "Omtaler datadækning/metode",
    "low_match_score": "Lav matchscore",
    "actions_present": "Konkret handling beskrevet",
    "planned_actions_present": "Planlagt handling beskrevet",
    "target_present": "Mål beskrevet",
    "target_measurable": "Mål er målbart",
    "indicator_action_link_clear": "Tydelig kobling mellem indikator og handling",
    "uses_generic_policy_reference_only": "Primært generisk politiktekst",
    "low_data_coverage_flag": "LLM flagger datadækningsproblem",
}

feature_df = pd.DataFrame({
    "Feature": [feature_names[col] for col in feature_cols],
    "Værdi": [selected[col] for col in feature_cols],
})

st.dataframe(feature_df, width="stretch", hide_index=True)

if "source_url" in selected.index and pd.notna(selected["source_url"]) and selected["source_url"] != "":
    st.markdown("### Dokument")
    st.markdown(
        f"[Åbn erklæring]({selected['source_url']}) (side: {int(selected['page_num'])})"
    )