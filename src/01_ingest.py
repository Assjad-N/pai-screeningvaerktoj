from pathlib import Path
import json
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "documents.jsonl"


def write_jsonl(path: Path, records: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    documents = config["documents"]
    output_records = []

    print("Checking configured documents...\n")

    for doc in documents:
        source_file = PROJECT_ROOT / doc["source_file"]
        file_exists = source_file.exists()

        record = {
            "statement_id": doc["statement_id"],
            "firm_name": doc["firm_name"],
            "source_file": str(source_file),
            "source_url": doc.get("source_url", ""),
            "click_depth_manual": doc.get("click_depth_manual"),
            "found_via_site_search_manual": doc.get("found_via_site_search_manual"),
            "file_exists": file_exists,
        }

        output_records.append(record)

        status = "[OK]" if file_exists else "[MISSING]"
        print(f"{status:8} {doc['statement_id']} -> {source_file.name}")

    write_jsonl(OUTPUT_PATH, output_records)

    print("\nDone.")
    print(f"Valid documents written: {len(output_records)}")
    print(f"Output file: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()