"""Offline-safe scaffolding for Google 3D synthetic dataset setup."""

from backend.services.google3d.aoi import AOI, AOIRegistry, DataPermission, WGS84Point
from backend.services.google3d.camera_paths import CameraPathConfig, CameraPose, generate_camera_path
from backend.services.google3d.tile_downloader import TileDownloader, TileMetadata
from backend.services.google3d.scene_builder import build_scene
from backend.services.google3d.mesh_renderer import run_blender
from backend.services.google3d.dataset_generator import generate_dataset, read_dataset

__all__ = [
    "AOI",
    "AOIRegistry",
    "CameraPathConfig",
    "CameraPose",
    "DataPermission",
    "TileDownloader",
    "TileMetadata",
    "WGS84Point",
    "build_scene",
    "generate_camera_path",
    "generate_dataset",
    "read_dataset",
    "run_blender",
]
