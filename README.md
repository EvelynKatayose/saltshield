# SaltShield Wachusett pilot

This package contains official public GIS extracts, reproducible road-length
analysis, six explicitly simulated investment alternatives, an exact budget
comparison, figures, and a standalone interactive HTML results report.

## Run

Use Python 3.11 or newer in a virtual environment. The analysis itself is offline.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_analysis.py
python build_report.py
```

Open `results/SaltShield_Wachusett.html`. For a fresh source snapshot, run
`python download_data.py` first while connected to the internet. Downloads use
official ArcGIS services; no API keys are needed for these public queries.

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
