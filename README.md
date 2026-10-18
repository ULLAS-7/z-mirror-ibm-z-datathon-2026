# Z-Mirror: Evidence-Gated Synthetic Data for IBM Z

**Theme:** AI Secured: Innovation Without Exposure
**Status:** Experimental prototype; release not approved.

Z-Mirror explores generating synthetic test data and evaluating whether a candidate is ready for downstream testing. Successful generation does not automatically authorize release.

## Current capabilities

- Seeded experimental synthetic-data generation.
- SHA-256 artifact manifests.
- Schema, integrity, and utility checks.
- An explicit release gate that can withhold approval.
- Empirical exact-overlap, unique-record-match, and nearest-neighbour probes.
- Fixed-width validation components for a COBOL-oriented workflow.
- JSON and Markdown evidence reports.

## Recorded LinuxONE verification

These results were recorded on 18 October 2026; rerun the tests to verify the current checkout.

| Check | Recorded result |
|---|---|
| Generator tests | 8/8 passed |
| Extended validator scenarios | 18/18 passed |
| Release-gate unit tests | 9/9 passed |
| Privacy-probe unit tests | 15/15 passed |
| V3 integrity checks | 10/10 passed in recorded verification |
| V3 utility against illustrative targets | Meets configured targets |
| Privacy probe | 2 PASS, 1 INCONCLUSIVE |
| Privacy assurance | NOT ESTABLISHED |
| Actual COBOL execution | NOT VERIFIED |
| Release decision | NOT APPROVED |

## Experimental utility comparison

Measurements from one experiment with 1,000 records per candidate:

| Metric | Reference | V2 | V3 |
|---|---:|---:|---:|
| Balance mean | 1,362.27 | 5,943.30 | 1,416.48 |
| Balance 95th percentile | 5,768.00 | 53,499.00 | 5,747.05 |
| Balance KS distance | 0.0000 | 0.0871 | 0.0758 |
| Age KS distance | 0.0000 | 0.0159 | 0.0184 |
| Outcome yes rate | 11.6985% | 10.3000% | 11.1000% |
| Absolute outcome-rate gap | — | 1.3985 pp | 0.5985 pp |

V3 improves selected balance and outcome-rate measurements in this experiment. Its age KS distance is slightly worse than V2. These results do not establish overall utility or production fitness. Thresholds are illustrative prototype targets, not approved acceptance criteria.

## Privacy findings and limitations

The V3 empirical probe reported:
- Exact-overlap rate: 0.297 against an exploratory baseline limit of 0.430.
- Unique-record-match rate: 0.143 against an exploratory baseline limit of 0.231.
- Nearest-neighbour check: INCONCLUSIVE because the baseline fifth-percentile distance was zero for the selected fields.
- Overall: two checks passed and one was inconclusive.

The reference dataset is public, only selected fields are evaluated, and the baseline is not a confidential-data holdout. These checks do not establish anonymity, resistance to every inference attack, or differential privacy. The release gate remains blocked pending privacy assurance and actual COBOL execution evidence.

## IBM LinuxONE context

Development evidence was recorded from IBM LinuxONE Community Cloud using the observed `s390x` environment. Platform use alone does not demonstrate integration with an enterprise COBOL application.

## Reproduction

Run from the repository root in a Python environment with the required dependencies installed:

```bash
python -m unittest discover -s tests -p "test_generate_synthetic.py" -v
python tests/test_validator_extended.py
python -m unittest discover -s tests -p "test_release_gate.py" -v
python -m unittest discover -s tests -p "test_privacy_probe.py" -v
python src/release_gate.py
python privacy_probe.py --reference data/reference_candidate.csv --candidate data/generated_candidate_v3.csv --output reports/privacy_probe_v3_20261018.json
```

Some checks may require additional dependencies or arguments depending on the local environment. The recorded LinuxONE results above are not a guarantee that these commands will pass on every machine.

## Important artifacts

- `src/`: generator and validation implementation.
- `tests/`: regression and scenario tests.
- `data/`: reference and generated candidate data, manifests, and source attribution.
- `reports/`: recorded test logs, utility comparisons, privacy findings, and release-gate evidence.
- `exports/`: packaged evidence bundle, when present.

## Future work

- Obtain stakeholder-approved utility and privacy criteria.
- Evaluate against an appropriately authorized confidential-data holdout.
- Investigate the inconclusive nearest-neighbour result.
- Verify fixed-width output using an actual COBOL compiler/runtime and documented test cases.
- Re-run all checks and update the evidence bundle after changes.

**Conclusion:** Z-Mirror demonstrates an evidence-gated prototype workflow. Privacy assurance and COBOL execution remain unverified, so the current candidate is not approved for release.
