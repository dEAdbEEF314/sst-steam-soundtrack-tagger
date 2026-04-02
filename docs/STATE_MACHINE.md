# STATE MACHINE

## States

INGESTED
IDENTIFIED
FINGERPRINTED
ENRICHED
TAGGED
STORED
FAILED

---

## Transitions

- **Standard Path:**
  INGESTED → IDENTIFIED (Candidates Found)
  IDENTIFIED → FINGERPRINTED (AcoustID Verification Started)
  FINGERPRINTED → ENRICHED (AcoustID Verified / Fallback Success)
  ENRICHED → TAGGED
  TAGGED → STORED

- **Fast-track Path:**
  INGESTED → IDENTIFIED
  IDENTIFIED → ENRICHED (AcoustID Skipped due to very high confidence)
  ENRICHED → TAGGED
  TAGGED → STORED

- **Failure Path:**
  ANY → FAILED (on low confidence fallback or unrecoverable error)

---

## Retry Rules

- FAILED can be retried up to N times via Prefect mechanics.
- Retry state resumes from last successful task based on task cache/flow status.