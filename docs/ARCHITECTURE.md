# SST Architecture

## Pipeline

1. Steam Metadata Fetch
2. MusicBrainz Search
3. Candidate Filtering
4. Scoring
5. Album Determination
6. AcoustID Verification
7. Metadata Enrichment
8. Tag Writing
9. Storage

---

## Module Structure

```
src/
 ├─ steam/
  ├─ musicbrainz/
   ├─ acoustid/
    ├─ scoring/
     ├─ pipeline/
      ├─ tagging/
       └─ storage/
       ```

       ---

## State Flow

INGESTED → IDENTIFIED → VERIFIED → TAGGED → STORED

