from pathlib import Path
import json
import csv
import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "interim" / "indicator_rows.jsonl"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "indicator_quality_prompt.txt"
JSONL_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_llm_review.jsonl"
CSV_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "indicator_llm_review.csv"

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
    "actions_present",
    "planned_actions_present",
    "target_present",
    "target_measurable",
    "indicator_action_link_clear",
    "uses_generic_policy_reference_only",
    "low_data_coverage_flag",
    "review_priority",
    "top_issue",
    "evidence_snippet_1",
    "evidence_snippet_2",
    "confidence",
]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col) for col in CSV_COLUMNS})


def load_prompt(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read().strip()


def build_user_message(row: Dict[str, Any]) -> str:
    return f"""
Indicator metadata:
- indicator_code: {row["indicator_code"]}
- indicator_name: {row["indicator_name"]}
- firm_name: {row["firm_name"]}
- page_num: {row["page_num"]}

Extracted row text:
\"\"\"
{row["raw_indicator_text"]}
\"\"\"
""".strip()


def extract_json_from_response(text: str) -> Dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")

    return json.loads(text[start:end + 1])


def validate_llm_output(data: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = [
        "actions_present",
        "planned_actions_present",
        "target_present",
        "target_measurable",
        "indicator_action_link_clear",
        "uses_generic_policy_reference_only",
        "low_data_coverage_flag",
        "review_priority",
        "top_issue",
        "evidence_snippet_1",
        "evidence_snippet_2",
        "confidence",
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field in LLM output: {field}")

    if data["review_priority"] not in {"low", "medium", "high"}:
        raise ValueError("Invalid review_priority value.")

    if data["confidence"] not in {"low", "medium", "high"}:
        raise ValueError("Invalid confidence value.")

    return data


def call_llm(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    text = response.choices[0].message.content or ""
    parsed = extract_json_from_response(text)
    return validate_llm_output(parsed)


def call_llm_with_retries(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
    max_retries: int = 5,
) -> Dict[str, Any]:
    for attempt in range(max_retries):
        try:
            return call_llm(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
            )

        except Exception as e:
            error_text = str(e).lower()

            is_retryable = (
                "rate_limit_exceeded" in error_text
                or "requests per min" in error_text
                or "please try again in" in error_text
            )

            if is_retryable and attempt < max_retries - 1:
                wait_seconds = 25
                print(f"  -> Rate limit hit. Sleeping {wait_seconds}s and retrying...")
                time.sleep(wait_seconds)
                continue

            raise


def main() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")

    client = OpenAI(api_key=api_key)

    rows = load_jsonl(INPUT_PATH)
    system_prompt = load_prompt(PROMPT_PATH)

    existing_results = load_jsonl(JSONL_OUTPUT_PATH)
    completed_row_ids = {row["row_id"] for row in existing_results}

    rows_to_review = [
        row
        for row in rows
        if row.get("text_extraction_status") == "high"
        and row["row_id"] not in completed_row_ids
    ]

    results: List[Dict[str, Any]] = existing_results.copy()

    print(f"Existing completed rows: {len(existing_results)}")
    print(f"Rows left to review: {len(rows_to_review)}\n")

    for i, row in enumerate(rows_to_review, start=1):
        print(
            f"[{i}/{len(rows_to_review)}] Reviewing "
            f"{row['statement_id']} {row['indicator_code']} p.{row['page_num']}"
        )

        try:
            llm_result = call_llm_with_retries(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_message=build_user_message(row),
            )

            output_row = {
                "row_id": row["row_id"],
                "statement_id": row["statement_id"],
                "firm_name": row["firm_name"],
                "source_file": row.get("source_file"),
                "source_url": row.get("source_url"),
                "click_depth_manual": row.get("click_depth_manual"),
                "indicator_code": row["indicator_code"],
                "indicator_name": row["indicator_name"],
                "page_num": row["page_num"],
                "score": row.get("score"),
                "text_extraction_status": row.get("text_extraction_status"),
                **llm_result,
            }

            results.append(output_row)

            write_jsonl(JSONL_OUTPUT_PATH, results)
            write_csv(CSV_OUTPUT_PATH, results)

            time.sleep(1.5)

        except Exception as e:
            print(f"  -> ERROR: {e}")

    write_jsonl(JSONL_OUTPUT_PATH, results)
    write_csv(CSV_OUTPUT_PATH, results)

    print("\nDone.")
    print(f"LLM-reviewed rows written: {len(results)}")
    print(f"JSONL output: {JSONL_OUTPUT_PATH}")
    print(f"CSV output: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()