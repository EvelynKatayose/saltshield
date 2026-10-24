---
inclusion: always
---

# SaltShield — Project Structure & Conventions

## Top-level layout

```
saltshield/
├── .kiro/                     # Kiro steering, specs, and hooks
├── assets/                    # Hero image + visual source manifest
├── data/
│   ├── raw/                   # Original GeoJSON + download metadata
│   ├── processed/             # Analysis-ready geometry (EPSG:26986)
│   ├── parameters/            # Editable simulated inputs (CSV/JSON)
│   ├── evidence/              # Frozen DCR funding source + manifest
│   └── weather/               # Five winters of ERA5 context
├── deployment/                # site.json (GitHub Pages routing)
├── docs/                      # Staged public site (build_site.py output)
├── results/                   # Analysis outputs + shipped HTML report
├── *.py                       # Analysis + build scripts
├── *.js                       # Browser solver, UI, and canvas art
├── *.html / *.css             # Report template, panels, styles
└── test_*.{py,cjs}            # Python unit tests + Node parity/UI tests
```

## Key conventions

- **Measured vs. simulated.** Never blur the line. Geometry and lengths are
  measured and conserved; prices, reduction rates, baselines, coverage and
  capacities are simulated and must be labeled. UI copy marks live edits as
  "unverified scenario inputs."
- **Self-contained output.** All CSS/JS is inlined into the single report HTML
  by `build_report.py`. Edit the root source files, never the generated
  `results/*.html` or `docs/*.html` by hand.
- **Experience vs. workspace separation.** The immersive story (`x-*` classes)
  is isolated from the planning workspace. Snow/salt/water artwork is
  illustrative only and must never feed the quantitative model — the test
  `snow_salt_and_water_interactions_do_not_change_quantitative_inputs` enforces this.
- **Integrity first.** Outputs carry source SHA-256 hashes and parameter
  fingerprints. Stale or tampered inputs are rejected, not silently used.
- **Styling.** The experience layer uses the `x-` class prefix and a mint/teal
  accent palette. Prefer appending overrides to `experience_live.css` (which
  loads last) over editing the minified `experience.css` base.
- **CSS/JS style.** The shipped assets are intentionally dense/minified in one
  or few lines. Keep edits consistent with the surrounding file.

## After any source edit

1. Re-run `python build_report.py` then `python build_site.py`.
2. Re-run the relevant `node test_*.cjs` (they load the rebuilt report).
3. Verify `docs/index.html` carries `saltshield-base content="/saltshield/"`.
