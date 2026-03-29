# SST Project - Systems and Tools (AI-Oriented Redesign)

---

## 1. Overview

This document defines the **systems, tools, and agent roles** used in SST.

SST is developed and operated as an **AI-assisted distributed system**, where AI agents act as core contributors.

---

## 2. Development Philosophy

* AI-first development
* Human-in-the-loop validation
* Modular and reproducible systems
* Distributed execution

---

## 3. Agent Roles

### 3.1 Coder Agent

* Implements modules
* Writes clean, testable code

---

### 3.2 Reviewer Agent

* Validates code quality
* Ensures adherence to rules

---

### 3.3 Researcher Agent

* Gathers external information
* Improves matching accuracy

---

### 3.4 Integrator Agent

* Connects modules
* Maintains system consistency

---

### 3.5 Operator (Human)

* Final decision maker
* Handles edge cases
* Reviews low-confidence outputs

---

## 4. Toolchain

### 4.1 Development

* VS Code
* GitHub Copilot / Agent
* GitHub (PR workflow)

---

### 4.2 Runtime

* Docker (containerization)
* Prefect (orchestration)
* MinIO (object storage)

---

### 4.3 Audio Processing

* FFmpeg
* AcoustID (Chromaprint)

---

### 4.4 Metadata

* MusicBrainz API
* Steam API

---

### 4.5 AI / Automation

* Local LLM (Ollama on M2 Mac)
* browser-use (web automation)

---

## 5. Development Workflow

```text
Spec → Task → Agent → PR → Review → Merge
```

---

### Steps

1. Define task (TASKS.md)
2. Assign to AI Agent
3. Generate code
4. Create Pull Request
5. Review (AI + Human)
6. Merge

---

## 6. Execution Workflow

```text
Scout → Core → Worker → Storage
```

---

### Scout

* Web scraping
* Metadata acquisition

---

### Core

* Prefect orchestration
* State management

---

### Worker

* Audio processing
* Tagging
* AcoustID matching

---

## 7. Infrastructure Mapping

| Role   | Node          |
| ------ | ------------- |
| Scout  | SST-Scout-VM  |
| Core   | SST-Core-VM   |
| Worker | SST-Worker-CT |
| AI     | M2 Mac        |

---

## 8. Environment Management

* Python 3.11
* uv for dependency management
* Docker for isolation

---

## 9. Design Rules

* Stateless processing
* Idempotent tasks
* Clear I/O contracts
* Retry-safe operations

---

## 10. Future Extensions

* Multi-node scaling
* Distributed cache
* AI-assisted review UI
* Community contribution (OSS)

---

## 11. Key Insight

SST is not just a system.

It is a **collaboration framework between humans and AI agents**.

---

# END
