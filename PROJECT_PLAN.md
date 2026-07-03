# DPR Monitoring Agent
## Project Plan

---

# Vision

Build a local AI-powered DPR RI Monitoring Assistant capable of automatically processing Executive Summary documents into structured monitoring reports.

The assistant should reduce manual processing time while keeping a human analyst in full control of the final output.

The system must work entirely offline using local AI models (Ollama).

---

# Goals

Primary Goals

- Process Executive Summary PDFs
- Extract every issue
- Preserve original descriptions
- Remove duplicate issues
- Classify each issue into ONE AKD
- Explain the classification
- Generate Excel
- Generate Word
- Generate JSON
- Require human review only when confidence is low

Secondary Goals

- Historical issue database
- Trend analysis
- Search previous issues
- Dashboard
- Multi-agent architecture
- One-click report generation

---

# Success Metrics

The project is successful if:

✓ One PDF can be processed in under 60 seconds.

✓ Duplicate detection accuracy >90%.

✓ AKD classification accuracy >90%.

✓ Human editing time reduced by at least 80%.

✓ No confidential documents leave the local computer.

---

# Architecture

```
                 Executive Summary PDF
                          │
                          ▼
                 PDF Processing Service
                          │
                          ▼
                  Text Extraction Service
                          │
                          ▼
                  Issue Extraction Service
                          │
                          ▼
                 Duplicate Detection Service
                          │
                          ▼
                  AKD Classification Service
                          │
                          ▼
                     Review Service
                          │
                          ▼
                  Report Generation Service
                          │
                          ▼
        Excel │ Word │ JSON │ Dashboard
```

---

# Technology Stack

Backend

- Python
- FastAPI

AI

- Ollama
- Qwen3 4B
- Gemma3 4B
- Phi4 Mini

Data

- Pandas
- Pydantic

PDF

- PyMuPDF

Embeddings

- sentence-transformers

Similarity

- RapidFuzz

Reports

- openpyxl
- python-docx

Frontend

- Streamlit

Container

- Docker
- Docker Compose

Future

- ChromaDB

---

# Project Milestones

---

# Milestone 1
## Environment Setup

Objective

Create a reproducible development environment.

Tasks

- Create repository
- Configure Docker
- Configure FastAPI
- Configure Ollama
- Configure virtual environment
- Configure logging
- Configure project structure

Deliverables

- Working Docker Compose
- Backend starts successfully
- Ollama reachable
- API health endpoint

Acceptance Criteria

GET /health returns 200.

---

# Milestone 2
## PDF Processing

Objective

Read Executive Summary PDFs.

Tasks

- Upload PDF
- Extract text
- Handle OCR-ready PDFs
- Preserve page numbers
- Store extracted text

Deliverables

Raw text output

Acceptance Criteria

95%+ of PDF text extracted correctly.

---

# Milestone 3
## Section Detection

Objective

Automatically detect report sections.

Examples

Top Issue

Alert Issue

Isu Harian

Media Online

Media Sosial

Tasks

- Detect headings
- Split document
- Preserve order

Acceptance Criteria

Sections detected correctly.

---

# Milestone 4
## Issue Extraction

Objective

Extract every issue.

Output

```json
{
    "title":"",
    "description":"",
    "date":"",
    "section":""
}
```

Tasks

- Prompt engineering
- JSON validation
- Retry malformed outputs

Acceptance Criteria

Issues extracted correctly.

Descriptions preserved.

---

# Milestone 5
## Duplicate Detection

Objective

Merge duplicate issues.

Tasks

- Generate embeddings
- Compute similarity
- Merge duplicates

Keep

- longest description
- earliest date
- source sections

Acceptance Criteria

Duplicate accuracy above 90%.

---

# Milestone 6
## AKD Classification

Objective

Assign exactly ONE AKD.

Knowledge

- MKD
- BURT
- Baleg
- Komisi I-XIII
- Banggar
- etc.

Tasks

- Rule engine
- AI fallback
- Confidence scoring

Acceptance Criteria

One AKD only.

Confidence returned.

---

# Milestone 7
## Quality Review

Objective

Detect problems automatically.

Checks

Missing date

Missing AKD

Duplicate title

Low confidence

Unknown section

Acceptance Criteria

Problematic records flagged.

---

# Milestone 8
## Report Generation

Generate

Excel

Word

JSON

Tasks

Standardized formatting

Automatic filenames

Acceptance Criteria

Output matches analyst template.

---

# Milestone 9
## Dashboard

Features

Upload PDF

View extracted issues

Edit AKD

Approve report

Download Excel

Download Word

Acceptance Criteria

Entire workflow usable without command line.

---

# Milestone 10
## Historical Database

Store

Issue

AKD

Date

Description

Source

Embedding

Capabilities

Search

Filter

Trend analysis

Duplicate detection across reports

---

# Future Milestones

## Daily Monitoring

Automatically monitor folder.

When new PDF arrives

↓

Run pipeline

↓

Generate report

↓

Notify analyst.

---

## Trend Analysis

Examples

Top recurring issues

Most active AKD

Monthly issue counts

Issue timeline

---

## Semantic Search

Examples

Show all MKD issues.

Show every issue mentioning KPK.

Find similar issues from previous months.

---

## Multi-Agent System

Supervisor Agent

↓

PDF Agent

↓

Extraction Agent

↓

Classification Agent

↓

Review Agent

↓

Report Agent

---

# Folder Structure

```
dpr-monitoring-agent/

backend/

frontend/

knowledge/

prompts/

tests/

docker/

docs/

scripts/

data/

pdfs/

output/
```

---

# Repository Structure

backend/

services/

routers/

models/

schemas/

utils/

knowledge/

tests/

frontend/

streamlit/

docs/

---

# Coding Standards

Every feature must include

- Unit tests
- Type hints
- Logging
- Error handling
- Documentation

Avoid

Large functions

Duplicate logic

Magic numbers

Hardcoded paths

---

# Risks

## AI Hallucination

Mitigation

Rule-based validation.

Human review.

---

## Incorrect AKD

Mitigation

Confidence scoring.

Knowledge base.

Human approval.

---

## Duplicate Detection Errors

Mitigation

Embedding similarity

+

Manual review

---

## Large PDFs

Mitigation

Chunk processing.

Streaming.

---

# Long-Term Vision

The project evolves from

PDF Processor

↓

AI Extraction Tool

↓

Monitoring Assistant

↓

Knowledge Management System

↓

Decision Support System

↓

Autonomous DPR Monitoring Agent

The architecture should remain modular so future AI capabilities can be added without rewriting the core system.