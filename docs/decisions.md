# Baselines

* ADR-001: Windows-first
  * Why: packaging +  support simplicity
* ADR-002: Local-first, no cloud
  * Why: privacy, cost, legal simplicity
* ADR-003: Evidence-backed questions
  * Why: trust/reliability   

## Week 2

* “CLI prototype: generate MCQ from .txt via Ollama; output strict JSON”

* “Add JSON validation + retry on invalid output”

## Week 3

* “PDF ingestion v1: extract text page-by-page”

* “DOCX ingestion v1: extract headings + paragraphs”

* “Normalize output format (doc → chunks)”

## Week 4

* “Chunking function (size + overlap)”

* “SQLite schema for documents + chunks”

* “Store chunks in SQLite with source metadata”