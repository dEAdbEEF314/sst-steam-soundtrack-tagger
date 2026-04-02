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

> [!NOTE]
> **Scout VM の環境について**
> Scout VM は API 経由の解決に加えて、AI エージェントのデバッグ、ボット対策回避のための Headed mode 実行、および CAPTCHA 解決等の手動介入を想定し、Ubuntu Desktop (GUI) 環境を維持します。

---

## 3. System Architecture

```text
[Scout VM]
   ↓
[Prefect Flow (Core VM)]
   ↓
[Worker Containers]
   ↓
[SeaweedFS S3 Storage]
```

---

## 4. Roles

### Scout VM

* Web metadata resolution (API & CDDB)
* Fallback browser automation (browser-use)
* Manual review / Captcha solving

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

### LLM Node (M2 Mac or others)

* API 経由のマルチバックエンド LLM 推論
* デフォルト: Ollama (ローカル推論)
* 選択可能: Gemini API, OpenAI API
* 役割: メタデータの不整合解決、検索結果のスコアリング、複雑な HTML パース

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
4. Results stored in SeaweedFS

---

## 7. Storage

SeaweedFS (S3-compatible)

```text
buckets/
 └─ sst/
     ├─ ingest/
     ├─ archive/
     ├─ review/
     └─ workspace/
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
