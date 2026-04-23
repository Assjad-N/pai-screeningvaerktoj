from pathlib import Path
import json
import re
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "interim" / "pages.jsonl"
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "sections_raw.jsonl"
BEST_OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "sections.jsonl"


SECTION_PATTERNS = {
    "summary": [
        r"\bsammenfatning\b",
        r"\bsummary\b",
        r"\b1\.\s*summary\b",
    ],
    "description_of_principal_adverse_impacts": [
        r"beskrivelse af de vigtigste negative indvirkninger på bæredygtighedsfaktorer",
        r"description of the principal adverse impacts on sustainability factors",
    ],
    "policies_to_identify_and_prioritise_pai": [
        r"beskrivelse af politikker for identifikation og prioritering af de vigtigste negative indvirkninger",
        r"description of policies to identify and prioritise principal adverse impacts",
        r"description of policies to identify and prioritize principal adverse impacts",
    ],
    "active_ownership": [
        r"politikker for aktivt ejerskab",
        r"\bactive ownership\b",
        r"\bengagement policies\b",
    ],
    "international_standards": [
        r"henvisninger til internationale standarder",
        r"references to international standards",
    ],
    "historical_comparison": [
        r"historisk sammenligning",
        r"historical comparison",
    ],
    "change_log": [
        r"change log",
    ],
    "data_quality_or_methodology": [
        r"dataset used for reporting and margin of error",
        r"margin of error",
        r"\bmethodologies\b",
        r"\bmetodolog",
        r"\bdatakvalitet\b",
        r"\bdata quality\b",
    ],
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
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_likely_toc(text: str, matched_sections_count: int) -> bool:
    text_norm = normalize_text(text)

    if "indholdsfortegnelse" in text_norm:
        return True
    if matched_sections_count >= 4:
        return True
    if re.search(r"\b1\.\s*summary\b", text_norm) and re.search(r"\b2\.", text_norm):
        return True
    return False


def detect_sections_for_page(page_record: dict):
    text = normalize_text(page_record["text"])
    hits = []

    for section_name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                hits.append({
                    "statement_id": page_record["statement_id"],
                    "firm_name": page_record["firm_name"],
                    "section_name": section_name,
                    "page_num": page_record["page_num"],
                    "source_file": page_record["source_file"],
                    "matched_pattern": pattern,
                    "is_toc_page": False,
                })
                break

    if hits:
        toc_flag = is_likely_toc(page_record["text"], len(hits))
        for hit in hits:
            hit["is_toc_page"] = toc_flag

    return hits


def choose_best_hits(raw_hits: list):
    grouped = defaultdict(list)
    for hit in raw_hits:
        key = (hit["statement_id"], hit["section_name"])
        grouped[key].append(hit)

    best_hits = []

    for (_, _), hits in grouped.items():
        non_toc_hits = [h for h in hits if not h["is_toc_page"]]

        candidates = non_toc_hits if non_toc_hits else hits
        best_hit = sorted(candidates, key=lambda x: x["page_num"])[0]
        best_hits.append(best_hit)

    return sorted(best_hits, key=lambda x: (x["statement_id"], x["page_num"], x["section_name"]))


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    pages = load_jsonl(INPUT_PATH)
    raw_hits = []

    print("Detecting section pages...\n")

    for page in pages:
        raw_hits.extend(detect_sections_for_page(page))

    raw_hits = sorted(raw_hits, key=lambda x: (x["statement_id"], x["page_num"], x["section_name"]))
    best_hits = choose_best_hits(raw_hits)

    write_jsonl(RAW_OUTPUT_PATH, raw_hits)
    write_jsonl(BEST_OUTPUT_PATH, best_hits)

    grouped = defaultdict(list)
    for hit in best_hits:
        grouped[hit["statement_id"]].append(hit)

    for statement_id, hits in grouped.items():
        print(f"[OK] {statement_id}:")
        for h in hits:
            toc_note = " [TOC fallback]" if h["is_toc_page"] else ""
            print(f"   - {h['section_name']} (p.{h['page_num']}){toc_note}")

    print("\nDone.")
    print(f"Raw section hits written: {len(raw_hits)}")
    print(f"Best section hits written: {len(best_hits)}")
    print(f"Raw output: {RAW_OUTPUT_PATH}")
    print(f"Best output: {BEST_OUTPUT_PATH}")


if __name__ == "__main__":
    main()