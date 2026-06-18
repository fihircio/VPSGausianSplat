# Localization Sample

Basic single-frame VPS localization using WebCamTexture.

## Setup

1. Import `com.vps.sdk` via Package Manager.
2. Open the `LocalizationSample` scene.
3. Assign `VPSClient` fields (Base URL, API Key, Scene ID) in the Inspector.
4. Build to Android/iOS with camera permission enabled.

## How It Works

- `WebCamTexture` captures frames at 3-second intervals.
- `VPSClient.Localize(Texture2D)` sends the frame to the cloud backend.
- On success, `MapSpace` aligns AR content to the real world.
- HUD displays confidence, inlier count, and lock status.

## Components

| GameObject | Component |
|---|---|
| VPS Controller | VPSClient, MapSpace |
| AR Camera | Camera (tagged MainCamera) |
| Canvas | Text + Image elements for HUD |
| AR Content | Any scene content anchored to MapSpace |

## Sample Script

`LocalizationController.cs` — manages camera capture, triggers localization, and updates HUD.
