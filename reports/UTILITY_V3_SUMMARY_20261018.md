# Z-Mirror V3 — Experimental Utility Comparison

- Reference rows: 45,211
- V2 rows: 1,000
- V3 rows: 1,000
- V3 SHA-256: `41334f9fa5f2ec0847edc09135ead30a634856a9b3d7c76b20a49657eb4203b7`
- Manifest hash matches CSV: True

| Measure | Reference | V2 | V3 |
|---|---:|---:|---:|
| age mean | 40.94 | 40.92 | 41.07 |
| age median | 39.00 | 39.00 | 39.00 |
| age p95 | 59.00 | 59.00 | 59.00 |
| age p99 | 71.00 | 69.01 | 72.00 |
| age KS distance vs reference | 0.0000 | 0.0159 | 0.0184 |
| balance mean | 1362.27 | 5943.30 | 1416.48 |
| balance median | 448.00 | 454.00 | 491.50 |
| balance p95 | 5768.00 | 53499.00 | 5747.05 |
| balance p99 | 13164.90 | 91717.24 | 12835.93 |
| balance KS distance vs reference | 0.0000 | 0.0871 | 0.0758 |
| Outcome yes rate | 11.6985% | 10.3000% | 11.1000% |

## Interpretation

- Compare V3 with V2; do not assume V3 is better before reviewing results.
- KS distances describe marginal distribution differences, not privacy.
- No acceptance thresholds are defined; no utility PASS is assigned.
- No formal privacy guarantee is provided.
- COBOL compatibility remains untested.
