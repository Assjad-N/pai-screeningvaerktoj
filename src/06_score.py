from pathlib import Path
import json
import csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULES_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_flags.jsonl"
LLM_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_llm_review.jsonl"
JSONL_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_review_scores.jsonl"
CSV_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_review_scores.csv"

CSV_COLUMNS = [
    "row_id",
    "statement_id",
    "firm_name",
    "source_file",
    "source_url",
    "click_depth_manual",
    "indicator_code",
    "indicator_name",
    "page_num",
    "score",
    "text_extraction_status",
    "mentions_engagement",
    "mentions_exclusion",
    "mentions_target_year",
    "mentions_percentage_target",
    "mentions_planned_actions",
    "mentions_no_current_consideration",
    "mentions_data_coverage",
    "low_match_score",
    "rule_flag_count",
    "actions_present",
    "planned_actions_present",
    "target_present",
    "target_measurable",
    "indicator_action_link_clear",
    "uses_generic_policy_reference_only",
    "low_data_coverage_flag",
    "llm_review_priority",
    "top_issue",
    "confidence",
    "accessibility_flag",
    "extraction_flag",
    "review_score",
    "review_priority",
    "review_reason",
]


def load_jsonl(path: Path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, records: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col) for col in CSV_COLUMNS})


def index_by_row_id(records: list):
    return {record["row_id"]: record for record in records}


def llm_priority_to_base_score(priority: str) -> int:
    mapping = {
        "low": 1,
        "medium": 2,
        "high": 3,
    }
    return mapping.get(priority, 2)


def score_to_priority(score: int) -> str:
    if score >= 3:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def compute_accessibility_flag(rule_row: dict) -> bool:
    click_depth = rule_row.get("click_depth_manual")
    if click_depth is None:
        return False
    try:
        return float(click_depth) >= 2
    except Exception:
        return False


def compute_extraction_flag(rule_row: dict) -> bool:
    if rule_row.get("text_extraction_status") == "low":
        return True
    if rule_row.get("low_match_score"):
        return True
    return False


def indicator_requires_quant_target(indicator_code: str) -> bool:
    return indicator_code in {"1.1", "1.2", "1.4"}


def priority_da(priority: str) -> str:
    mapping = {
        "low": "Lav",
        "medium": "Middel",
        "high": "Høj",
    }
    return mapping.get(priority, "Ukendt")


def build_review_reason(
    rule_row: dict,
    llm_row: dict,
    accessibility_flag: bool,
    extraction_flag: bool,
    final_priority: str,
) -> str:
    reasons = []

    llm_priority = llm_row.get("review_priority", "unknown")
    reasons.append(f"LLM’s vurdering af risiko: {priority_da(llm_priority)}")

    if accessibility_flag:
        reasons.append(
            "erklæringen fremstår ikke umiddelbart let tilgængelig, idet klikdybden er 2 eller derover"
        )

    if extraction_flag:
        reasons.append(
            "der er identificeret teknisk usikkerhed i det automatiske fund, eksempelvis som følge af lav dokumentlæsbarhed eller svagt tekstmatch"
        )

    if rule_row.get("mentions_no_current_consideration"):
        reasons.append(
            "teksten indikerer, at indikatoren ikke aktuelt indgår i investeringsbeslutningen"
        )

    if not llm_row.get("actions_present"):
        reasons.append(
            "der fremgår ikke en tilstrækkelig klar beskrivelse af konkrete foranstaltninger"
        )

    if not llm_row.get("planned_actions_present"):
        reasons.append(
            "der fremgår ikke en tilstrækkelig klar beskrivelse af planlagte foranstaltninger"
        )

    if not llm_row.get("target_present"):
        reasons.append(
            "der fremgår ikke et klart formuleret mål for indikatoren"
        )

    if not llm_row.get("target_measurable"):
        reasons.append(
            "eventuelle mål fremstår ikke tilstrækkeligt målbare"
        )

    if not llm_row.get("indicator_action_link_clear"):
        reasons.append(
            "sammenhængen mellem indikator og beskrevne foranstaltninger fremstår ikke tilstrækkelig tydelig"
        )

    if llm_row.get("uses_generic_policy_reference_only"):
        reasons.append(
            "beskrivelsen hviler i væsentligt omfang på generelle politikhenvisninger frem for indikatornære oplysninger"
        )

    if llm_row.get("low_data_coverage_flag"):
        reasons.append(
            "der er forhold vedrørende datadækning eller metodeusikkerhed, som kan begrænse vurderingsgrundlaget"
        )

    if final_priority == "high":
        reasons.append(
            "forholdet bør prioriteres til manuel gennemgang"
        )

    return "; ".join(reasons)


def derive_priority(rule_row: dict, llm_row: dict):
    indicator_code = rule_row.get("indicator_code")
    llm_base = llm_priority_to_base_score(llm_row.get("review_priority", "medium"))

    accessibility_flag = compute_accessibility_flag(rule_row)
    extraction_flag = compute_extraction_flag(rule_row)

    severe_disclosure_issue = (
        rule_row.get("mentions_no_current_consideration")
        or (
            not llm_row.get("actions_present")
            and not llm_row.get("planned_actions_present")
            and not llm_row.get("indicator_action_link_clear")
        )
    )

    weak_climate_disclosure = (
        indicator_requires_quant_target(indicator_code)
        and not llm_row.get("target_present")
        and not llm_row.get("target_measurable")
        and llm_row.get("uses_generic_policy_reference_only")
    )

    supporting_concerns = sum(
        [
            bool(extraction_flag),
            bool(llm_row.get("low_data_coverage_flag")),
            bool(llm_row.get("uses_generic_policy_reference_only")),
            not bool(llm_row.get("target_present")),
            not bool(llm_row.get("target_measurable")),
        ]
    )

    final_score = llm_base

    if severe_disclosure_issue or weak_climate_disclosure:
        final_score = max(final_score, 3)

    if accessibility_flag and final_score == 1:
        final_score = 2

    if extraction_flag and final_score == 1:
        final_score = 2

    if (
        final_score == 2
        and (severe_disclosure_issue or weak_climate_disclosure)
        and supporting_concerns >= 3
    ):
        final_score = 3

    if (
        llm_base == 2
        and llm_row.get("actions_present")
        and llm_row.get("indicator_action_link_clear")
        and (
            llm_row.get("target_present")
            or not indicator_requires_quant_target(indicator_code)
        )
        and not rule_row.get("mentions_no_current_consideration")
        and not severe_disclosure_issue
        and not weak_climate_disclosure
    ):
        final_score = min(final_score, 2)

    final_priority = score_to_priority(final_score)

    return final_score, final_priority, accessibility_flag, extraction_flag


def main():
    rule_rows = load_jsonl(RULES_INPUT_PATH)
    llm_rows = load_jsonl(LLM_INPUT_PATH)

    llm_index = index_by_row_id(llm_rows)

    merged_rows = []

    for rule_row in rule_rows:
        row_id = rule_row["row_id"]
        llm_row = llm_index.get(row_id)

        if not llm_row:
            continue

        review_score, review_priority, accessibility_flag, extraction_flag = derive_priority(
            rule_row, llm_row
        )

        review_reason = build_review_reason(
            rule_row=rule_row,
            llm_row=llm_row,
            accessibility_flag=accessibility_flag,
            extraction_flag=extraction_flag,
            final_priority=review_priority,
        )

        merged_row = {
            "row_id": rule_row["row_id"],
            "statement_id": rule_row["statement_id"],
            "firm_name": rule_row["firm_name"],
            "source_file": rule_row.get("source_file"),
            "source_url": rule_row.get("source_url"),
            "click_depth_manual": rule_row.get("click_depth_manual"),
            "indicator_code": rule_row["indicator_code"],
            "indicator_name": rule_row["indicator_name"],
            "page_num": rule_row["page_num"],
            "score": rule_row.get("score"),
            "text_extraction_status": rule_row.get("text_extraction_status"),
            "mentions_engagement": rule_row.get("mentions_engagement"),
            "mentions_exclusion": rule_row.get("mentions_exclusion"),
            "mentions_target_year": rule_row.get("mentions_target_year"),
            "mentions_percentage_target": rule_row.get("mentions_percentage_target"),
            "mentions_planned_actions": rule_row.get("mentions_planned_actions"),
            "mentions_no_current_consideration": rule_row.get("mentions_no_current_consideration"),
            "mentions_data_coverage": rule_row.get("mentions_data_coverage"),
            "low_match_score": rule_row.get("low_match_score"),
            "rule_flag_count": rule_row.get("rule_flag_count"),
            "actions_present": llm_row.get("actions_present"),
            "planned_actions_present": llm_row.get("planned_actions_present"),
            "target_present": llm_row.get("target_present"),
            "target_measurable": llm_row.get("target_measurable"),
            "indicator_action_link_clear": llm_row.get("indicator_action_link_clear"),
            "uses_generic_policy_reference_only": llm_row.get("uses_generic_policy_reference_only"),
            "low_data_coverage_flag": llm_row.get("low_data_coverage_flag"),
            "llm_review_priority": llm_row.get("review_priority"),
            "top_issue": llm_row.get("top_issue"),
            "confidence": llm_row.get("confidence"),
            "accessibility_flag": accessibility_flag,
            "extraction_flag": extraction_flag,
            "review_score": review_score,
            "review_priority": review_priority,
            "review_reason": review_reason,
        }

        merged_rows.append(merged_row)

    write_jsonl(JSONL_OUTPUT_PATH, merged_rows)
    write_csv(CSV_OUTPUT_PATH, merged_rows)

    print("Done.")
    print(f"Merged rows: {len(merged_rows)}")
    print(f"Scored rows written: {len(merged_rows)}")
    print(f"JSONL output: {JSONL_OUTPUT_PATH}")
    print(f"CSV output: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()