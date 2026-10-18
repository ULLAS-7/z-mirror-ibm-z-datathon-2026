# Z-Mirror implementation and evidence status

Status: 18 October 2026. This report distinguishes verified prototype facts from unresolved work.

## Verified on LinuxONE
- The project ran in a Docker/Jupyter workflow on LinuxONE Community Cloud, s390x architecture.
- Synthetic generator regression suite: 8/8 tests passed when run independently.
- Extended validator test script: 18/18 scenarios passed when run independently. It is a standalone script, not a standard `unittest` module; importing it through automatic discovery produces `SystemExit`, so run it directly.
- The notebook's Generator V2 output reported 45,211 public-reference rows, 1,000 generated rows, 124 aggregate cells, seed 42, and a manifest hash.
- The demonstrated fixed-width sample contained five 12-character records.
- GnuCOBOL 3.1.2 was installed on the LinuxONE host.

## Open / not yet established
- A V2-vs-reference utility evaluation with decision thresholds has not been confirmed. The saved older V1 comparison showed age KS distance 0.3361, balance KS distance 0.7511, reference yes-rate 11.7%, generated yes-rate 43.9%, and an absolute outcome-rate gap of 32.2 percentage points. This is evidence of material drift for that older candidate, not V2.
- Empirical privacy-risk checks are not yet implemented/verified. Aggregate generation alone does not establish anonymity or privacy safety.
- GnuCOBOL was found on the host. A small format-smoke-test source file is included, but its remote compile/run result has not yet been recorded here. Compiler installation alone is not compatibility evidence.
- No formal differential-privacy guarantee, legal compliance, or production readiness is claimed.

## Test commands
Run in the project root with Python 3.12+:

```bash
python -m unittest discover -s tests -p 'test_generate_synthetic.py' -v
python tests/test_validator_extended.py
python -m unittest discover -s tests -p 'test_evaluate_utility.py' -v
```

Run the validator fixture (this writes `data/cobol_input.dat` and `reports/validation_report.txt`):

```bash
python src/validate_candidate.py
```

The generator is an educational prototype. It uses hand-defined parameters and is not a fitted model. It must not be described as automatically anonymous or production synthetic-data software.
