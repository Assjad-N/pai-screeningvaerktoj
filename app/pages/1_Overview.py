from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.title("Overblik")

project_root = Path(__file__).resolve().parents[2]

review_queue_path = project_root / "data" / "processed" / "review_queue.csv"
review_scores_path = project_root / "data" / "processed" / "indicator_review_scores.csv"
quality_path = project_root / "data" / "interim" / "statement_extraction_quality.jsonl"

df_queue = pd.read_csv(review_queue_path, dtype={"indicator_code": str})
df_scores = pd.read_csv(review_scores_path, dtype={"indicator_code": str})

quality_records = []
with quality_path.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            quality_records.append(json.loads(line))

df_quality = pd.DataFrame(quality_records)

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

bool_map = {
    True: "Ja",
    False: "Nej",
}

df_queue["review_priority_da"] = (
    df_queue["review_priority"].map(priority_map).fillna(df_queue["review_priority"])
)

df_scores["review_priority_da"] = (
    df_scores["review_priority"].map(priority_map).fillna(df_scores["review_priority"])
)
df_scores["llm_review_priority_da"] = (
    df_scores["llm_review_priority"].map(priority_map).fillna(df_scores["llm_review_priority"])
)
df_scores["Tilgængelighedsflag"] = df_scores["accessibility_flag"].map(bool_map)
df_scores["Teknisk usikkerhed"] = df_scores["extraction_flag"].map(bool_map)

df_quality["text_extraction_status_da"] = (
    df_quality["text_extraction_status"].map(extraction_map).fillna(df_quality["text_extraction_status"])
)

df_quality["Fundne indikatorer"] = (
    df_quality["extracted_indicator_count"].astype(str)
    + "/"
    + df_quality["target_indicator_count"].astype(str)
)


def shorten_text(text, max_len=70):
    if pd.isna(text):
        return ""
    text = str(text)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


# ---------- Hjælpefunktioner til farver ----------
def style_click_depth(val):
    if pd.isna(val):
        return ""
    try:
        val = float(val)
    except Exception:
        return ""
    if val >= 2:
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    return ""


def style_extraction_status(val):
    if val == "Lav":
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    if val == "Middel":
        return "background-color: #fff3cd; color: #664d03;"
    return ""


def style_review_priority(val):
    if val == "Høj":
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    if val == "Middel":
        return "background-color: #fff3cd; color: #664d03;"
    return ""


def style_yes_no_flag(val):
    if val == "Ja":
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    return ""


def style_institution_score(val):
    if pd.isna(val):
        return ""
    try:
        val = float(val)
    except Exception:
        return ""
    if val >= 15:
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    if val >= 10:
        return "background-color: #fff3cd; color: #664d03; font-weight: 600;"
    return ""


def style_institution_high(val):
    if pd.isna(val):
        return ""
    try:
        val = int(val)
    except Exception:
        return ""
    if val >= 2:
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    if val == 1:
        return "background-color: #fff3cd; color: #664d03;"
    return ""


def style_institution_medium(val):
    if pd.isna(val):
        return ""
    try:
        val = int(val)
    except Exception:
        return ""
    if val >= 4:
        return "background-color: #fff3cd; color: #664d03;"
    return ""


def style_institution_flags(val):
    if pd.isna(val):
        return ""
    try:
        val = int(val)
    except Exception:
        return ""
    if val >= 2:
        return "background-color: #f8d7da; color: #842029; font-weight: 600;"
    if val == 1:
        return "background-color: #fff3cd; color: #664d03;"
    return ""


# ---------- Datagrundlag ----------
source_rows = []
for _, row in df_quality.iterrows():
    statement_id = row["statement_id"]
    year = statement_id.split("_")[-1] if "_" in statement_id else ""

    source_rows.append(
        {
            "Selskab": row["firm_name"],
            "År": year,
            "Erklæring": row.get("source_url"),
            "Klikdybde": row.get("click_depth_manual"),
        }
    )

df_sources = pd.DataFrame(source_rows)

df_sources["Klikdybde_sort"] = pd.to_numeric(df_sources["Klikdybde"], errors="coerce")
df_sources = df_sources.sort_values(
    by=["Klikdybde_sort", "Selskab"],
    ascending=[False, True],
    na_position="last",
).drop(columns="Klikdybde_sort")


# ---------- Metrics ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Erklæringer", df_quality["statement_id"].nunique())
col2.metric("Indikatorrækker", len(df_queue))
col3.metric("Højprioritetsrækker", (df_scores["review_priority_da"] == "Høj").sum())
col4.metric("Lav ekstraktionskvalitet", (df_quality["text_extraction_status_da"] == "Lav").sum())

left, right = st.columns([1.35, 1])

with left:
    st.markdown(
        """
<span style="display:inline-flex; align-items:center; gap:8px; margin-bottom:8px;">
    <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#dc3545;"></span>
    <span style="font-size:0.95rem;">Rød markering angiver forhold, der bør prioriteres til manuel gennemgang.</span>
</span>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### Datagrundlag")
    df_sources_styled = df_sources.style.map(
        style_click_depth,
        subset=["Klikdybde"],
    )

    st.dataframe(
        df_sources_styled,
        width="stretch",
        hide_index=True,
        column_config={
            "Selskab": st.column_config.TextColumn("Selskab", width="medium"),
            "År": st.column_config.TextColumn("År", width="small"),
            "Erklæring": st.column_config.LinkColumn(
                "Dokument",
                display_text="PAI-erklæring",
                width="small",
            ),
            "Klikdybde": st.column_config.NumberColumn("Klikdybde", width="small"),
        },
    )

    st.markdown("### Ekstraktionskvalitet")
    st.caption(
        "Ekstraktionskvalitet angiver, i hvor høj grad de udvalgte indikatorer kunne identificeres "
        "automatisk i erklæringens tekst. En lav ekstraktionskvalitet kan blandt andet skyldes, at "
        "PDF-dokumentet er scannet, billedbaseret eller struktureret på en måde, der begrænser maskinelt "
        "tekstudtræk. Målet skal derfor forstås som en teknisk læsbarhedsindikator og ikke som en "
        "vurdering af erklæringens materielle kvalitet."
    )

    df_quality_display = df_quality[
        [
            "firm_name",
            "Fundne indikatorer",
            "extracted_indicator_count",
            "text_extraction_status_da",
        ]
    ].rename(
        columns={
            "firm_name": "Selskab",
            "extracted_indicator_count": "Fundne indikatorer_sort",
            "text_extraction_status_da": "Ekstraktionskvalitet",
        }
    )

    status_order = {"Lav": 0, "Middel": 1, "Høj": 2}
    df_quality_display["status_sort"] = df_quality_display["Ekstraktionskvalitet"].map(status_order)

    df_quality_display = df_quality_display.sort_values(
        by=[
            "status_sort",
            "Fundne indikatorer_sort",
            "Selskab",
        ],
        ascending=[True, True, True],
        na_position="last",
    ).drop(columns=["status_sort", "Fundne indikatorer_sort"])

    df_quality_styled = (
        df_quality_display.style
        .map(style_extraction_status, subset=["Ekstraktionskvalitet"])
    )

    st.dataframe(
        df_quality_styled,
        width="stretch",
        hide_index=True,
        column_config={
            "Selskab": st.column_config.TextColumn("Selskab", width="medium"),
            "Fundne indikatorer": st.column_config.TextColumn("Fundne indikatorer", width="small"),
            "Ekstraktionskvalitet": st.column_config.TextColumn("Ekstraktionskvalitet", width="small"),
        },
    )

with right:
    st.info(
        """
**Formål**

Prototypen skal støtte screening af PAI-erklæringer ved at fremhæve dokumenter og indikatorafsnit med forhøjet reviewbehov.

**Metode**
- LLM-vurderingen er hovedmotoren i prioriteringen og vurderer bl.a., om teksten beskriver konkrete handlinger, planlagte tiltag, mål, målbarhed og tydelig kobling mellem indikator og tiltag.
- Regelbaserede checks bruges som støtte- og kontrolag, ikke som hovedscore. De bruges især til at markere teknisk usikkerhed, svag tekstmatch og tilgængelighedsforhold.
- Klikdybde indgår som tilgængelighedsindikator. En klikdybde på 2 eller mere markeres, fordi erklæringen da ikke fremstår direkte tilgængelig fra forsiden eller under en tydelig, retvisende overskrift.
- Værktøjet skelner dermed mellem disclosure-risiko, ekstraktionsrisiko og tilgængelighedsrisiko.

**Anvendelse**
Værktøjet er ikke en juridisk compliance-vurdering. Formålet er at assistere med at identificere dokumenter og indikatorafsnit, der bør prioriteres til manuel gennemgang.
        """
    )


# ---------- Institutionsoverblik ----------
st.markdown("### Reviewprioritet pr. institution")
st.caption(
    "Tabellen opsummerer den samlede screeningsvurdering pr. institution. "
    "Institutioner med højest samlet reviewscore og flest alvorlige fund står øverst."
)
st.caption(
    "Teknisk usikkerhed angiver antal indikatorrækker, hvor det automatiske fund er vurderet som mindre robust, "
    "typisk på grund af lav dokumentlæsbarhed eller svagt tekstmatch. Et tal på 2 betyder således, at der er "
    "teknisk usikkerhed forbundet med to af de analyserede indikatorrækker."
)

score_map = {
    "Høj": 5,
    "Middel": 2,
    "Lav": 0,
}

df_scores["priority_score"] = df_scores["review_priority_da"].map(score_map)

institution_summary = (
    df_scores.groupby("firm_name", as_index=False)
    .agg(
        samlet_reviewscore=("priority_score", "sum"),
        høj=("review_priority_da", lambda x: (x == "Høj").sum()),
        middel=("review_priority_da", lambda x: (x == "Middel").sum()),
        lav=("review_priority_da", lambda x: (x == "Lav").sum()),
        tilgængelighedsflag=("accessibility_flag", "max"),
        teknisk_usikkerhed=("extraction_flag", "sum"),
        indikatorrækker=("review_priority_da", "count"),
    )
    .sort_values(
        by=["samlet_reviewscore", "høj", "middel", "tilgængelighedsflag", "teknisk_usikkerhed", "firm_name"],
        ascending=[False, False, False, False, False, True],
    )
    .rename(
        columns={
            "firm_name": "Selskab",
            "samlet_reviewscore": "Samlet reviewscore",
            "høj": "Høj",
            "middel": "Middel",
            "lav": "Lav",
            "tilgængelighedsflag": "Tilgængelighedsflag",
            "teknisk_usikkerhed": "Teknisk usikkerhed",
            "indikatorrækker": "Indikatorrækker",
        }
    )
)


def classify_primary_reason(row):
    if row["Høj"] >= 1:
        return "Disclosure"
    if row["Tilgængelighedsflag"] >= 1 and row["Teknisk usikkerhed"] >= 2:
        return "Blandet"
    if row["Tilgængelighedsflag"] >= 1:
        return "Tilgængelighed"
    if row["Teknisk usikkerhed"] >= 2:
        return "Teknisk usikkerhed"
    return "Blandet"


institution_summary["Primær årsag"] = institution_summary.apply(classify_primary_reason, axis=1)

top_3 = institution_summary.head(3)["Selskab"].tolist()
if top_3:
    st.markdown("**Hurtig prioritering:** " + " → ".join(top_3))

institution_summary = institution_summary[
    [
        "Selskab",
        "Samlet reviewscore",
        "Høj",
        "Middel",
        "Lav",
        "Tilgængelighedsflag",
        "Teknisk usikkerhed",
        "Indikatorrækker",
        "Primær årsag",
    ]
]

institution_summary_styled = (
    institution_summary.style
    .map(style_institution_score, subset=["Samlet reviewscore"])
    .map(style_institution_high, subset=["Høj"])
    .map(style_institution_medium, subset=["Middel"])
    .map(style_institution_flags, subset=["Tilgængelighedsflag", "Teknisk usikkerhed"])
)

st.markdown(
    """
<div style="font-weight:600; margin-bottom:0.35rem;">
    LLM-fund fordelt efter alvorlighed
</div>
<div style="font-size:0.9rem; color:#6c757d; margin-bottom:0.75rem;">
    Høj = betydelige mangler, Middel = moderate mangler, Lav = begrænset reviewbehov
</div>
""",
    unsafe_allow_html=True,
)
st.dataframe(
    institution_summary_styled,
    width="content",
    hide_index=True,
    column_config={
        "Selskab": st.column_config.TextColumn("Selskab", width="medium"),
        "Samlet reviewscore": st.column_config.NumberColumn("Samlet reviewscore", width="content"),
        "Høj": st.column_config.NumberColumn("Høj", width="content"),
        "Middel": st.column_config.NumberColumn("Middel", width="content"),
        "Lav": st.column_config.NumberColumn("Lav", width="content"),
        "Tilgængelighedsflag": st.column_config.NumberColumn("Tilgængelighedsflag", width="content"),
        "Teknisk usikkerhed": st.column_config.NumberColumn("Teknisk usikkerhed", width="content"),
        "Indikatorrækker": st.column_config.NumberColumn("Indikatorrækker", width="content"),
        "Primær årsag": st.column_config.TextColumn("Primær årsag", width="content"),
    },
)


# ---------- Rækker med højest reviewbehov ----------
st.markdown("### Rækker med højest reviewbehov")
st.caption(
    "Nedenfor vises de 5 rækker med højest prioriteret reviewbehov. "
    "Klik for at se den fulde problemtekst, begrundelsen for prioriteringen og link til dokumentet."
)


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


df_top_rows = df_scores[
    [
        "row_id",
        "review_score",
        "firm_name",
        "indicator_code",
        "indicator_name",
        "review_priority_da",
        "llm_review_priority_da",
        "Tilgængelighedsflag",
        "Teknisk usikkerhed",
        "top_issue",
        "review_reason",
        "page_num",
        "click_depth_manual",
        "source_url",
    ]
].rename(
    columns={
        "firm_name": "Selskab",
        "indicator_code": "Indikator",
        "indicator_name": "Indikatornavn",
        "review_priority_da": "Reviewprioritet",
        "llm_review_priority_da": "Disclosure-risiko",
        "top_issue": "Vigtigste problem",
        "review_reason": "Begrundelse",
        "page_num": "Side",
        "click_depth_manual": "Klikdybde",
        "source_url": "Dokument",
    }
)

priority_order = pd.Categorical(
    df_top_rows["Reviewprioritet"],
    categories=["Høj", "Middel", "Lav"],
    ordered=True,
)

df_top_rows = df_top_rows.assign(_sort_priority=priority_order)
df_top_rows["Klikdybde_sort"] = pd.to_numeric(df_top_rows["Klikdybde"], errors="coerce")

df_top_rows = df_top_rows.sort_values(
    by=["_sort_priority", "review_score", "Klikdybde_sort", "Selskab", "Indikator"],
    ascending=[True, False, False, True, True],
    na_position="last",
).drop(columns=["_sort_priority", "Klikdybde_sort"])

df_expanders = df_top_rows.head(5).copy()

for _, row in df_expanders.iterrows():
    expander_title = f"{row['Selskab']} · Reviewprioritet: {row['Reviewprioritet']}"

    with st.expander(expander_title):
        st.markdown(
            f"""
<div style="margin-bottom:0.75rem;">
    <strong>Reviewprioritet:</strong> {render_priority_badge(row["Reviewprioritet"])}
</div>
""",
            unsafe_allow_html=True,
        )

        meta_col1, meta_col2 = st.columns(2)

        with meta_col1:
            st.markdown(f"**Selskab:** {row['Selskab']}")
            st.markdown(f"**Indikatornummer:** {row['Indikator']}")
            st.markdown(f"**Indikatornavn:** {row['Indikatornavn']}")
            st.markdown(f"**Disclosure-risiko:** {row['Disclosure-risiko']}")

        with meta_col2:
            st.markdown(f"**Tilgængelighedsflag:** {row['Tilgængelighedsflag']}")
            st.markdown(f"**Teknisk usikkerhed:** {row['Teknisk usikkerhed']}")
            st.markdown(f"**Klikdybde:** {row['Klikdybde']}")
            if pd.notna(row["Dokument"]) and row["Dokument"] != "":
                st.markdown(
                    f"**Dokument:** [Åbn PAI-erklæring]({row['Dokument']}) (side: {row['Side']})"
                )
        
        st.markdown("**Vigtigste problem**")
        st.write(row["Vigtigste problem"])

        st.markdown("**Begrundelse for prioritering**")
        st.write(row["Begrundelse"])

st.page_link(
    "pages/2_Alle_indikatorvurderinger.py",
    label="Se fuld liste over indikatorvurderinger",
    icon="📄",
)
# ---------- Hyppigste problemtyper ----------
st.markdown("### Hyppigste problemtyper")
top_issues = df_scores["top_issue"].value_counts().head(10)
st.dataframe(
    top_issues.rename_axis("Problemtype").reset_index(name="Antal"),
    width="stretch",
    hide_index=True,
)