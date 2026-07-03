# DPR Monitoring Agent

An AI-assisted monitoring platform for DPR RI Executive Summary documents.

The system automatically extracts issues from Executive Summary PDFs, removes duplicate issues, classifies them into the appropriate DPR RI Alat Kelengkapan Dewan (AKD), and generates standardized monitoring reports.

The project is designed to run completely locally using Ollama to ensure confidential government documents never leave the user's computer.

---

## Features

- PDF Processing
- Executive Summary Parsing
- AI Issue Extraction
- Duplicate Detection
- AKD Classification
- Confidence Scoring
- Human Review
- Excel Export
- Word Export
- JSON Export

---

## Tech Stack

Backend

- FastAPI
- Python

AI

- Ollama
- Qwen3
- Gemma3
- Phi4 Mini

Data

- Pandas
- Pydantic

PDF

- PyMuPDF

Reports

- openpyxl
- python-docx

Frontend

- Streamlit

Container

- Docker Compose

---

## Project Status

Current Version

v0.1

Current Milestone

Environment Setup
