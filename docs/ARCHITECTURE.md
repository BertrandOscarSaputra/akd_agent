# Architecture

## Philosophy

Small services.

Single responsibility.

Deterministic logic before AI.

---

## Pipeline

PDF

↓

PDF Service

↓

Text Extraction

↓

Section Detection

↓

Issue Extraction

↓

Duplicate Detection

↓

AKD Classification

↓

Quality Review

↓

Report Generation

---

## Services

### PDF Service

Responsibilities

- Read PDFs
- OCR support
- Extract text

---

### Extraction Service

Responsibilities

- Detect issues
- Preserve descriptions
- Detect dates

---

### Deduplication Service

Responsibilities

- Semantic similarity
- Merge duplicates

---

### Classification Service

Responsibilities

- Rule engine
- AI fallback

---

### Export Service

Responsibilities

Generate

- Excel
- Word
- JSON

---

## Future

- ChromaDB
- Multi-Agent
- Dashboard
