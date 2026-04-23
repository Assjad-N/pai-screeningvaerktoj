# PAI Statement Screener

Prototype for screening entity-level PAI statements for review-relevant disclosure issues.

## Project structure

- `data/raw/` raw PDF statements
- `data/interim/` intermediate outputs
- `data/processed/` final tables for review and app use
- `data/labels/` manual labels for evaluation
- `src/` pipeline scripts
- `app/` Streamlit app
- `outputs/` exported results and screenshots
- `prompts/` prompt files
- `tests/` basic tests

## Current workflow

1. Ingest documents
2. Extract page text
3. Detect sections
4. Build indicator rows
5. Apply rule-based flags
6. Score and export review queue
7. Display outputs in Streamlit

## Sample set

- Jyske
- BankInvest
- Nordea Funds
- Danske Invest
- Sparinvest
- Nordea Bank Abp

## Notes

This prototype is a decision-support tool for prioritising manual review. It does not determine legal compliance.