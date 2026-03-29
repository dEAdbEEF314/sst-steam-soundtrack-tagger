# SST Architecture

---

## 1. System Overview

SST is a **distributed, orchestrated, multi-node pipeline system**.

It is designed to run across multiple machines and containers, coordinated by Prefect.

---

## 2. Physical Infrastructure

### Nodes

* SST-Scout-VM (Ubuntu Desktop + Docker)
* SST-Core-VM (Ubuntu Server + Docker)
* SST-Worker-CT (Container, USB-SSD mounted)
* M2 MacBook Air (AI / LLM support)

---

## 3. System Architecture

```text
[Scout VM]
   ↓
[Prefect Flow (Core VM)]
   ↓
[Worker Containers]
   ↓
[MinIO Storage]
```

---

## 4. Roles

### Scout VM

* Web metadata acquisition
* browser-use execution

---

### Core VM

* Prefect orchestration
* Flow control
* State tracking

---

### Worker Containers

* Audio processing
* AcoustID matching
* Tag writing

---

### M2 Mac

* Local LLM (Ollama)
* AI assistance

---

## 5. Orchestration (Prefect)

Prefect manages:

* Task execution order
* Retry logic
* State transitions
* Observability

---

## 6. Data Flow

1. Scout collects metadata
2. Core schedules flow
3. Workers process tasks
4. Results stored in MinIO

---

## 7. Storage

MinIO (S3-compatible)

```text
bucket/
 ├─ raw/
 ├─ processed/
 ├─ review/
 └─ cache/
```

---

## 8. Parallelism

* Prefect task-level parallel execution
* Multiple workers per task

---

## 9. Design Principles

* Orchestration-first
* Node separation
* Fault tolerance
* Reproducibility

---

# END
