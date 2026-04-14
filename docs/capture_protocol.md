# VPS Capture Protocol (MVP)

## Objective
Capture scene video that is reliable for:
- COLMAP reconstruction
- ORB-to-3D correspondence mapping
- VPS localization validation

## Recording Setup
- Device:
  - Use a modern phone camera with good stabilization.
- Resolution / FPS:
  - Prefer `1080p @ 30fps`.
  - Avoid ultra-wide lens for MVP unless required.
- Camera pose:
  - Height `1.4m - 1.6m`.
  - Keep camera mostly horizontal.
- Speed:
  - Walk slowly and steadily.
  - Avoid fast turns and sudden acceleration.

## Required Capture Paths
- Record at least `2 loops`:
  1. Clockwise loop through the space
  2. Counter-clockwise loop over the same path
- Duration:
  - `2 - 4 minutes` per loop
- Coverage:
  - Include long corridors plus intersections/junctions.
  - Include anchor-rich landmarks:
    - doors with labels
    - signs / room numbers
    - structural corners
    - distinctive objects

## Shot Quality Rules
- Keep image sharp:
  - No motion blur
  - No aggressive digital zoom
- Keep exposure stable:
  - Avoid strong backlight where possible
- Minimize dynamic occlusion:
  - Reduce frames dominated by moving people
- Avoid excessive tilt:
  - Do not point only at floor/ceiling

## Corridor-Specific Guidance
Corridors with repeated patterns are hard for VPS. To reduce ambiguity:
- Add small lateral motion while walking (slight side parallax).
- Pause briefly at intersections and look left/right.
- Revisit key nodes from opposite directions.

## Handoff Metadata (must provide)
- Device model
- Lens mode used
- FPS + resolution
- Start point and end point of each loop
- Approximate local time and lighting condition
- Areas skipped / blocked

## File Naming
Use deterministic names:
- `scene_<site>_<date>_loop1_clockwise.mp4`
- `scene_<site>_<date>_loop2_counterclockwise.mp4`

## Minimum Acceptable Submission
- At least 2 videos (clockwise + counter-clockwise)
- Stable lighting
- Full corridor and junction coverage
