from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="PAI-screeningværktøj",
    page_icon="📄",
    layout="wide",
)

st.title("PAI-screeningværktøj")
st.write(
    """
    Prototype til AI-assisteret screening af PAI-erklæringer på virksomhedsniveau.

    Brug siderne i venstremenuen til at:
    - se samlet status for datagrundlag, ekstraktion og review
    - gennemgå alle indikatorvurderinger
    - undersøge enkelte indikatorrækker i detalje
    """
)

st.info(
    """
**Afgrænsning af analysen**

Analysen er gennemført for et udvalgt udsnit af PAI-indikatorer: **1.1, 1.2, 1.4, 1.10, 1.11 og 1.14**.  
Udvælgelsen omfatter centrale klima- og sociale indikatorer og skal forstås som en afgrænset screeningsramme, ikke en fuldstændig gennemgang af alle PAI-indikatorer.
"""
)

project_root = Path(__file__).resolve().parents[1]
quality_path = project_root / "data" / "interim" / "statement_extraction_quality.jsonl"

quality_records = []
with quality_path.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            quality_records.append(json.loads(line))

df_quality = pd.DataFrame(quality_records)

source_rows = []
for _, row in df_quality.iterrows():
    statement_id = row["statement_id"]
    year = statement_id.split("_")[-1] if "_" in statement_id else ""
    source_rows.append(
        {
            "Selskab": row["firm_name"],
            "År": year,
            "Erklæringsnavn": "PAI-erklæring",
            "URL": row.get("source_url"),
        }
    )

df_sources = pd.DataFrame(source_rows)

st.markdown("### Kilder")
for _, row in df_sources.iterrows():
    if pd.notna(row["URL"]) and row["URL"] != "":
        st.markdown(f"- **{row['Selskab']} ({row['År']})**: [Åbn erklæring]({row['URL']})")