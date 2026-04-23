from pathlib import Path
import pandas as pd
import streamlit as st

st.title("Alle indikatorvurderinger")

project_root = Path(__file__).resolve().parents[2]
review_scores_path = project_root / "data" / "processed" / "indicator_review_scores.csv"

df = pd.read_csv(review_scores_path, dtype={"indicator_code": str})

priority_map = {
    "high": "Høj",
    "medium": "Middel",
    "low": "Lav",
}

bool_map = {
    True: "Ja",
    False: "Nej",
}


def normalize_bool(value):
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "ja"}


def render_priority_badge(priority: str) -> str:
    if priority == "Høj":
        bg = "#f8d7da"
        fg = "#842029"
    elif priority == "Middel":
        bg = "#fff3cd"
        fg = "#664d03"
    else:
        bg = "#e2e3e5"
        fg = "#41464b"

    return (
        f"<span style='background:{bg}; color:{fg}; padding:0.2rem 0.5rem; "
        f"border-radius:0.4rem; font-weight:600;'>{priority}</span>"
    )


df["review_priority_da"] = df["review_priority"].map(priority_map).fillna(df["review_priority"])
df["llm_review_priority_da"] = df["llm_review_priority"].map(priority_map).fillna(df["llm_review_priority"])
df["Tilgængelighedsflag"] = df["accessibility_flag"].apply(normalize_bool).map(bool_map)
df["Teknisk usikkerhed"] = df["extraction_flag"].apply(normalize_bool).map(bool_map)

priority_filter = st.multiselect(
    "Filtrér efter reviewprioritet",
    options=["Høj", "Middel", "Lav"],
    default=["Høj", "Middel", "Lav"],
)

firm_filter = st.multiselect(
    "Filtrér efter selskab",
    options=sorted(df["firm_name"].dropna().unique().tolist()),
    default=sorted(df["firm_name"].dropna().unique().tolist()),
)

indicator_filter = st.multiselect(
    "Filtrér efter indikatorkode",
    options=sorted(df["indicator_code"].dropna().unique().tolist()),
    default=sorted(df["indicator_code"].dropna().unique().tolist()),
)

filtered = df[
    df["review_priority_da"].isin(priority_filter)
    & df["firm_name"].isin(firm_filter)
    & df["indicator_code"].isin(indicator_filter)
].copy()

priority_order = pd.Categorical(
    filtered["review_priority_da"],
    categories=["Høj", "Middel", "Lav"],
    ordered=True,
)
filtered = filtered.assign(_priority_sort=priority_order)
filtered["Klikdybde_sort"] = pd.to_numeric(filtered["click_depth_manual"], errors="coerce")

filtered = filtered.sort_values(
    by=["_priority_sort", "review_score", "Klikdybde_sort", "firm_name", "indicator_code"],
    ascending=[True, False, False, True, True],
    na_position="last",
).drop(columns=["_priority_sort", "Klikdybde_sort"])

st.caption(
    "Siden viser alle filtrerede indikatorrækker i prioriteret rækkefølge. "
    "Brug filtrene til at afgrænse visningen, og fold en række ud for at se den fulde begrundelse."
)

st.markdown(f"**Viste rækker:** {len(filtered)}")

for _, row in filtered.iterrows():
    expander_title = (
        f"{row['firm_name']} · Reviewprioritet: {row['review_priority_da']} · "
        f"Indikator {row['indicator_code']}"
    )

    with st.expander(expander_title):
        st.markdown(
            f"""
<div style="margin-bottom:0.75rem;">
    <strong>Reviewprioritet:</strong> {render_priority_badge(row["review_priority_da"])}
</div>
""",
            unsafe_allow_html=True,
        )

        meta_col1, meta_col2 = st.columns(2)

        with meta_col1:
            st.markdown(f"**Selskab:** {row['firm_name']}")
            st.markdown(f"**Indikatornummer:** {row['indicator_code']}")
            st.markdown(f"**Indikatornavn:** {row['indicator_name']}")
            st.markdown(f"**Disclosure-risiko:** {row['llm_review_priority_da']}")

        with meta_col2:
            st.markdown(f"**Tilgængelighedsflag:** {row['Tilgængelighedsflag']}")
            st.markdown(f"**Teknisk usikkerhed:** {row['Teknisk usikkerhed']}")
            st.markdown(f"**Klikdybde:** {row['click_depth_manual']}")
            if pd.notna(row.get("source_url")) and row.get("source_url") != "":
                st.markdown(
                    f"**Dokument:** [Åbn PAI-erklæring]({row['source_url']}) (side: {row['page_num']})"
                )

        st.markdown("**Vigtigste problem**")
        st.write(row["top_issue"])

        st.markdown("**Begrundelse for prioritering**")
        st.write(row["review_reason"])