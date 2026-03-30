# STATE MACHINE

## States

INGESTED
FINGERPRINTED
CANDIDATE_FOUND
PARTIALLY_VERIFIED
FULLY_IDENTIFIED
TAGGED
STORED
FAILED

---

## Transitions

INGESTED → FINGERPRINTED

FINGERPRINTED → CANDIDATE_FOUND

CANDIDATE_FOUND →
  PARTIALLY_VERIFIED (if high score)
  OR FULLY_IDENTIFIED (fallback)

PARTIALLY_VERIFIED →
  FULLY_IDENTIFIED (if success)
  OR FULLY_IDENTIFIED (after full AcoustID fallback)
  OR FAILED (if full AcoustID fallback also fails)

FULLY_IDENTIFIED → TAGGED

TAGGED → STORED

ANY → FAILED (on unrecoverable error)

---

## Retry Rules

- FAILED can be retried up to N times
- Retry state resumes from last successful step