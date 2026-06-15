import subprocess
from pathlib import Path
import shutil

import numpy as np
from sqlalchemy.orm import Session

from backend.models.scene import Scene
from backend.utils.config import get_settings
from backend.utils.storage import get_storage


class SplattingService:
    @staticmethod
    def run(scene: Scene, db: Session) -> str:
        storage = get_storage()
        settings = get_settings()
        
        sparse_dir_remote = f"recon/{scene.id}"
        frames_dir_remote = f"frames/{scene.id}"
        splat_dir_remote = f"splats/{scene.id}"
        
        local_sparse_dir = storage.ensure_local_copy(sparse_dir_remote)
        local_frames_dir = storage.ensure_local_copy(frames_dir_remote)
        local_splat_dir = storage.ensure_local_copy(splat_dir_remote)
        local_splat_dir.mkdir(parents=True, exist_ok=True)

        sparse_txt = local_sparse_dir / "sparse_txt"

        gaussian_repo = Path(settings.gaussian_splatting_repo) if settings.gaussian_splatting_repo else None
        if gaussian_repo and (gaussian_repo / "train.py").exists():
            output_dir = local_splat_dir / "gaussian_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            gs_input = local_splat_dir / "gaussian_input"
            if gs_input.exists():
                shutil.rmtree(gs_input)
            gs_input.mkdir(parents=True, exist_ok=True)
            shutil.copytree(local_frames_dir, gs_input / "images")
            shutil.copytree(local_sparse_dir / "sparse", gs_input / "sparse")
            cmd = [
                "python",
                str(gaussian_repo / "train.py"),
                "-s",
                str(gs_input),
                "-m",
                str(output_dir),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            ply_candidates = sorted(output_dir.rglob("*.ply"))
            if not ply_candidates:
                raise RuntimeError("Gaussian Splatting training finished but no .ply found")
            splat_path_local = ply_candidates[-1]
        else:
            splat_path_local = local_splat_dir / "sparse_points_fallback.ply"
            SplattingService._export_colmap_points_to_ply(
                points_path=sparse_txt / "points3D.txt",
                output_ply=splat_path_local,
            )

        # Sync back to remote if not LOCAL
        if settings.storage_backend.upper() != "LOCAL":
            storage.sync_dir_to_remote(local_splat_dir, splat_dir_remote)

        remote_splat_path = f"{splat_dir_remote}/{splat_path_local.name}"
        scene.splat_path = remote_splat_path
        db.add(scene)
        db.commit()
        return scene.splat_path

    @staticmethod
    def _export_colmap_points_to_ply(points_path: Path, output_ply: Path) -> None:
        import struct

        xyz = []
        rgb = []
        with points_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
                rgb.append([int(parts[4]), int(parts[5]), int(parts[6])])

        if not xyz:
            raise RuntimeError("No COLMAP 3D points available to create fallback PLY")

        num_pts = len(xyz)

        # Write binary PLY — ~80% smaller than ASCII, ~10x faster to parse in Three.js
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            f"element vertex {num_pts}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "property uchar red\n"
            "property uchar green\n"
            "property uchar blue\n"
            "end_header\n"
        ).encode("ascii")

        with output_ply.open("wb") as f:
            f.write(header)
            for p, c in zip(xyz, rgb):
                f.write(struct.pack("<fff", p[0], p[1], p[2]))
                f.write(struct.pack("<BBB", int(c[0]), int(c[1]), int(c[2])))

