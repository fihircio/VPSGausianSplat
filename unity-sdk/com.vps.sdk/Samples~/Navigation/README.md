# Navigation Sample

VPS-driven AR navigation with NavMesh, target waypoints, and optional WebSocket multi-agent sync.

## Setup

1. Import `com.vps.sdk` via Package Manager.
2. Open the `NavigationSample` scene.
3. Assign `VPSClient` and `WebSocketClient` fields in the Inspector.
4. Bake a NavMesh on the scene geometry.
5. Build to Android/iOS.

## How It Works

- VPS localization runs at 2-second intervals.
- `NavMeshAgent` navigates toward a user-placed target marker.
- `LineRenderer` traces the path from the agent's current NavMesh path.
- Optional `WebSocketClient` syncs the Unity agent's pose to other connected clients.

## Components

| GameObject | Component |
|---|---|
| VPS Controller | VPSClient, MapSpace |
| AR Camera | Camera (tagged MainCamera) |
| Navigation Agent | NavMeshAgent, NavigationController |
| Target Marker | Transform (placed at destination) |
| Path Line | LineRenderer |

## Sample Script

`NavigationController.cs` — manages localization, NavMesh steering, target placement, WebSocket sync, and path visualization.
