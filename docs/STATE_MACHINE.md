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
  INGESTED → IDENTIFIED (Candidates Found / MusicBrainz Search)
  IDENTIFIED → FINGERPRINTED (AcoustID Verification Started)
  FINGERPRINTED → ENRICHED (AcoustID Verified / Fallback Success)
  ENRICHED → TAGGED
  TAGGED → STORED

- **Fast-track Path:**
  INGESTED → IDENTIFIED (MusicBrainz Score >= skip_acoustid_threshold)
  IDENTIFIED → ENRICHED (AcoustID Skipped)
  ENRICHED → TAGGED
  TAGGED → STORED

- **Failure Path:**
  ANY → FAILED (on low confidence fallback or unrecoverable error)

---

## Retry Rules

- FAILED can be retried up to N times via Prefect mechanics.
- Retry state resumes from last successful task based on task cache/flow status.