# Evidence summary (known results)

| Check | Current result | Notes |
|---|---|---|
| Generator tests | PASS, 8/8 | Ran independently on LinuxONE Docker container. |
| Extended validator scenarios | PASS, 18/18 | Run `python tests/test_validator_extended.py`; don't import as a unittest module. |
| Generator V2 creation | Reported complete | 1,000 rows; 124 aggregate cells; seed 42; manifest hash emitted in notebook. |
| Fixed-width sample format | PASS for sample | Five inspected records, 12 characters each. |
| V2 statistical utility | INCONCLUSIVE | Need a V2-vs-reference report and defined thresholds. |
| Empirical privacy assessment | NOT VERIFIED | No formal privacy guarantee. |
| GnuCOBOL consumer test | NOT RUN / NOT VERIFIED | Compiler installed; compile and execute a real consumer before claiming compatibility. |

Older V1 utility comparison in the notebook: age KS 0.3361; balance KS 0.7511; reference `yes` rate 11.7%; V1 candidate `yes` rate 43.9%; gap 32.2 percentage points. These results are not V2 results.
