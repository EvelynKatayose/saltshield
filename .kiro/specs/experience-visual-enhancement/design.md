# Design — Experience Page Visual Enhancement

## Overview

Enhance the experience page purely through the presentation layer: an appended
override block in `experience_live.css` and targeted color/gradient changes in
the Canvas 2D renderer `winter_scene.js`. No markup, model, or routing changes.

## Architecture context

The build (`build_report.py`) concatenates `experience.css` + `experience_live.css`
into `__WORKSPACE_CSS__`, so rules appended to `experience_live.css` load last
and win at equal specificity. `winter_scene.js` is inlined into `__SOLVER_JS__`
and exposes `SaltShieldWinter.draw()`, which paints both the hero and lab canvases.

```
experience_live.css  ──┐
experience.css ────────┼──► __WORKSPACE_CSS__ ──► report_template.html <style>
winter_scene.js  ──────┴──► __SOLVER_JS__      ──► report_template.html <script>
```

## Components and changes

### 1. CSS override block (`experience_live.css`, appended)

- Hero: radial vignette on `.x-hero-shade`; gradient text + glow on `h1`/span;
  text-shadow on the description.
- Buttons: gradient backgrounds, layered box-shadows, subtle hover scale for
  `.x-button-white`, `.x-button-glass`, `.x-button-dark`.
- Nav: translucent background with drop shadow; gradient CTA hover.
- Stats / accents: gradient text fill for `.x-facts strong` and `.x-accent-number`.
- Map: deeper shadow on `.x-compare-map`; gradient + glow divider; gradient
  policy-comparison bars (distinct independent vs. pooled); glowing capacity tracks.
- Closing: richer radial background; gradient headline span.
- Reveal transition easing refinement.

All selectors are scoped under `.experience` to avoid leaking into the workspace.

### 2. Canvas renderer (`winter_scene.js`)

- Sky: add intermediate gradient stops for a smoother transition.
- Add a warm radial "sun" glow (`createRadialGradient`) in the upper right.
- Hill layers: lighter, atmospheric palette.
- Slope: vertical gradient instead of flat fill.
- Trees: three-tone variation instead of two.
- Lake: add a middle gradient stop for depth.
- Snow/ripples/waves: minor opacity lifts for legibility.
- Water-stage connection line: slightly thicker and more vivid.

All geometry, particle physics, and bounds are unchanged — only fill/stroke
styles and gradient stops.

## Testing strategy

- `node test_experience.cjs` executes the embedded scripts. Its canvas mock must
  support `createRadialGradient` (additive change mirroring `createLinearGradient`).
- Re-run the full Node + Python test suite after `build_report.py`.

## Integrity and non-goals

- No change to `experience.html`, the model, `deployment/site.json`, or routing.
- Artwork remains illustrative; it never feeds salt accounting.
