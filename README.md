# SaltShield Wachusett pilot

This package contains official public GIS extracts, reproducible road-length
analysis, six explicitly simulated investment alternatives, exact budget
comparisons, five winters of regional weather context, spatial coverage
allocation, figures, and a standalone interactive HTML results report.

## Run

Use Python 3.11 or newer in a virtual environment. The analysis itself is offline.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_analysis.py
python build_evidence.py
python phase2_model.py
python build_weather.py
python spatial_priority.py
python build_report.py
python -m unittest test_phase2 test_phase3 -v
node test_ui.cjs  # optional Node.js verification of embedded report scripts
```

Open `results/SaltShield_Wachusett.html`. For a fresh source snapshot, run
`python download_data.py` first while connected to the internet. Downloads use
official ArcGIS services; no API keys are needed for these public queries.

To refresh the historical funding source, run `python download_evidence.py`,
then rebuild the evidence, phase 2 analysis and report. Extraction deliberately
stops if the frozen 18-record source changes, so new entries require review.

## Phase 2 evidence and configurable planning

The report now includes 13 official historical awards for the three study towns
from FY2021 through FY2026, totaling $188,251 in grants. The saved DCR webpage,
its checksum, exact fiscal-year/town locators, and structured records are in
`data/evidence`. Holden has five records totaling $84,000; Sterling has four
totaling $66,168; West Boylston has four totaling $38,083.

Grant awards are not equipment prices. The Holden FY2023 entry separately
describes a $150,000 brine production/storage project and a $20,000 grant.
Neither amount is treated as a current quote. Prior funded purposes do not
verify installation, spare capacity, current availability, or road coverage.
All six hypothetical future investments retain simulated prices and effects.

The offline editor can change each project's capital cost, coverage fraction,
and enabled status, together with baseline intensity and effect scenario.
Coverage is a uniform share of that project's mapped eligible road sections,
not measured route or fleet capacity. Changing coverage affects benefits but
does not automatically scale a fixed equipment purchase cost.

Five comparisons are available: independent budgets, pooled budgets, pooled
with at least one selected project per town, pooled at the independent plan's
actual spending, and that same-spend case with the participation constraint.
Infeasible participation requirements are reported explicitly, not converted
into a zero-cost or empty feasible plan. Selecting a project in every town is
a participation rule, not proof of environmental or distributive equity.

At the original $45,000 actual spending, unconstrained pooling gives 52.56
simulated tonnes of avoided Zone A application while selecting projects in
only two towns. Requiring one project in every town returns 41.54 tonnes.
This exposes a resource-allocation tradeoff rather than claiming free gains.

Scenario JSON can be exported and re-imported. Only operational controls are
imported; source geometry and evidence stay fixed. Imports require a matching
evidence checksum and the original project ID set. Current numeric inputs are
validated, and invalid inputs hide results to avoid displaying stale outputs.
The report checks that its phase 2 results match the underlying analysis file.

`results/phase2_policy_comparison.csv` contains 120 rows across eight budgets,
three effect scenarios and five funding rules. The Python tests cover evidence
extraction, missing costs, project enablement, participation infeasibility,
coverage, budget constraints and zero-effect behavior. Browser/Python agreement
is recorded separately in `results/phase2_validation.json` after verification.
With Node.js installed, run `node test_ui.cjs` for offline UI-state validation
and scenario import/export round-trip tests. These are unit tests, not a
substitute for visual browser inspection.

## English planning workspace

The standalone report is now an English application with four sections:
Overview, Investments, Road Coverage, and Evidence. A system-font interface,
restrained colors, translucent navigation, compact controls and light/dark
appearance replace the earlier long-form report layout. Layouts adapt for
narrow screens, navigation supports arrow keys, and reduced-motion preferences
are respected. The app uses no remote fonts, UI framework, model calls or
runtime network requests.

Overview includes a live decision brief. Choose independent funding, unrestricted
pooling, or pooling with a project in every town. The brief uses the current
equipment inputs and separately reports the current spatial coverage case.
It includes an equal-actual-spending check and explicit assumptions. Download
the brief as standalone English HTML, or use **Print brief** to print only the
brief from any section. Infeasible selected policies disable brief export;
invalid inputs clear stale results and disable both printing and download.

Valid controls are saved automatically on the current browser/device through
localStorage. A reload restores costs, coverage, enablement, budget, baseline,
effect scenario and spatial case only after full validation against the saved
evidence fingerprint and fixed project IDs. Source geometry and effect rates
cannot be changed by a draft. Invalid in-progress edits do not overwrite the
last valid draft. A rejected draft falls back to defaults with a status message.
Where browser storage is unavailable, the existing JSON scenario export/import
remains available. Local files and a local HTTP preview use separate browser
storage origins; drafts are not synced across devices.

Edit `workspace.css`, `workspace.js`, `report_template.html`, or the English
panel templates, then rerun `python build_report.py` to embed every asset into
`results/SaltShield_Wachusett.html`. The generated file remains self-contained.
`node test_ui.cjs` executes the exact embedded scripts and covers navigation,
appearance, exports, brief synchronization, draft restoration, evidence mismatch
rejection and English-only report output, alongside the existing planner tests.
This redesign does not change the geographic inventory or optimization model.

## Phase 3 regional context and spatial coverage

Five complete winters, 2021–2022 through 2025–2026, have been retrieved from
Open-Meteo's Historical Weather API with `models=era5`. Each season is November
1 through March 31 in America/New_York time. The snapshot contains 18,144 hours
across 756 local calendar days, with no missing values in the four requested
variables: 2 m air temperature (C), precipitation (mm), snowfall (cm), and 10 m
wind speed (m/s). UTC epochs preserve both occurrences of a repeated daylight
saving time hour. Missing values, if present in a future snapshot, remain
missing and suppress affected totals; they are not filled with zero.

The requested reference is the projected watershed centroid, approximately
42.404817 N, 71.811495 W. The returned ERA5 grid coordinate is 42.5 N,
71.75 W. ERA5 is a coarse 0.25-degree regional reanalysis, not local road-sensor
observations. Default API elevation adjustment is retained and the response
elevation is recorded. This reference cannot resolve local pavement conditions.
Precipitation includes rain and snow water equivalent; snowfall depth is a
separate model variable and must not be added to precipitation.

The descriptive "cold-wet" count uses air temperature <= 2 C and preceding-hour
precipitation >= 0.1 mm. It is not a road icing diagnosis or calibrated salt
demand estimate. Weather is context only and does not change the phase 2 salt
baseline, investment effects, or spatial objective. Attribution: ERA5 /
Copernicus Climate Change Service via Open-Meteo; Open-Meteo data CC BY 4.0.
Documentation: https://open-meteo.com/en/docs/historical-weather-api

`data/weather` holds five raw responses, exact request URLs, retrieval dates,
response coordinates/units, SHA-256 checksums, and hourly/daily CSVs. Refresh
online with `python download_weather.py`; then run `python build_weather.py`.
Cached analysis is fully offline. Keep all weather snapshots and their manifest
together; the report rejects a changed manifest or mismatched raw snapshot.

The spatial module partitions eligible municipal paved roads into 173 occupied
1 km planning cells in EPSG:26986. Cell footprints are clipped to the study
town/watershed masks. Each source road piece is assigned only once at grid
boundaries, and per-town eligible, protected, and Zone A lengths are conserved.
The original source-record overlap described below remains in summed lengths.
`data/processed/planning_cells.geojson` contains the cell polygons and metrics.

Each town is assigned an illustrative coverage capacity of 25%, 50%, 75%, or
100% of its eligible centerline length. Four methods share that same per-town
capacity: uniform fractional coverage, a Zone-A-ratio greedy whole-cell choice,
an exact binary knapsack solved with SciPy/HiGHS, and a fractional-knapsack
upper bound. Integer solves require a certified optimal result with zero
relative gap. Grid size is a modeling choice, and no grid-size robustness claim
is made. Zero-benefit cells can be omitted; full-capacity scenarios cover all
cells. Unused capacity is displayed rather than assumed spent.

At 25% capacity, the three towns have 73.81 km of aggregate capacity. The whole
cell optimum covers 73.70 km of roads including 39.56 km in Zone A; the uniform
fractional baseline covers 20.77 km in Zone A. This is a spatial-targeting
comparison, not a measured salt saving. The greedy whole-cell heuristic is
already close to the optimum; the larger difference against uniform coverage
must not be attributed solely to using an integer solver. Uniform and upper
bound cases allow partial cells and are not executable whole-cell plans.

The spatial planner is separate from the equipment budget editor. It does not
convert geometry coverage into new avoided-application tonnes, equipment costs,
route schedules or measured fleet capacity. Grid cells are not validated snow
maintenance routes. Travel links, concurrent weather response, staffing,
storage, safety service requirements and equipment sharing logistics remain
unmodeled. The report provides a case selector, a shaded map, side-by-side
method comparisons, and downloadable cell allocations.

Rebuild with `python spatial_priority.py`. The 12 town/capacity cases and 48
method rows are in `results/spatial_priority.json` and
`results/spatial_policy_comparison.csv`; all case allocations are in
`results/spatial_cell_allocations.csv`. The report checks both source geometry
and planning-cell checksums. Tests compare a small integer problem against
exhaustive enumeration, verify real-data capacity/length bounds, preserve DST
hours, reject weather corruption and execute the embedded HTML scripts.
Validation summary: `results/phase3_validation.json`.

## Real data and geographic scope

The four logical layers are MassGIS/MassDOT roads, official municipalities,
MassDEP surface-water supply watersheds, and MassDEP protection zones A/B/C.
Original GeoJSON is in `data/raw`; processing outputs are in `data/processed`.
The road extract is the three-town bounding-box subset, not a statewide copy.
All data were retrieved during this task; the exact request metadata, source
domains, download counts, and input SHA-256 hashes are included.

The watershed is specifically MWRA Wachusett Reservoir, SOURCE_ID 6000000-01S.
The source has another supplier record for the same reservoir and a different
Wachusett Lake record. These are not added to the selected watershed.

The study is only the Holden, Sterling, and West Boylston portions of that
watershed. It does not represent the entire watershed or all affected residents.

## Measurement rules

Lengths are measured from source geometry in NAD83 Massachusetts Mainland,
EPSG:26986, in meters and reported as mapped centerline kilometers. They are not
lane-kilometers, official certified road mileage, or contracted plowing mileage.
Town borders are intersected geometrically. Exact shared-border linework is
assigned once, preferring the source town attribute. Zones are partitioned
A first, then B minus A, then C minus A/B. Unmatched sections remain UNZONED;
they are not silently assigned to C or included in protected-road totals.

Source road records contain approximately 78.8 meters of coincident linework
within the study (see validation.json for the exact diagnostic). Raw record
lengths retain their source classifications rather than arbitrarily assigning
conflicting jurisdictions. This small source overlap remains in record-summed
lengths; unique dissolved linework is slightly shorter. The report gives this
limitation explicitly. Town/zone segmentation does not introduce extra length.

Jurisdiction labels come directly from the service's coded domain. Code 2 is
City or Town accepted road; code 1 is MassDOT; code 0 is Unaccepted by city or
town. Code 0 is not relabeled private. Missing jurisdiction stays unknown.
These are source jurisdiction classes, not verified snow-maintenance contracts.

Only accepted municipal roads with a known paved surface code 3 through 9 and
not a bicycle/pedestrian facility enter the hypothetical equipment scenario.
State roads, unaccepted roads, unknown jurisdiction and unknown/unpaved surfaces
remain visible in the measured inventory but outside investment coverage.
NUM_LANES and OPP_LANES are preserved without guessing how to combine them.

## Explicitly simulated parameters

Uniform baseline: 5 tonnes of applied salt per mapped centerline km per season.
This is a round demonstration input, not a measured or recommended dose.

Each town has two mutually exclusive hypothetical packages covering all its
eligible road sections in the selected watershed:

* CAL: calibration/control package, $15,000, central reduction 10%, range 5–15%.
* BRINE: brine/pre-wetting package, $30,000, central reduction 25%, range 15–35%.

Prices, reduction percentages, full-road coverage, fleet adequacy, and baseline
salt intensity are simulated. No vendor quote or deployment feasibility is
asserted. One-time capital costs are compared; operating costs, equipment life,
material purchases and maintenance savings are not modeled.

## Budget comparison

Both modes have a $75,000 aggregate capital ceiling. Independent mode gives
each town a nontransferable $25,000 ceiling. Pooled mode permits transfers.
Both modes use the same projects, parameters, scope and objective: maximize
simulated avoided application on Zone A municipal paved roads. All 27 possible
none/CAL/BRINE combinations are enumerated exactly, with at most one package
per town. Ties prefer more avoided application across all zones, then lower cost.

Equal budget ceilings can produce unequal actual expenditures. The default
independent mode cannot buy a $30,000 package with a $25,000 town ceiling. The
report explicitly separates this unspent-capital effect from resource
reallocation by also comparing pooled investment at the independent plan's
actual $45,000 spending. That equal-spend case can leave one town unfunded;
the report exposes the allocation rather than describing it as equitable.

The objective is a planning proxy for avoided salt application near protected
waterways, not chloride concentration, delivered pollutant load, verified safe
road service, a causal impact estimate, or a pollution-responsibility finding.
The optimization is operations research, not a trained ML model or an LLM agent.

## Results and validation

CSV tables describe town lengths, jurisdiction lengths, zone breakdowns,
equipment options and budget sensitivity. JSON includes the full comparison,
effect sensitivity, assumptions and validation results. Checks cover complete
download counts, source IDs, unique output IDs, length conservation, disjoint
zone accounting, budget feasibility, project exclusivity, zero budgets, zero
benefits, and pooled feasibility dominating independent mode under its relaxed
funding constraints. No field savings or water-quality improvements are claimed.

## Sources

* https://www.mass.gov/info-details/massgis-data-massgis-massdot-roads
* https://www.mass.gov/info-details/massgis-data-municipalities
* https://www.mass.gov/info-details/massgis-data-surface-water-supply-watersheds
* https://www.mass.gov/info-details/massgis-data-surface-water-supply-protection-areas-zone-a-b-c

To move from a demonstrator to deployment, obtain town equipment inventories,
road service requirements, actual salt application logs, vendor costs, fleet
capacity and project-specific effects. Water concentration forecasts additionally
need calibrated transport and flow data plus independent monitoring validation.
