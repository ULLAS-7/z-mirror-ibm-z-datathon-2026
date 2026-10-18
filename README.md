# Z-Mirror — IBM Z Datathon 2026

**Evidence-gated synthetic test data for COBOL-oriented workflows.**

Z-Mirror is a prototype for generating candidate synthetic records, validating a constrained CSV schema and fixed-width output, tracking run provenance with a SHA-256 manifest, and measuring selected utility properties before a release decision. It aims to make generation auditable rather than assume that generated data is automatically private or useful.

## Demonstrated environment
- IBM LinuxONE Community Cloud, `s390x`
- Python 3.12 / JupyterLab in Docker
- GnuCOBOL 3.1.2 available on the host (an end-to-end COBOL consumer test remains pending)
- Public UCI Bank Marketing reference dataset; full dataset is not bundled

## Notebook packaging note
The recovered runtime notebook `zmirror_pipeline.ipynb` lives in the submitter's Windows Downloads folder and is not included in this generated source bundle. If it is appropriate to publish, copy the actual notebook into the repository after checking it for access tokens, private keys, credentials, and sensitive output. The notebook contains the recorded Generator V2 run; this bundle's standalone `generate_synthetic.py` is the earlier V1 demo generator. Do not claim V2 is reproducible from this repository until its code is included and reviewed.

## Current evidence
- Generator tests: **8/8 passed**
- Validator scenarios: **18/18 passed**
- Notebook Generator V2 reported 45,211 reference rows, 1,000 generated rows, 124 aggregate cells, seed 42 and a manifest hash.
- V1's earlier utility comparison showed material distribution/outcome-rate drift; do not use it as a V2 result.
- V2 utility threshold comparison, empirical privacy-risk assessment, and end-to-end COBOL execution are still open. See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).

## Run tests
Use Python 3.12+ from this repository root:

```bash
python -m unittest discover -s tests -p 'test_generate_synthetic.py' -v
python tests/test_validator_extended.py
python -m unittest discover -s tests -p 'test_evaluate_utility.py' -v
```

The validator's fixture `data/candidate.csv` contains five demonstration records. To validate and emit a 12-character fixed-width sample:

```bash
python src/validate_candidate.py
```

To generate a candidate and manifest:

```bash
python src/generate_synthetic.py --rows 1000 --seed 42 --output data/generated_candidate.csv
```

To evaluate utility, first download the public UCI Bank Marketing data from the [official repository](https://archive.ics.uci.edu/dataset/222/bank+marketing), extract `bank-full.csv` into `data/source/`, normalize it, and compare:

```bash
python src/prepare_reference.py --input data/source/bank-full.csv --output data/reference.csv
python src/evaluate_utility.py --reference data/reference.csv --candidate data/generated_candidate.csv --output reports/utility_evaluation.json
```

The evaluator measures selected properties and does not make a PASS/FAIL utility decision unless policy thresholds are independently defined. Exact tuple overlap against a public reference is not a privacy-risk score.

## Limitations / safe claims
- This is a prototype, not a production synthetic-data product.
- The standalone generator uses hand-defined parameters and does not, by itself, learn from confidential data.
- No differential privacy, formal anonymity, legal-compliance, or production-readiness guarantee is claimed.
- Empirical privacy-risk checks remain open. A GnuCOBOL fixed-width format smoke test is included in `tests/cobol_format_smoke.cbl`; run it on LinuxONE before claiming the format gate passed. It is not a substitute for a production copybook or business-program integration test.

## Resources and attribution
- UCI Bank Marketing, Moro, Rita & Cortez (2014), DOI: https://doi.org/10.24432/C5K306; CC BY 4.0 attribution is required for adapted data. [Dataset page](https://archive.ics.uci.edu/dataset/222/bank+marketing)
- Python: https://www.python.org/
- Project Jupyter: https://jupyter.org/
- Docker/Moby: https://github.com/moby/moby
- GnuCOBOL: https://gnucobol.sourceforge.io/
- LinuxONE Community Cloud: https://linuxone.cloud.marist.edu/#/login

## Project documents
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md)
- [`reports/evidence_summary.md`](reports/evidence_summary.md)
