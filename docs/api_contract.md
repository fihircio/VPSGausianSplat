# VPS API Contract

## Base URL

Local default:

```bash
http://localhost:8000
```

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Scene Status

```http
GET /scene/{scene_id}
```

Use this before Navigatus localization to confirm the map is ready.

Required ready state:

```json
{
  "status": "READY",
  "faiss_index_path": "...",
  "splat_path": "..."
}
```

## VPS Localize

```http
POST /vps/localize
Content-Type: multipart/form-data
```

Form fields:

| Field | Required | Description |
| --- | --- | --- |
| `scene_id` | yes | Processed scene UUID |
| `query_image` | yes | JPEG/PNG camera frame |
| `agent_id` | no | Client identity for multi-user sync broadcast |

Success response:

```json
{
  "position": [0.12, 1.45, -2.03],
  "rotation": [0.0, 0.71, 0.0, 0.70],
  "inliers": 64,
  "confidence": 0.72
}
```

Coordinate convention:

- `position` is the camera position in the reconstructed VPS scene coordinate system.
- `rotation` is quaternion `[qx, qy, qz, qw]`.
- Navigatus must transform this pose into floorplan/navigation coordinates before route guidance is geometrically meaningful.

Failure responses:

```json
{
  "detail": "Feature index not built for scene"
}
```

Common failure causes:

| HTTP | Cause |
| --- | --- |
| `404` | Scene does not exist |
| `400` | Scene is not localizable, weak query image, not enough correspondences |
| `500` | Unexpected backend/runtime error |

## Agent Sync WebSocket

```http
WS /vps/ws/agents/{scene_id}
```

Current use:

- Backend broadcasts pose updates when `/vps/localize` receives `agent_id`.
- Navigatus can later subscribe to show other live users or staff devices.

## Evaluation Report

```http
GET /vps/evaluation/{scene_id}
```

Returns the best-config evaluation summary from `backend/storage/debug/vps_evaluation_report.json`.

Response:

```json
{
  "summary": {
    "scene_id": "...",
    "num_frames": 10,
    "success_rate": 1.0,
    "avg_inliers": 137.9,
    "avg_confidence": 0.66,
    "avg_translation_error": 0.041,
    "avg_rotation_error": 0.187
  },
  "config": {
    "orb_nfeatures": 1000,
    "pixel_distance_threshold": 8.0,
    "ratio_test_threshold": 0.7
  }
}
```
