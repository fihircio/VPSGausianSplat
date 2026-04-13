from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ColmapImage:
    image_id: int
    name: str
    camera_id: int
    xys: np.ndarray
    point3d_ids: np.ndarray


@dataclass
class ColmapPoint3D:
    point3d_id: int
    xyz: np.ndarray
    rgb: tuple[int, int, int]
    error: float


class ColmapLoader:
    @staticmethod
    def load_sparse_model(model_dir: Path) -> tuple[dict[str, ColmapImage], dict[int, ColmapPoint3D]]:
        images_path = model_dir / "images.bin"
        points_path = model_dir / "points3D.bin"
        if not images_path.exists() or not points_path.exists():
            raise RuntimeError(
                f"COLMAP binary model files missing in {model_dir}. Expected images.bin and points3D.bin"
            )
        images = ColmapLoader.load_images_bin(images_path)
        points3d = ColmapLoader.load_points3d_bin(points_path)
        images_by_name = {img.name: img for img in images.values()}
        return images_by_name, points3d

    @staticmethod
    def load_images_bin(path: Path) -> dict[int, ColmapImage]:
        images: dict[int, ColmapImage] = {}
        with path.open("rb") as f:
            num_images = ColmapLoader._read_struct(f, "<Q")[0]
            for _ in range(num_images):
                image_id = ColmapLoader._read_struct(f, "<i")[0]
                _qvec = ColmapLoader._read_struct(f, "<dddd")
                _tvec = ColmapLoader._read_struct(f, "<ddd")
                camera_id = ColmapLoader._read_struct(f, "<i")[0]
                name = ColmapLoader._read_c_string(f)
                num_points2d = ColmapLoader._read_struct(f, "<Q")[0]
                xys = np.empty((num_points2d, 2), dtype=np.float32)
                point3d_ids = np.empty((num_points2d,), dtype=np.int64)
                for j in range(num_points2d):
                    x, y, point3d_id = ColmapLoader._read_struct(f, "<ddq")
                    xys[j] = [float(x), float(y)]
                    point3d_ids[j] = int(point3d_id)
                images[image_id] = ColmapImage(
                    image_id=image_id,
                    name=name,
                    camera_id=camera_id,
                    xys=xys,
                    point3d_ids=point3d_ids,
                )
        return images

    @staticmethod
    def load_points3d_bin(path: Path) -> dict[int, ColmapPoint3D]:
        points: dict[int, ColmapPoint3D] = {}
        with path.open("rb") as f:
            num_points = ColmapLoader._read_struct(f, "<Q")[0]
            for _ in range(num_points):
                point3d_id = ColmapLoader._read_struct(f, "<Q")[0]
                x, y, z = ColmapLoader._read_struct(f, "<ddd")
                r, g, b = ColmapLoader._read_struct(f, "<BBB")
                error = ColmapLoader._read_struct(f, "<d")[0]
                track_len = ColmapLoader._read_struct(f, "<Q")[0]
                if track_len > 0:
                    f.seek(8 * track_len, 1)  # (image_id, point2D_idx) pairs -> 2 int32 = 8 bytes
                points[int(point3d_id)] = ColmapPoint3D(
                    point3d_id=int(point3d_id),
                    xyz=np.array([float(x), float(y), float(z)], dtype=np.float32),
                    rgb=(int(r), int(g), int(b)),
                    error=float(error),
                )
        return points

    @staticmethod
    def _read_struct(f, fmt: str) -> tuple:
        size = struct.calcsize(fmt)
        data = f.read(size)
        if len(data) != size:
            raise EOFError(f"Unexpected EOF while reading format {fmt}")
        return struct.unpack(fmt, data)

    @staticmethod
    def _read_c_string(f) -> str:
        chars = []
        while True:
            c = f.read(1)
            if c == b"":
                raise EOFError("Unexpected EOF while reading COLMAP C-string")
            if c == b"\x00":
                return b"".join(chars).decode("utf-8", errors="replace")
            chars.append(c)
