from pathlib import Path
import pandas as pd
import streamlit as st

st.title("Metode")

project_root = Path(__file__).resolve().parents[2]
review_scores_path = project_root / "data" / "processed" / "indicator_review_scores.csv"

df = pd.read_csv(review_scores_path, dtype={"indicator_code": str})


# ---------- Hjælpefunktioner ----------
def normalize_bool(value):
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "ja"}


priority_map = {
    "high": "Høj",
    "medium": "Middel",
    "low": "Lav",
}

if "review_priority" in df.columns:
    df["review_priority_da"] = (
        df["review_priority"].map(priority_map).fillna(df["review_priority"])
    )

if "llm_review_priority" in df.columns:
    df["llm_review_priority_da"] = (
        df["llm_review_priority"].map(priority_map).fillna(df["llm_review_priority"])
    )

if "accessibility_flag" in df.columns:
    df["accessibility_flag_bool"] = df["accessibility_flag"].apply(normalize_bool)

if "extraction_flag" in df.columns:
    df["extraction_flag_bool"] = df["extraction_flag"].apply(normalize_bool)


# ---------- Kort ledelsesoverblik ----------
st.markdown(
    """
Denne side beskriver, hvordan prototypen går fra dokument og tekstudtræk til en samlet prioritering af,
hvilke indikatorrækker der bør gennemgås manuelt. Metoden er udviklet som et **screeningsværktøj** og
skal forstås som beslutningsstøtte, ikke som en juridisk compliance-vurdering.
"""
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Analyserede rækker", len(df))
col2.metric(
    "Høj prioritet",
    int((df["review_priority_da"] == "Høj").sum()) if "review_priority_da" in df.columns else 0,
)
col3.metric(
    "Tilgængelighedsflag",
    int(df["accessibility_flag_bool"].sum()) if "accessibility_flag_bool" in df.columns else 0,
)
col4.metric(
    "Teknisk usikkerhed",
    int(df["extraction_flag_bool"].sum()) if "extraction_flag_bool" in df.columns else 0,
)


# ---------- Procesflow ----------
st.markdown("## Procesoverblik")
st.caption(
    "Flowet nedenfor viser processen på et overordnet niveau: først identificeres indikatorrækker i dokumenterne, "
    "derefter vurderes de med både regelbaserede checks og en LLM, hvorefter de samles i en endelig reviewprioritet."
)

flowchart = """
digraph G {
    rankdir=LR;
    splines=ortho;
    nodesep=0.5;
    ranksep=0.75;

    node [shape=box, style="rounded,filled", fillcolor="#F8F9FA", color="#CED4DA", fontname="Helvetica", fontsize=11];
    edge [color="#6C757D", arrowsize=0.7];

    a [label="1. Dokumentmetadata\\nog PDF-kilder"];
    b [label="2. Side- og\\ntekstekstraktion"];
    c [label="3. Matchning af\\nudvalgte PAI-indikatorer"];
    d [label="4. Regelbaserede\\nstøttechecks"];
    e [label="5. LLM's vurdering\\naf risiko"];
    f [label="6. Samlet\\nreviewprioritet"];
    g [label="7. Dashboard og\\nmanuel gennemgang"];

    a -> b -> c;
    c -> d;
    c -> e;
    d -> f;
    e -> f;
    f -> g;
}
"""
st.graphviz_chart(flowchart, use_container_width=True)


# ---------- Hovedprincipper ----------
st.markdown("## Hovedprincipper for klassifikation")

princip_col1, princip_col2 = st.columns(2)

with princip_col1:
    st.markdown(
        """
### 1. LLM-first
Den samlede prioritering tager udgangspunkt i **LLM's vurdering af risiko**.  
Regelbaserede checks fungerer som støtte- og kontrolag.

### 2. Ikke alt skal eskalere
Enkeltstående tekniske eller tilgængelighedsrelaterede forhold skal som udgangspunkt **ikke alene**
føre til høj prioritet.

### 3. Fokus på reviewbehov
Modellen søger at identificere rækker, hvor der er størst sandsynlighed for, at en manuel gennemgang
er relevant.
"""
    )

with princip_col2:
    st.markdown(
        """
### 4. Tre risikodimensioner
Metoden søger at skelne mellem:
- **Disclosure-risiko**
- **Tilgængelighedsrisiko**
- **Teknisk usikkerhed**

### 5. Institutionsniveau
På dashboardsiden kan rækkeniveauet efterfølgende aggregeres, så institutioner med størst samlet
reviewbehov fremhæves.

### 6. Ingen juridisk konklusion
Screeningen er ikke en afgørelse af, om en erklæring opfylder lovkrav. Den er et prioriteringsværktøj.
"""
    )


# ---------- Uddybende metode ----------
st.markdown("## Uddybende metodebeskrivelse")

st.markdown(
    """
### 1. Datagrundlag og pipeline
Pipeline består overordnet af følgende trin:

1. indlæsning af dokumentmetadata  
2. sideekstraktion fra PDF-dokumenter  
3. identifikation af relevante sektioner  
4. matchning af udvalgte PAI-indikatorer  
5. regelbaserede tekstflag  
6. LLM-baseret vurdering af disclosure-kvalitet  
7. samlet prioritering af reviewbehov  

### 2. LLM's vurdering af risiko
For hver indikatorrække foretager LLM'en en struktureret vurdering af blandt andet følgende forhold:

- om der fremgår **konkrete handlinger**
- om der fremgår **planlagte handlinger**
- om der fremgår **mål**
- om eventuelle mål fremstår **tilstrækkeligt målbare**
- om der er **tydelig kobling mellem indikator og tiltag**
- om teksten i væsentligt omfang hviler på **generelle politikhenvisninger**
- om der er forhold vedrørende **datadækning eller metodeusikkerhed**
- en samlet **LLM-vurdering af risiko**: `low`, `medium` eller `high`

LLM'en fungerer som hovedmotor i vurderingen af disclosure-risiko.

### 3. Regelbaserede støttechecks
De regelbaserede checks bruges primært som støtte- og kontrolag. De anvendes navnlig til at identificere:

- svagt tekstmatch (`low_match_score`)
- lav teknisk læsbarhed eller lav ekstraktionsstatus (`text_extraction_status = low`)
- omtale af datadækning og usikkerhed
- omtale af aktivt ejerskab, eksklusioner og planlagte tiltag
- manuel vurdering af click depth

Disse signaler indgår som støtteinformation i den samlede vurdering, men udgør ikke i sig selv den centrale prioriteringslogik.

### 4. Ekstraktionskvalitet
Ekstraktionskvalitet er et teknisk mål for, i hvor høj grad de udvalgte indikatorer kunne identificeres automatisk i dokumentets tekst.

Lav ekstraktionskvalitet kan blandt andet skyldes, at dokumentet er:
- billedbaseret
- scannet
- struktureret på en måde, der begrænser maskinelt tekstudtræk

Ekstraktionskvalitet skal derfor læses som en indikator for **teknisk læsbarhed**, ikke som en direkte vurdering af den materielle kvalitet af indholdet.

### 5. Click depth og tilgængelighed
Click depth registreres manuelt og anvendes som indikator for, hvor let erklæringen er tilgængelig fra institutionens hjemmeside:

- `0` = dokumentet er direkte tilgængeligt fra forsiden  
- `1` = dokumentet er tilgængeligt med ét klik fra forsiden  
- `2+` = dokumentet kræver mindst to klik fra forsiden  

I prototypen markeres `click_depth_manual >= 2` som et **tilgængelighedsflag**.

Tilgængelighedsflaget er binært:
- `0` = intet tilgængelighedsflag
- `1` = tilgængelighedsflag til stede

### 6. Teknisk usikkerhed
Teknisk usikkerhed er et binært signal på rækkeniveau. Det aktiveres, hvis:

- ekstraktionsstatus er lav, eller
- tekstmatch vurderes som svagt

På institutionsniveau kan teknisk usikkerhed summeres, så man kan se, for hvor mange indikatorrækker der er usikkerhed knyttet til det automatiske fund.

### 7. Samlet prioritering
Den samlede prioritet fastsættes i flere trin:

#### Udgangspunkt
LLM'ens vurdering af risiko er basis for prioriteringen:

- `low` → lav prioritet  
- `medium` → middel prioritet  
- `high` → høj prioritet  

#### Eskalation
En række kan løftes til høj prioritet, hvis der samtidig foreligger tydelige svagheder i disclosure-beskrivelsen, for eksempel:

- indikatoren synes ikke aktuelt at blive taget i betragtning
- der fremgår hverken tydelige handlinger, planlagte handlinger eller en klar kobling mellem indikator og tiltag
- for klimaindikatorer (`1.1`, `1.2`, `1.4`) fremgår der ikke klare og målbare mål, samtidig med at teksten i væsentligt omfang hviler på generelle politikhenvisninger

#### Tilgængelighedsflag
Tilgængelighedsflaget er et støttesignal. Det skal normalt ikke alene føre til høj prioritet, men kan løfte en række fra lav til middel.

#### Teknisk usikkerhed
Teknisk usikkerhed fungerer tilsvarende som et støttesignal. Det skal normalt heller ikke alene føre til høj prioritet, men kan løfte en række fra lav til middel og indgå som supplerende forhold i den samlede vurdering.

### 8. Fortolkning
Den samlede prioritet skal læses således:

- **Høj**: forholdet bør prioriteres til manuel gennemgang  
- **Middel**: forholdet vurderes relevant at gennemgå nærmere  
- **Lav**: der er ikke identificeret tydelige væsentlige problemer i den konkrete række

### 9. Forbehold
Prototypen foretager ikke en juridisk vurdering af, om en erklæring opfylder gældende regler.

Metoden er udviklet som et screeningsværktøj, der skal understøtte:
- risikobaseret prioritering
- hurtigere identificering af indikatorafsnit med potentielle svagheder
- mere målrettet manuel gennemgang
"""
)


# ---------- Beslutningslogik i kort form ----------
st.markdown("## Beslutningslogik i kort form")
st.caption("Nedenfor er logikken gengivet i forenklet form, så man hurtigt kan se, hvordan den samlede prioritet fastsættes.")

st.code(
    """1. Fastlæg basis ud fra LLM's vurdering af risiko:
   low -> lav
   medium -> middel
   high -> høj

2. Undersøg alvorlige disclosure-forhold:
   - indikatoren tages ikke aktuelt i betragtning
   - ingen tydelige handlinger, ingen planlagte handlinger og svag kobling til indikatoren
   - for 1.1, 1.2 og 1.4: ingen tydelige og målbare mål + overvejende generisk policyhenvisning

3. Hvis sådanne alvorlige forhold foreligger:
   -> rækken kan løftes til høj prioritet

4. Undersøg støttesignaler:
   - tilgængelighedsflag (click depth >= 2)
   - teknisk usikkerhed (lav ekstraktionsstatus eller svagt tekstmatch)

5. Støttesignaler kan normalt:
   - løfte en lav række til middel
   - men ikke alene skabe høj prioritet

6. Hvis disclosure i øvrigt fremstår rimelig:
   - små tekniske forhold skal ikke løfte unødigt""",
    language="text",
)


# ---------- Variabeldefinitioner ----------
st.markdown("## Centrale variable og deres betydning")

variable_rows = [
    {
        "Variabel": "llm_review_priority",
        "Niveau": "Række",
        "Betydning": "LLM's vurdering af risiko for den konkrete indikatorrække.",
        "Indgår i prioritering": "Ja, som udgangspunkt",
    },
    {
        "Variabel": "review_priority",
        "Niveau": "Række",
        "Betydning": "Den endelige samlede prioritet efter samspillet mellem LLM og støttechecks.",
        "Indgår i prioritering": "Ja, slutresultat",
    },
    {
        "Variabel": "actions_present",
        "Niveau": "Række",
        "Betydning": "Angiver om der fremgår konkrete handlinger i teksten.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "planned_actions_present",
        "Niveau": "Række",
        "Betydning": "Angiver om der fremgår planlagte handlinger eller fremadrettede tiltag.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "target_present",
        "Niveau": "Række",
        "Betydning": "Angiver om der fremgår et mål for indikatoren.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "target_measurable",
        "Niveau": "Række",
        "Betydning": "Angiver om målet fremstår tilstrækkeligt målbart.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "indicator_action_link_clear",
        "Niveau": "Række",
        "Betydning": "Angiver om der er tydelig kobling mellem indikator og tiltag.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "uses_generic_policy_reference_only",
        "Niveau": "Række",
        "Betydning": "Angiver om teksten i væsentligt omfang hviler på generelle politikhenvisninger frem for konkrete indikatornære oplysninger.",
        "Indgår i prioritering": "Ja",
    },
    {
        "Variabel": "low_data_coverage_flag",
        "Niveau": "Række",
        "Betydning": "Angiver forhold vedrørende datadækning eller metodeusikkerhed.",
        "Indgår i prioritering": "Ja, som støttesignal",
    },
    {
        "Variabel": "accessibility_flag",
        "Niveau": "Række",
        "Betydning": "Binært signal for utilstrækkelig tilgængelighed. Aktiveres ved click depth 2 eller derover.",
        "Indgår i prioritering": "Ja, som støttesignal",
    },
    {
        "Variabel": "extraction_flag",
        "Niveau": "Række",
        "Betydning": "Binært signal for teknisk usikkerhed i det automatiske fund. Aktiveres ved lav ekstraktionsstatus eller svagt tekstmatch.",
        "Indgår i prioritering": "Ja, som støttesignal",
    },
    {
        "Variabel": "review_reason",
        "Niveau": "Række",
        "Betydning": "Tekstlig begrundelse for, hvorfor rækken har fået den pågældende samlede prioritet.",
        "Indgår i prioritering": "Nej, forklarende output",
    },
]

df_variables = pd.DataFrame(variable_rows)

st.dataframe(
    df_variables,
    width="stretch",
    hide_index=True,
)


# ---------- Fortolkningstabel ----------
st.markdown("## Fortolkning af prioritet")

interpretation_df = pd.DataFrame(
    [
        {
            "Prioritet": "Høj",
            "Betydning": "Forholdet bør prioriteres til manuel gennemgang.",
            "Typisk karakteristika": "Betydelige mangler, svag indikatornær beskrivelse eller flere alvorlige forhold.",
        },
        {
            "Prioritet": "Middel",
            "Betydning": "Forholdet vurderes relevant at gennemgå nærmere.",
            "Typisk karakteristika": "Moderate mangler eller kombination af flere støttesignaler.",
        },
        {
            "Prioritet": "Lav",
            "Betydning": "Der er ikke identificeret tydelige væsentlige problemer i den konkrete række.",
            "Typisk karakteristika": "Relativt sammenhængende disclosure og ingen stærke advarselssignaler.",
        },
    ]
)

st.dataframe(
    interpretation_df,
    width="stretch",
    hide_index=True,
)


# ---------- Eksempel på outputdata ----------
st.markdown("## Eksempel på outputdata")
st.caption(
    "Nedenfor vises et udsnit af de centrale outputfelter fra den faktisk genererede scorefil. "
    "Formålet er at gøre metoden operationelt gennemsigtig."
)

columns_to_show = [
    "firm_name",
    "indicator_code",
    "review_priority",
    "llm_review_priority",
    "actions_present",
    "planned_actions_present",
    "target_present",
    "target_measurable",
    "indicator_action_link_clear",
    "uses_generic_policy_reference_only",
    "low_data_coverage_flag",
    "accessibility_flag",
    "extraction_flag",
    "review_reason",
]

existing_cols = [c for c in columns_to_show if c in df.columns]
display_df = df[existing_cols].copy()

rename_map = {
    "firm_name": "Selskab",
    "indicator_code": "Indikator",
    "review_priority": "Samlet prioritet",
    "llm_review_priority": "LLM's vurdering af risiko",
    "actions_present": "Konkrete handlinger",
    "planned_actions_present": "Planlagte handlinger",
    "target_present": "Mål til stede",
    "target_measurable": "Mål er målbart",
    "indicator_action_link_clear": "Tydelig kobling mellem indikator og tiltag",
    "uses_generic_policy_reference_only": "Overvejende generisk policyhenvisning",
    "low_data_coverage_flag": "Datadæknings-/metodeusikkerhed",
    "accessibility_flag": "Tilgængelighedsflag",
    "extraction_flag": "Teknisk usikkerhed",
    "review_reason": "Begrundelse",
}

display_df = display_df.rename(columns=rename_map)

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
)


# ---------- Fordelinger ----------
st.markdown("## Aggregeret fordeling")

dist_col1, dist_col2, dist_col3 = st.columns(3)

with dist_col1:
    st.markdown("### Samlet prioritet")
    if "review_priority_da" in df.columns:
        priority_dist = (
            df["review_priority_da"]
            .value_counts()
            .reindex(["Høj", "Middel", "Lav"], fill_value=0)
            .rename_axis("Prioritet")
            .reset_index(name="Antal")
        )
        st.dataframe(priority_dist, width="stretch", hide_index=True)

with dist_col2:
    st.markdown("### LLM's vurdering af risiko")
    if "llm_review_priority_da" in df.columns:
        llm_dist = (
            df["llm_review_priority_da"]
            .value_counts()
            .reindex(["Høj", "Middel", "Lav"], fill_value=0)
            .rename_axis("Prioritet")
            .reset_index(name="Antal")
        )
        st.dataframe(llm_dist, width="stretch", hide_index=True)

with dist_col3:
    st.markdown("### Støttesignaler")
    support_rows = []
    if "accessibility_flag_bool" in df.columns:
        support_rows.append(
            {
                "Signal": "Tilgængelighedsflag",
                "Antal": int(df["accessibility_flag_bool"].sum()),
            }
        )
    if "extraction_flag_bool" in df.columns:
        support_rows.append(
            {
                "Signal": "Teknisk usikkerhed",
                "Antal": int(df["extraction_flag_bool"].sum()),
            }
        )

    if support_rows:
        st.dataframe(pd.DataFrame(support_rows), width="stretch", hide_index=True)