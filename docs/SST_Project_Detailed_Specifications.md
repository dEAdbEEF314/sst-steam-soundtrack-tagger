# SST (Steam Soundtrack Tagger) - Detailed Specifications

---

## 1. Overview

SST is a distributed metadata resolution system for **Steam-purchased soundtracks**.

It combines:

* Steam metadata
* MusicBrainz search
* AcoustID verification

---

## 2. System Architecture (UPDATED)

SST operates as a **distributed, orchestrated system**.

### Nodes

* Scout Node: metadata acquisition
* Core Node: orchestration (Prefect)
* Worker Nodes: audio processing

---

## 3. Orchestration Layer (NEW)

SST uses **Prefect** to manage execution.

### Responsibilities

* Task scheduling
* Retry handling
* State tracking
* Parallel execution

---

## 4. Execution Model (NEW)

* Asynchronous processing
* Task-level parallelism
* Distributed execution across nodes

---

## 5. Node Responsibilities (NEW)

### Scout

* Fetch Steam metadata
* Perform web-based enrichment

---

### Core

* Execute Prefect flows
* Manage pipeline state

---

### Worker

* AcoustID processing
* Audio tagging
* File operations

---

## 6. Pipeline

1. Steam metadata acquisition
2. MusicBrainz candidate search
3. Candidate scoring
4. Album determination
5. Partial AcoustID verification
6. Full AcoustID fallback
7. Metadata enrichment
8. Tag writing

---

## 7. MusicBrainz Strategy

* Multi-language query (ja → en → original)
* Merge results
* Deduplicate

---

## 8. Candidate Scoring

score = title + track + date + format

---

## 9. Partial Verification

* First 3 tracks
* Match ratio ≥ threshold

---

## 10. Storage

* MinIO (S3)

---

## 11. State Management

* Managed by Prefect

---

## 12. Design Principles

* Distributed-first
* Orchestration-driven
* Fault tolerant
* Human fallback

---

# END
