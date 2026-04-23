from pathlib import Path
import json
import csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_review_scores.jsonl"
JSONL_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "review_queue.jsonl"
CSV_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "review_queue.csv"

OUTPUT_COLUMNS = [
    "statement_id",
    "firm_name",
    "indicator_code",
    "indicator_name",
    "page_num",
    "review_priority",
    "review_score",
    "top_issue",
    "review_reason",
    "confidence",
    "llm_review_priority",
    "text_extraction_status",
    "click_depth_manual",
    "source_url",
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
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col) for col in OUTPUT_COLUMNS})


def build_review_queue_row(row: dict) -> dict:
    return {
        "statement_id": row["statement_id"],
        "firm_name": row["firm_name"],
        "indicator_code": row["indicator_code"],
        "indicator_name": row["indicator_name"],
        "page_num": row["page_num"],
        "review_priority": row["review_priority"],
        "review_score": row["review_score"],
        "top_issue": row.get("top_issue"),
        "review_reason": row.get("review_reason"),
        "confidence": row.get("confidence"),
        "llm_review_priority": row.get("llm_review_priority"),
        "text_extraction_status": row.get("text_extraction_status"),
        "click_depth_manual": row.get("click_depth_manual"),
        "source_url": row.get("source_url"),
    }


def review_priority_sort_value(priority: str) -> int:
    order = {"high": 0, "medium": 1, "low": 2}
    return order.get(priority, 99)


def main():
    rows = load_jsonl(INPUT_PATH)

    review_queue = [build_review_queue_row(row) for row in rows]

    review_queue = sorted(
        review_queue,
        key=lambda x: (
            review_priority_sort_value(x["review_priority"]),
            -x["review_score"],
            x["firm_name"],
            x["indicator_code"],
            x["page_num"],
        ),
    )

    write_jsonl(JSONL_OUTPUT_PATH, review_queue)
    write_csv(CSV_OUTPUT_PATH, review_queue)

    print("Done.")
    print(f"Review queue rows written: {len(review_queue)}")
    print(f"JSONL output: {JSONL_OUTPUT_PATH}")
    print(f"CSV output: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()