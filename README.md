# PAI Statement Screener

Prototype for AI-assisted screening of entity-level PAI statements for review-relevant disclosure issues.

## Purpose

The tool is designed to support risk-based manual review of selected PAI disclosures. It combines rule-based checks, LLM-based text assessment, and simple accessibility signals to prioritise which indicator rows and institutions may warrant closer inspection.

This prototype is a decision-support tool. It does not determine legal compliance.

## Scope

The current prototype analyses the following selected PAI indicators:

- 1.1 GHG emissions
- 1.2 Carbon footprint
- 1.4 Exposure to fossil fuel companies
- 1.10 UNGC/OECD violations
- 1.11 Lack of compliance processes/mechanisms
- 1.14 Controversial weapons

## Project structure

- `data/raw/` raw PDF statements
- `data/interim/` intermediate outputs
- `data/processed/` final tables for scoring and app use
- `src/` pipeline scripts
- `app/` Streamlit app
- `prompts/` prompt files
- `requirements.txt` Python dependencies

## Current workflow

1. Ingest document metadata
2. Extract page text from PDF files
3. Detect relevant statement sections
4. Build candidate indicator rows for selected PAI indicators
5. Apply rule-based text flags
6. Run LLM-based row review
7. Merge rule-based and LLM-based signals into final review scores
8. Export prioritised outputs for dashboard use
9. Display results in Streamlit

## Sample set

The current sample includes:

- Jyske Bank
- BankInvest
- Nordea Funds
- Danske Invest
- Sparinvest
- Nordea Bank Abp

## Streamlit app

The Streamlit app provides:

- an overview of sources, extraction quality, and prioritised findings
- institution-level summaries
- expandable indicator-level review results
- a detailed indicator inspection page
- a transparent method page describing the scoring logic

## Notes

The prioritisation logic is LLM-first:
- the LLM provides the base disclosure-risk assessment
- rule-based checks act as supporting and control signals
- accessibility and technical-extraction signals are included as supplementary risk indicators

The app is intended for demonstration and analytical review purposes.
