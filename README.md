# RepoMind

> Understand any codebase in minutes, not days.

RepoMind is an AI-powered repository intelligence system that analyzes software projects using Abstract Syntax Trees (ASTs), dependency graphs, semantic search, and Retrieval-Augmented Generation (RAG).

Instead of treating a repository as plain text, RepoMind builds a structural understanding of the codebase, allowing developers to explore architecture, trace dependencies, analyze impact, and chat with repositories using grounded answers.

---

## Vision

Modern AI assistants struggle with large repositories because they rely primarily on text retrieval.

RepoMind is designed to solve this by combining:

- Repository ingestion
- Source code parsing with Tree-sitter
- Symbol graph construction
- Semantic code embeddings
- Dependency analysis
- Retrieval-Augmented Generation (RAG)

The goal is to make understanding unfamiliar codebases dramatically faster.

---

## Current Progress

### ✅ Module 1 — Repository Ingestion

- Clone Git repositories
- Validate GitHub URLs
- Detect existing repositories
- Prevent corrupted clones
- Structured logging
- Unit tested

### ✅ Module 2 — Repository Scanner

- Recursive repository traversal
- Multi-language source file detection
- Ignore build and cache directories
- Deterministic scanning
- Source file metadata extraction
- Comprehensive unit tests

### 🚧 Upcoming Modules

- Tree-sitter Parsing
- Symbol Graph Construction
- Impact Analysis
- Semantic Embeddings
- Vector Search
- Repository RAG Chat
- Architecture Visualization
- Repository Health Metrics
- Web Dashboard

---

## Project Architecture

```
Git Repository
       │
       ▼
Repository Downloader
       │
       ▼
Repository Scanner
       │
       ▼
Tree-sitter Parser
       │
       ▼
Symbol Graph
       │
       ▼
Embeddings
       │
       ▼
Semantic Search
       │
       ▼
Repository RAG
```

---

## Tech Stack

- Python 3.13
- GitPython
- Pytest
- Tree-sitter *(upcoming)*
- FAISS *(upcoming)*
- LangChain *(upcoming)*
- FastAPI *(planned)*
- React *(planned)*

---

## Repository Structure

```
RepoMind/
│
├── backend/
├── tests/
├── docs/
├── repos/
├── requirements.txt
└── README.md
```

---

## Running the Project

Clone the repository:

```bash
git clone https://github.com/<your-username>/RepoMind.git
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python -m backend.main <github_repository_url>
```

Example:

```bash
python -m backend.main https://github.com/pallets/flask
```

Run tests:

```bash
pytest -v
```

---

## Development Philosophy

RepoMind is being developed module by module.

Each module is:

- Independently testable
- Fully documented
- Production-oriented
- Reviewed before integration

This approach emphasizes software engineering principles such as modularity, maintainability, deterministic behavior, and comprehensive testing.

---

## Roadmap

- [x] Repository Ingestion
- [x] Repository Scanner
- [ ] Tree-sitter Parsing
- [ ] Symbol Graph
- [ ] Impact Analysis
- [ ] Semantic Embeddings
- [ ] Vector Search
- [ ] Repository RAG
- [ ] Architecture Visualization
- [ ] Repository Health Metrics
- [ ] Frontend Dashboard
- [ ] Deployment

---

## License

This project is licensed under the MIT License.