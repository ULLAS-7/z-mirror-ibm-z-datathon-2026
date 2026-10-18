# Architecture

```text
Public UCI Bank Marketing benchmark (45,211 rows)
                     |
                     v
    Python/Jupyter workflow inside Docker
              on LinuxONE s390x
                     |
       +-------------+------------------+
       |                                |
       v                                v
Seeded synthetic generator     Reference normalization
       |                                |
       +---------------+----------------+
                       v
        Candidate CSV + SHA-256 manifest
                       |
                       v
        Schema/range/ID validator
                       |
                       v
          Fixed-width record file
                       |
          +------------+-----------+
          |            |           |
          v            v           v
       Utility      Empirical     COBOL consumer
      comparison   risk checks    compatibility test
          |            |           |
          +------------+-----------+
                       v
             Evidence-based release gate
             PASS / FAIL / INCONCLUSIVE
```

Current implementation status differs by stage: generation and validator tests are verified; the older V1 utility comparison exposed material mismatch; V2 utility thresholds/results, empirical privacy-risk checks and actual COBOL execution remain to be completed. Do not claim these pending gates passed.
