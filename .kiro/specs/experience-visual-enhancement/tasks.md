# Implementation Plan — Experience Page Visual Enhancement

## Overview

This plan covers the presentation-layer changes that strengthen the `#experience`
landing page: a scoped CSS override block appended to `experience_live.css` and
color/gradient upgrades in the `winter_scene.js` Canvas 2D renderer, plus the
build, verification, and integrity checks. All tasks are implemented and verified;
the shipped report (`results/SaltShield_Wachusett.html`) and staged site (`docs/`)
reflect these changes. No markup, model, or routing changes are in scope.

## Tasks

- [x] 1. Add the CSS visual-enhancement override block
  - Append a scoped `.experience` override block to `experience_live.css`
  - Cover hero, buttons, nav, stats, map, policy bars, capacity tracks, closing
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Enrich the canvas renderer
  - [x] 2.1 Smooth the sky gradient and add an atmospheric sun glow
    - _Requirements: 2.1_
  - [x] 2.2 Upgrade hill/slope/lake fills to gradients and three-tone trees
    - _Requirements: 2.1_
  - [x] 2.3 Lift snow, ripple, and connection-line legibility
    - _Requirements: 2.2, 2.3_

- [x] 3. Support the new Canvas API in the test harness
  - Add `createRadialGradient` to the `test_experience.cjs` canvas mock
  - _Requirements: 3.4_

- [x] 4. Rebuild and verify
  - [x] 4.1 Run `python build_report.py` and `python build_site.py`
    - _Requirements: 3.5_
  - [x] 4.2 Run `node test_experience.cjs` plus demo/ui/planning/joint suites
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 4.3 Confirm `docs/index.html` base path stays `/saltshield/`
    - _Requirements: 3.5_

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2", "3"],
      "dependsOn": []
    },
    {
      "wave": 2,
      "tasks": ["4.1"],
      "dependsOn": ["1", "2", "3"]
    },
    {
      "wave": 3,
      "tasks": ["4.2"],
      "dependsOn": ["4.1"]
    },
    {
      "wave": 4,
      "tasks": ["4.3"],
      "dependsOn": ["4.2"]
    }
  ]
}
```

- Tasks 1, 2, and 3 are independent and can proceed in parallel.
- Task 4 depends on 1, 2, and 3; its subtasks run in order 4.1 → 4.2 → 4.3.

## Notes

- `experience_live.css` is concatenated after `experience.css` at build time, so
  appended overrides win at equal specificity. Keep all new selectors scoped
  under `.experience`.
- `winter_scene.js` changes are limited to fill/stroke styles and gradient stops;
  particle physics, bounds, and geometry are unchanged.
- The `createRadialGradient` test-harness addition mirrors the existing
  `createLinearGradient` mock and is the only test change permitted by
  Requirement 3.4.
- Do not edit `deployment/site.json`; the public base path must stay `/saltshield/`
  (Requirement 3.5). Never hand-edit generated files under `results/` or `docs/`.
