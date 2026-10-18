# COBOL fixed-width format smoke test

This small GnuCOBOL program reads the generated sample file and checks that each line has exactly 12 characters matching the demonstrated layout: 3 numeric age characters, a plus/minus sign, 7 numeric balance characters, and a final `Y`/`N` outcome code.

Run from the repository root on LinuxONE after `data/cobol_input.dat` has been created by `python src/validate_candidate.py`:

```bash
cobc -x -free -o /tmp/zmirror-format-smoke tests/cobol_format_smoke.cbl
/tmp/zmirror-format-smoke data/cobol_input.dat
```

A passing result verifies this format smoke test only. It does not establish compatibility with a production COBOL program, an actual copybook, EBCDIC deployment, or business logic.
