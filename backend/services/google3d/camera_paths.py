"""Deterministic camera path generation for synthetic Google 3D AOIs."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from backend.services.google3d.aoi import AOI
from backend.services.google3d.transforms import ENUPoint, enu_to_ecef, enu_to_wgs84, wgs84_to_enu


@dataclass(frozen=True)
class CameraPathConfig:
    policy: str = "pedestrian_perimeter"
    frame_count: int = 24
    camera_height_m: float = 1.6
    fov_degrees: float = 70.0
    width: int = 1280
    height: int = 720
    pitch_degrees: float = -5.0
    seed: int = 13
    jitter_m: float = 0.0

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "CameraPathConfig":
        if value is None:
            return cls()
        return cls(
            policy=str(value.get("policy", "pedestrian_perimeter")),
            frame_count=int(value.get("frame_count", 24)),
            camera_height_m=float(value.get("camera_height_m", 1.6)),
            fov_degrees=float(value.get("fov_degrees", 70.0)),
            width=int(value.get("width", 1280)),
            height=int(value.get("height", 720)),
            pitch_degrees=float(value.get("pitch_degrees", -5.0)),
            seed=int(value.get("seed", 13)),
            jitter_m=float(value.get("jitter_m", 0.0)),
        )

    def intrinsics(self) -> dict[str, float | int]:
        fx = (self.width / 2.0) / math.tan(math.radians(self.fov_degrees) / 2.0)
        fy = fx
        return {
            "width": self.width,
            "height": self.height,
            "fx": fx,
            "fy": fy,
            "cx": self.width / 2.0,
            "cy": self.height / 2.0,
            "fov_degrees": self.fov_degrees,
        }


@dataclass(frozen=True)
class CameraPose:
    frame_id: str
    position_enu: ENUPoint
    yaw_degrees: float
    pitch_degrees: float
    roll_degrees: float = 0.0

    def to_dict(self, aoi: AOI, intrinsics: dict[str, Any]) -> dict[str, Any]:
        ecef = enu_to_ecef(self.position_enu, aoi.origin_wgs84)
        wgs84 = enu_to_wgs84(self.position_enu, aoi.origin_wgs84)
        return {
            "frame_id": self.frame_id,
            "camera_model": "pinhole",
            "intrinsics": intrinsics,
            "position_enu": self.position_enu.to_list(),
            "position_ecef": ecef.to_list(),
            "position_wgs84": wgs84.to_dict(),
            "rotation_ypr_degrees_enu": {
                "yaw": self.yaw_degrees,
                "pitch": self.pitch_degrees,
                "roll": self.roll_degrees,
            },
            "extrinsics_note": "ENU camera pose scaffold; renderer-specific matrices are not generated yet.",
            "source_tile_ids": [],
        }


def generate_camera_path(aoi: AOI, config: CameraPathConfig | None = None) -> list[CameraPose]:
    config = config or CameraPathConfig()
    if config.frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if config.policy != "pedestrian_perimeter":
        raise ValueError(f"unsupported camera policy {config.policy!r}")

    polygon_enu = [wgs84_to_enu(point, aoi.origin_wgs84) for point in aoi.polygon_wgs84]
    min_e = min(point.e for point in polygon_enu)
    max_e = max(point.e for point in polygon_enu)
    min_n = min(point.n for point in polygon_enu)
    max_n = max(point.n for point in polygon_enu)
    width = max(max_e - min_e, 1.0)
    depth = max(max_n - min_n, 1.0)
    inset = min(width, depth, 8.0) * 0.15
    corners = [
        (min_e + inset, min_n + inset),
        (max_e - inset, min_n + inset),
        (max_e - inset, max_n - inset),
        (min_e + inset, max_n - inset),
    ]

    rng = random.Random(config.seed)
    poses: list[CameraPose] = []
    for index in range(config.frame_count):
        edge_index = (index * 4) // config.frame_count
        edge_fraction = ((index * 4) / config.frame_count) - edge_index
        start = corners[edge_index % 4]
        end = corners[(edge_index + 1) % 4]
        east = start[0] + (end[0] - start[0]) * edge_fraction
        north = start[1] + (end[1] - start[1]) * edge_fraction
        if config.jitter_m:
            east += rng.uniform(-config.jitter_m, config.jitter_m)
            north += rng.uniform(-config.jitter_m, config.jitter_m)
        yaw = math.degrees(math.atan2(end[0] - start[0], end[1] - start[1]))
        poses.append(
            CameraPose(
                frame_id=f"frame_{index:06d}",
                position_enu=ENUPoint(east, north, config.camera_height_m),
                yaw_degrees=yaw,
                pitch_degrees=config.pitch_degrees,
            )
        )
    return poses
