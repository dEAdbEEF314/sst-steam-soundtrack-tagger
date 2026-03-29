# Coding Rules

## Language

* Python 3.11

---

## Requirements

* Type hints required
* Logging required
* Exception handling required

---

## Style

* Follow PEP8
* Use dataclasses where applicable

---

## API Rules

* Retry on failure (max 3)
* Respect rate limits

---

## Logging

Each step must log:

* job_id
* step
* result
* error (if any)

