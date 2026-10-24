# Requirements — Experience Page Visual Enhancement

## Introduction

The immersive `#experience` landing page is the first thing visitors and demo
audiences see. This spec captures the requirements for strengthening its visual
appeal and data visualization without altering the quantitative planning model
or the separation between illustrative artwork and measured results.

## Requirements

### Requirement 1 — Richer visual depth

**User Story:** As a visitor, I want the landing experience to feel polished and
premium, so that I trust the tool and want to keep exploring.

#### Acceptance Criteria

1. WHEN the hero renders THEN the headline SHALL use a gradient accent and a
   subtle glow, and buttons SHALL use layered depth (gradient + shadow).
2. WHEN a section with stat numbers or accent metrics renders THEN key figures
   SHALL use gradient text fills consistent with the mint/teal palette.
3. WHEN interactive controls (nav, tabs, policy rows, map divider) render THEN
   they SHALL present soft shadows/glow and smooth hover transitions.

### Requirement 2 — Stronger canvas visualization

**User Story:** As a presenter, I want the snow/salt/water illustration to look
atmospheric and legible, so that the story reads clearly on a projector.

#### Acceptance Criteria

1. WHEN the lab canvas draws THEN the sky, slope, and lake SHALL use smoother
   multi-stop gradients and an atmospheric light source.
2. WHEN particles and ripples render THEN they SHALL remain legible and bounded.
3. WHEN the water stage is active THEN the schematic connection SHALL read as
   the most prominent element without implying a hydrologic route.

### Requirement 3 — No change to behavior or integrity

**User Story:** As a maintainer, I want purely visual changes, so that the model,
accessibility, and data integrity guarantees are preserved.

#### Acceptance Criteria

1. WHEN artwork is interacted with THEN quantitative inputs SHALL NOT change.
2. WHEN the canvas is unavailable THEN the static fallback and planner SHALL
   still function.
3. WHEN reduced-motion is preferred THEN motion SHALL stay paused by default.
4. WHEN the build and all existing tests run THEN they SHALL pass unchanged
   except for additive test-harness support for new Canvas APIs.
5. WHEN the site is rebuilt THEN the public domain/base path SHALL remain
   `/saltshield/` and `deployment/site.json` SHALL be untouched.
