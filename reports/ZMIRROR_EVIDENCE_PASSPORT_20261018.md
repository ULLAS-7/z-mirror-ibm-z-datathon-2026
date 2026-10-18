# Z-Mirror — Evidence Passport

Generated (UTC): 2026-10-18T07:41:25.070011+00:00

## Project

Z-Mirror is an experimental aggregate/histogram-based synthetic-data
prototype with manifests, validation tests, and utility comparisons.
It is not a certified privacy mechanism.

## Recorded engineering evidence

- Generator regression tests: 8/8 passed in a previous run.
- Validator scenarios: 18/18 passed in a previous run.
- Current artifact-integrity checks: 10/10 passed during passport generation.
- V3 contains 1,000 rows; its CSV hash matches the manifest.
- V3 manifest reference hash matches the current reference CSV.

## V2 versus V3

| Metric | Reference | V2 | V3 |
|---|---:|---:|---:|
| Balance mean | 1362.27 | 5943.30 | 1416.48 |
| Balance 95th percentile | 5768.00 | 53499.00 | 5747.05 |
| Balance KS distance | 0.0000 | 0.0871 | 0.0758 |
| Age KS distance | 0.0000 | 0.0159 | 0.0184 |

- Outcome-rate gap: V2 1.3985 pp; V3 0.5985 pp.
- V3 improved the measured balance KS distance and balance-tail alignment in this experiment.
- Age KS distance is slightly worse in V3 than V2.
- No utility acceptance thresholds have been defined, so neither candidate receives a utility PASS.

## Release decision

| Gate | Status |
|---|---|
| Listed artifact-integrity checks | PASS — 10/10 |
| Generator tests | PASS — 8/8 previously recorded |
| Validator scenarios | PASS — 18/18 previously recorded |
| Utility acceptance | INCONCLUSIVE |
| Privacy assurance | NOT ESTABLISHED |
| Actual COBOL execution | NOT VERIFIED |
| Production readiness | NOT ESTABLISHED |

## SHA-256

- Reference: `176e520cbefc564170872bea12a1886982430471ce25c1298595a6bf27ce0810`
- V2: `9c85fd9e7edffef1ebdb5898207d29906d508672b8a9ea349f1f56597c5f42ce`
- V3: `41334f9fa5f2ec0847edc09135ead30a634856a9b3d7c76b20a49657eb4203b7`

## Limitations

Distribution similarity is not a privacy score or anonymity guarantee.
Test totals above were recorded in previous runs and are not rerun here.
COBOL execution has not been demonstrated by the current evidence.
Production suitability requires defined acceptance thresholds, additional
testing, and a documented privacy-risk assessment.
