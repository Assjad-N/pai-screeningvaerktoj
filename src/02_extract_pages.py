from pathlib import Path
import json
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_PATH = PROJECT_ROOT / "data" / "interim" / "documents.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "pages.jsonl"


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


def extract_pages_from_pdf(
    statement_id: str,
    firm_name: str,
    source_file: str,
    source_url: str,
    click_depth_manual,
):
    page_records = []

    pdf_path = Path(source_file)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            page_records.append(
                {
                    "statement_id": statement_id,
                    "firm_name": firm_name,
                    "source_file": str(pdf_path),
                    "source_url": source_url,
                    "click_depth_manual": click_depth_manual,
                    "page_num": i,
                    "total_pages": total_pages,
                    "text": text,
                }
            )

    return page_records


def main():
    documents = load_jsonl(DOCUMENTS_PATH)

    all_page_records = []

    print("Extracting pages from PDFs...\n")

    for doc in documents:
        if not doc.get("file_exists", False):
            print(f"[SKIP] {doc['statement_id']}: file does not exist")
            continue

        page_records = extract_pages_from_pdf(
            statement_id=doc["statement_id"],
            firm_name=doc["firm_name"],
            source_file=doc["source_file"],
            source_url=doc.get("source_url", ""),
            click_depth_manual=doc.get("click_depth_manual"),
        )

        all_page_records.extend(page_records)

        print(f"[OK] {doc['statement_id']}: extracted {len(page_records)} pages")

    write_jsonl(OUTPUT_PATH, all_page_records)

    print("\nDone.")
    print(f"Total page records written: {len(all_page_records)}")
    print(f"Output file: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()