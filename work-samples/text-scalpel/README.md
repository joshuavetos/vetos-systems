# Text Scalpel Pro v3.0

A surgical code injection engine designed for deterministic, indentation-aware source code modifications.

## Core Features
- **Indentation Preservation**: Automatically matches the indentation of the target anchor.
- **Surgical Precision**: Uses regex with strict match counting to prevent global side-effects.
- **Full-Stack Ready**: Includes a FastAPI backend and a notebook-ready interactive dashboard.

## Installation
```bash
pip install .
Quick Start (API)
python main.py
The server will start at http://0.0.0.0:8000.
