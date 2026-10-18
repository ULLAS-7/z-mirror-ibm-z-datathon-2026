# Z-Mirror Automated Release Gate

Generated UTC: 2026-10-18T09:55:06.369416+00:00

- Integrity: **PASS**
- V3 utility against illustrative targets: **MEETS_ILLUSTRATIVE_TARGETS**
- Privacy assurance: **INCONCLUSIVE_NOT_ESTABLISHED**
- COBOL execution: **NOT_VERIFIED**
- Overall release: **NOT_APPROVED_PRIVACY_AND_COBOL_CHECKS_PENDING**

## Integrity checks

- PASS: reference_schema_valid
- PASS: v2_schema_valid
- PASS: v3_schema_valid
- PASS: v3_has_1000_rows
- PASS: v3_ids_unique
- PASS: v3_hash_matches_manifest
- PASS: reference_hash_matches_manifest
- PASS: v3_age_within_reference_range
- PASS: v3_balance_within_reference_range

## V2 versus V3

| Measure | V2 | V3 |
|---|---:|---:|
| Age KS distance | 0.0159 | 0.0184 |
| Balance KS distance | 0.0871 | 0.0758 |
| Balance mean | 5943.30 | 1416.48 |
| Balance 95th percentile | 53499.00 | 5747.05 |
| Outcome yes-rate gap (pp) | 1.3985 | 0.5985 |

## V3 utility target checks

- PASS: age_ks_within_target
- PASS: balance_ks_within_target
- PASS: balance_mean_error_within_target
- PASS: balance_p95_error_within_target
- PASS: outcome_gap_within_target

## Release policy

The configured numerical targets are illustrative prototype targets, not formally approved acceptance criteria and not privacy thresholds.
The gate deliberately does not approve release while privacy assurance and actual COBOL execution remain unverified.

No anonymity, differential privacy, or production-readiness guarantee is made.
