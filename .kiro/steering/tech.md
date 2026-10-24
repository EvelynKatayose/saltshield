---
inclusion: always
---

# SaltShield — Technology & Build

## Stack

- **Analysis (Python 3.11+):** numpy, scipy (HiGHS MILP), shapely, pyproj,
  matplotlib, beautifulsoup4. All analysis runs offline from cached data.
- **Browser (vanilla JavaScript):** no UI framework, no remote fonts, no runtime
  network calls. Canvas 2D drives the hero snow and the snow/salt/water
  illustration (`winter_scene.js`).
- **Output:** a single self-contained `results/SaltShield_Wachusett.html` with
  all CSS and JS inlined, staged to `docs/` for GitHub Pages.

## Source layout (what feeds the final page)

- `report_template.html` — outer shell with placeholder anchors
  (`__EXPERIENCE_PANEL__`, `__WORKSPACE_CSS__`, `__SOLVER_JS__`, etc.).
- `experience.html` — immersive story markup (build fills `__TOTAL_ROADS__` and
  the two `__EXPERIENCE_MAP_*__` SVG placeholders).
- `experience.css` + `experience_live.css` — presentation layer. `experience_live.css`
  is concatenated **after** `experience.css`, so it overrides at equal specificity.
- `experience.js` — experience interactivity (map cell colors, compare slider,
  parallax, animation loop). `winter_scene.js` — canvas artwork.
- `workspace.css` / `workspace.js` and the phase panel templates/scripts drive
  the four workspace sections.

## Build pipeline (run in order)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_analysis.py
python build_evidence.py
python phase2_model.py
python prepare_parameters.py
python planning_v1.py
python build_weather.py
python spatial_priority.py
python joint_planning.py
python build_report.py   # assembles results/SaltShield_Wachusett.html
python build_site.py     # stages the public site into docs/
```

`build_report.py` refuses to run unless the phase JSON outputs
(`planning_v1.json`, `phase2_analysis.json`, `spatial_priority.json`,
`weather_context.json`, `joint_planning.json`) exist and match their source
hashes. To iterate on visuals only, edit the source files, then re-run
`build_report.py` and `build_site.py`.

## Tests

```bash
python -m unittest test_phase2 test_phase3 test_planning_v1 test_joint_planning -v
node test_ui.cjs
node test_planning.cjs
node test_joint.cjs
node test_joint_brief.cjs
node test_experience.cjs
node test_demo.cjs
node test_routing.cjs
```

Node tests execute the exact scripts embedded in the shipped report, so always
re-run `build_report.py` before running them after a source change.

## Deployment

GitHub Pages serves `/docs` from `main`. Routing config lives in
`deployment/site.json` (`base_path: /saltshield/`). Do not change the domain,
`expected_url`, or `base_path` — the build validates that hosting URL and
routing base agree.
