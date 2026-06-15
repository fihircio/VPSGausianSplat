"""Local manifest skeleton writer for Google 3D AOI setup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.google3d.aoi import AOIRegistry
from backend.services.google3d.camera_paths import CameraPathConfig, generate_camera_path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def create_aoi_manifest_skeleton(
    config_path: Path,
    output_root: Path,
    aoi_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    registry = AOIRegistry.load(config_path)
    aoi = registry.get(aoi_id) if aoi_id else registry.aois[0]
    camera_config = CameraPathConfig.from_mapping(_load_raw(config_path).get("camera_path"))
    aoi_dir = output_root / "aois" / aoi.aoi_id
    if aoi_dir.exists() and not overwrite:
        raise FileExistsError(f"{aoi_dir} already exists; pass --overwrite to replace scaffold JSON")

    trajectory_path = aoi_dir / "render_runs" / "scaffold" / "trajectory.json"
    source_tiles_path = aoi_dir / "source_tiles.json"
    aoi_path = aoi_dir / "aoi.json"
    permission_path = output_root / "permissions" / f"{aoi.aoi_id}_permission.json"
    manifest_path = aoi_dir / "manifest.json"

    intrinsics = camera_config.intrinsics()
    poses = [pose.to_dict(aoi, intrinsics) for pose in generate_camera_path(aoi, camera_config)]
    write_json(aoi_path, aoi.to_dict())
    write_json(permission_path, registry.permission.to_dict())
    write_json(
        source_tiles_path,
        {
            "schema_version": "google3d.source_tiles.v1",
            "aoi_id": aoi.aoi_id,
            "provider": registry.permission.provider,
            "source": registry.permission.source,
            "status": "not_ingested",
            "tiles": [],
            "notes": "Offline scaffold only. Populate after authorized Google 3D tile traversal.",
        },
    )
    write_json(
        trajectory_path,
        {
            "schema_version": "google3d.trajectory.v1",
            "aoi_id": aoi.aoi_id,
            "camera_policy": camera_config.policy,
            "frame_count": len(poses),
            "frames": poses,
        },
    )
    manifest = {
        "schema_version": "google3d.aoi_manifest.v1",
        "aoi_id": aoi.aoi_id,
        "local_frame": aoi.local_frame,
        "paths": {
            "aoi": str(aoi_path),
            "permission": str(permission_path),
            "source_tiles": str(source_tiles_path),
            "trajectory": str(trajectory_path),
            "tiles_dir": str(aoi_dir / "tiles"),
            "meshes_dir": str(aoi_dir / "meshes"),
            "render_runs_dir": str(aoi_dir / "render_runs"),
            "features_dir": str(aoi_dir / "features"),
            "eval_dir": str(aoi_dir / "eval"),
        },
        "permission_research_only": registry.permission.is_research_only,
    }
    write_json(manifest_path, manifest)
    return manifest


def _load_raw(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
