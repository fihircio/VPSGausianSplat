"""Offline-safe scaffolding for Google 3D synthetic dataset setup."""

from backend.services.google3d.aoi import AOI, AOIRegistry, DataPermission, WGS84Point
from backend.services.google3d.camera_paths import CameraPathConfig, CameraPose, generate_camera_path

__all__ = [
    "AOI",
    "AOIRegistry",
    "CameraPathConfig",
    "CameraPose",
    "DataPermission",
    "WGS84Point",
    "generate_camera_path",
]
