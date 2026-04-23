from pathlib import Path
import json
import re
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = PROJECT_ROOT / "data" / "interim" / "pages.jsonl"
SECTIONS_PATH = PROJECT_ROOT / "data" / "interim" / "sections.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "indicator_rows.jsonl"
DEBUG_OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "indicator_hits_debug.jsonl"
QUALITY_OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "statement_extraction_quality.jsonl"


TARGET_INDICATORS = {
    "1.1": {
        "label": "GHG emissions",
        "code_patterns": [
            r"\b1\.\s*drivhusgas",
            r"\b1\.\s*ghg emissions",
            r"\bghg emissions\s*\(1\.1\)",
        ],
        "name_patterns": [
            r"drivhusgas[- ]?emissioner",
            r"\bghg emissions\b",
        ],
    },
    "1.2": {
        "label": "Carbon footprint",
        "code_patterns": [
            r"\b2\.\s*co2[- ]?aftryk",
            r"\b2\.\s*carbon footprint",
            r"\bcarbon footprint\s*\(1\.2\)",
        ],
        "name_patterns": [
            r"co2[- ]?aftryk",
            r"\bcarbon footprint\b",
        ],
    },
    "1.4": {
        "label": "Exposure to fossil fuel companies",
        "code_patterns": [
            r"\b4\.\s*eksponering for",
            r"\b4\.\s*exposure to companies active in the fossil fuel sector",
            r"fossil fuel sector\s*\(1\.4\)",
        ],
        "name_patterns": [
            r"aktive i sektoren for fossile brændstoffer",
            r"fossile brændstoffer",
            r"companies active in the fossil fuel sector",
            r"fossil fuel sector",
        ],
    },
    "1.10": {
        "label": "UNGC/OECD violations",
        "code_patterns": [
            r"\b10\.\s*overtrædelser",
            r"\b10\.\s*violations of un global compact principles",
            r"\(1\.10\)",
        ],
        "name_patterns": [
            r"fn'?s global compact",
            r"oecd'?s retningslinjer",
            r"un global compact principles",
            r"oecd guidelines",
            r"\bungc\b",
        ],
    },
    "1.11": {
        "label": "Lack of compliance processes/mechanisms",
        "code_patterns": [
            r"\b11\.\s*mangel på processer",
            r"\b11\.\s*lack of processes and compliance mechanisms",
            r"\(1\.11\)",
        ],
        "name_patterns": [
            r"mangel på processer",
            r"overholdelsesmekanismer",
            r"lack of processes and compliance mechanisms",
            r"monitor compliance",
            r"grievance",
        ],
    },
    "1.14": {
        "label": "Controversial weapons",
        "code_patterns": [
            r"\b14\.\s*eksponering for kontroversielle våben",
            r"\b14\.\s*exposure to controversial weapons",
            r"\(1\.14\)",
        ],
        "name_patterns": [
            r"kontroversielle våben",
            r"controversial weapons",
            r"klyngeammunition",
            r"cluster munitions",
        ],
    },
}


def load_jsonl(path: Path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def group_pages_by_statement(pages: list):
    grouped = defaultdict(list)
    for page in pages:
        grouped[page["statement_id"]].append(page)
    for statement_id in grouped:
        grouped[statement_id] = sorted(grouped[statement_id], key=lambda x: x["page_num"])
    return grouped


def get_description_start_page(sections: list):
    desc_pages = {}
    for row in sections:
        if (
            row["section_name"] == "description_of_principal_adverse_impacts"
            and not row.get("is_toc_page", False)
        ):
            current = desc_pages.get(row["statement_id"])
            if current is None or row["page_num"] < current:
                desc_pages[row["statement_id"]] = row["page_num"]
    return desc_pages


def score_page_for_indicator(text: str, indicator_meta: dict):
    score = 0
    matched = []

    for pattern in indicator_meta["code_patterns"]:
        if re.search(pattern, text):
            score += 3
            matched.append(pattern)

    for pattern in indicator_meta["name_patterns"]:
        if re.search(pattern, text):
            score += 1
            matched.append(pattern)

    return score, matched


def extract_indicator_candidates(
    statement_id: str,
    firm_name: str,
    source_file: str,
    source_url: str,
    click_depth_manual,
    pages_for_statement: list,
    start_page: int,
):
    candidates = []

    for page in pages_for_statement:
        if page["page_num"] < start_page:
            continue

        text = normalize_text(page["text"])

        for indicator_code, meta in TARGET_INDICATORS.items():
            score, matched = score_page_for_indicator(text, meta)

            if score > 0:
                candidates.append(
                    {
                        "statement_id": statement_id,
                        "firm_name": firm_name,
                        "source_file": source_file,
                        "source_url": source_url,
                        "click_depth_manual": click_depth_manual,
                        "indicator_code": indicator_code,
                        "indicator_name": meta["label"],
                        "page_num": page["page_num"],
                        "score": score,
                        "matched_patterns": matched,
                        "raw_indicator_text": page["text"],
                    }
                )

    return candidates


def choose_best_candidates(candidates: list):
    grouped = defaultdict(list)
    for c in candidates:
        key = (c["statement_id"], c["indicator_code"])
        grouped[key].append(c)

    best = []
    for (_, _), hits in grouped.items():
        hits_sorted = sorted(hits, key=lambda x: (-x["score"], x["page_num"]))
        chosen = hits_sorted[0]
        chosen["row_id"] = (
            f"{chosen['statement_id']}_{chosen['indicator_code'].replace('.', '_')}_p{chosen['page_num']}"
        )
        best.append(chosen)

    return sorted(best, key=lambda x: (x["statement_id"], x["page_num"], x["indicator_code"]))


def get_text_extraction_status(num_found: int, num_target: int) -> str:
    if num_found >= 5:
        return "high"
    elif num_found >= 3:
        return "medium"
    else:
        return "low"


def main():
    pages = load_jsonl(PAGES_PATH)
    sections = load_jsonl(SECTIONS_PATH)

    pages_by_statement = group_pages_by_statement(pages)
    desc_start_pages = get_description_start_page(sections)

    all_candidates = []
    all_best = []
    quality_records = []

    print("Building indicator rows...\n")

    total_target_indicators = len(TARGET_INDICATORS)

    for statement_id, pages_for_statement in pages_by_statement.items():
        firm_name = pages_for_statement[0]["firm_name"]
        source_file = pages_for_statement[0]["source_file"]
        source_url = pages_for_statement[0].get("source_url", "")
        click_depth_manual = pages_for_statement[0].get("click_depth_manual")
        start_page = desc_start_pages.get(statement_id, 1)

        candidates = extract_indicator_candidates(
            statement_id=statement_id,
            firm_name=firm_name,
            source_file=source_file,
            source_url=source_url,
            click_depth_manual=click_depth_manual,
            pages_for_statement=pages_for_statement,
            start_page=start_page,
        )

        best = choose_best_candidates(candidates)

        num_found = len(best)
        extraction_status = get_text_extraction_status(
            num_found=num_found,
            num_target=total_target_indicators,
        )

        for row in best:
            row["text_extraction_status"] = extraction_status

        quality_records.append(
            {
                "statement_id": statement_id,
                "firm_name": firm_name,
                "source_file": source_file,
                "source_url": source_url,
                "click_depth_manual": click_depth_manual,
                "target_indicator_count": total_target_indicators,
                "extracted_indicator_count": num_found,
                "text_extraction_status": extraction_status,
            }
        )

        all_candidates.extend(candidates)
        all_best.extend(best)

        found_codes = [b["indicator_code"] for b in best]
        print(
            f"[OK] {statement_id}: found {num_found}/{total_target_indicators} "
            f"indicators -> {found_codes} | status={extraction_status}"
        )

    write_jsonl(DEBUG_OUTPUT_PATH, all_candidates)
    write_jsonl(OUTPUT_PATH, all_best)
    write_jsonl(QUALITY_OUTPUT_PATH, quality_records)

    print("\nDone.")
    print(f"Best indicator rows written: {len(all_best)}")
    print(f"Debug hits written: {len(all_candidates)}")
    print(f"Quality file written: {len(quality_records)}")
    print(f"Output file: {OUTPUT_PATH}")
    print(f"Debug file: {DEBUG_OUTPUT_PATH}")
    print(f"Quality file: {QUALITY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()