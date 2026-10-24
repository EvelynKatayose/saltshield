---
inclusion: always
---

# SaltShield — Product Overview

SaltShield is a reproducible, offline-first planning tool for a three-town winter
road-salt pilot in the Wachusett Reservoir watershed (Holden, Sterling, and West
Boylston, Massachusetts). It connects official public GIS road inventory to a
practical question: where can a limited winter-equipment budget do the most good
for a shared drinking-water source?

## Who it is for

- Town public-works planners comparing independent vs. shared (pooled) budgets.
- Watershed stakeholders who need a transparent, inspectable decision brief.
- Presenters who need a repeatable three-minute demo (`?demo=1`).

## What it delivers

- An immersive `#experience` landing story (hero, snow/salt/water illustration,
  live budget comparison map) that leads into a four-section planning workspace:
  Overview, Investments, Road Coverage, Evidence.
- Exact budget optimization across six explicitly simulated equipment options.
- Spatial whole-cell coverage allocation over 173 one-kilometer planning cells.
- Five winters of regional weather context (ERA5 via Open-Meteo).
- A self-contained, offline HTML report and a publishable decision brief.

## Public surfaces

- Website: https://evelynkatayose.github.io/saltshield/
- Demo: https://evelynkatayose.github.io/saltshield/?demo=1
- Presenter walkthrough: https://evelynkatayose.github.io/saltshield/demo/

## Guiding principles

- **Honest framing.** Geometry is measured; investment inputs, prices, reduction
  rates and capacities are explicitly simulated and labeled as such. The tool
  never claims verified water-quality improvements or field savings.
- **Reproducible and offline.** No remote fonts, UI frameworks, model calls, or
  runtime network requests in the shipped report.
- **Inspectable.** Source hashes, provenance, and measurement rules travel with
  every output; stale or tampered inputs are rejected rather than silently used.
