# Multi-Frame Localization Sample

Capture 2–6 frames for improved VPS localization accuracy with per-frame confidence visualization.

## Setup

1. Import `com.vps.sdk` via Package Manager.
2. Open the `MultiFrameSample` scene.
3. Assign `VPSClient` fields in the Inspector.
4. Build to Android/iOS.

## How It Works

- Tap the **Capture** button to begin multi-frame capture.
- 4 frames (configurable 2–6) are captured at 0.5s intervals.
- Each frame is sent to `/vps/localize/multi`.
- The response includes `frames_used` and `frame_confidences[]` — shown as color-coded bars.
- On success, AR content appears.
- If confidence is low, tap **Capture** again.

## Components

| GameObject | Component |
|---|---|
| VPS Controller | VPSClient, MapSpace |
| AR Camera | Camera (tagged MainCamera) |
| Canvas | Conf bars, thumbnails, HUD text |
| AR Content | Content anchored to MapSpace |

## Sample Script

`MultiFrameController.cs` — manages multi-frame capture, thumbnail display, per-frame confidence bars, and triggering the multi-frame API call.
