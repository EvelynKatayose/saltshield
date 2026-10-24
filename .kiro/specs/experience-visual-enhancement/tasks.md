# Implementation Plan — Experience Page Visual Enhancement

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
