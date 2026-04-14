import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session

from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.utils.config import get_settings
from backend.utils.ffmpeg import extract_video_frames
from backend.utils.geometry import qvec_to_rotmat


class ReconstructionService:
    @staticmethod
    def _list_frame_files(frames_dir: Path) -> list[Path]:
        files: list[Path] = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
            files.extend(frames_dir.glob(ext))
        return sorted(files)

    @staticmethod
    def extract_frames(scene: Scene, db: Session, force_rebuild: bool = False) -> list[Path]:
        frames_dir = Path(scene.frames_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)

        if force_rebuild:
            for existing in ReconstructionService._list_frame_files(frames_dir):
                existing.unlink(missing_ok=True)
            db.execute(delete(Frame).where(Frame.scene_id == scene.id))
            db.commit()

        frame_files = ReconstructionService._list_frame_files(frames_dir)
        if frame_files and not force_rebuild:
            return frame_files

        input_path = Path(scene.input_path)
        if scene.input_type == "video":
            extract_video_frames(input_path, frames_dir)
        else:
            ext = input_path.suffix.lower() or ".jpg"
            out = frames_dir / f"frame_000001{ext}"
            shutil.copy2(input_path, out)

        frame_files = ReconstructionService._list_frame_files(frames_dir)
        created_frames: list[Frame] = []
        for idx, image_path in enumerate(frame_files):
            created_frames.append(
                Frame(scene_id=scene.id, frame_index=idx, image_path=str(image_path.resolve()))
            )
        if created_frames:
            db.add_all(created_frames)
            db.commit()
        return frame_files

    @staticmethod
    def run_colmap(scene: Scene, db: Session) -> None:
        settings = get_settings()
        frames_dir = Path(scene.frames_dir)
        sparse_root = Path(scene.sparse_dir or "")
        if not sparse_root.exists():
            sparse_root.mkdir(parents=True, exist_ok=True)
        database_path = sparse_root / "colmap.db"
        sparse_model_path = sparse_root / "sparse"
        sparse_txt_path = sparse_root / "sparse_txt"
        sparse_model_path.mkdir(parents=True, exist_ok=True)
        sparse_txt_path.mkdir(parents=True, exist_ok=True)

        commands = [
            [
                settings.colmap_bin,
                "feature_extractor",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_dir),
                "--ImageReader.single_camera",
                "1",
                "--ImageReader.camera_model",
                "OPENCV",
                "--SiftExtraction.max_num_features",
                "8192",
                "--SiftExtraction.estimate_affine_shape",
                "1",
                "--SiftExtraction.domain_size_pooling",
                "1",
            ],
            [
                settings.colmap_bin,
                "sequential_matcher",
                "--database_path",
                str(database_path),
                "--SequentialMatching.overlap",
                "10",
            ],
            [
                settings.colmap_bin,
                "mapper",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_dir),
                "--output_path",
                str(sparse_model_path),
                "--Mapper.abs_pose_min_num_inliers",
                "15",
                "--Mapper.init_min_num_inliers",
                "50",
                "--Mapper.init_min_tri_angle",
                "4",
                "--Mapper.abs_pose_min_inlier_ratio",
                "0.1",
                "--Mapper.min_model_size",
                "3",
            ],
        ]

        for cmd in commands:
            subprocess.run(cmd, check=True, capture_output=True)

        # Find the largest model among potentially multiple disparate reconstructions
        best_model_dir = sparse_model_path / "0"
        max_images = 0
        for model_cand in sparse_model_path.iterdir():
            if model_cand.is_dir() and (model_cand / "images.bin").exists():
                # Count images in images.bin would be perfect, but checking file size is a good proxy.
                # For more accuracy, I'll just use the one with the most points or images if I had a parser.
                # Here, we will just use the one with the largest images.bin file size as a proxy for complexity.
                sz = (model_cand / "images.bin").stat().st_size
                if sz > max_images:
                    max_images = sz
                    best_model_dir = model_cand

        # Convert the best model to TXT
        subprocess.run(
            [
                settings.colmap_bin,
                "model_converter",
                "--input_path",
                str(best_model_dir),
                "--output_path",
                str(sparse_txt_path),
                "--output_type",
                "TXT",
            ],
            check=True,
            capture_output=True,
        )

        ReconstructionService._persist_colmap_poses(scene.id, sparse_txt_path, db)
 
        # Hard Quality Gate: Check registration percentage
        db.refresh(scene)
        total_extracted = len(ReconstructionService._list_frame_files(frames_dir))
        registered_count = db.scalar(
            select(func.count(Frame.id))
            .where(Frame.scene_id == scene.id, Frame.pose_json.is_not(None))
        )
        reg_ratio = registered_count / total_extracted if total_extracted > 0 else 0
        
        if reg_ratio < 0.5:
            raise ValueError(
                f"Mapping Quality Too Low: Only {reg_ratio:.1%} frames registered. "
                "Ensure video has physical movement and sufficient texture."
            )

        scene.sparse_dir = str(sparse_root.resolve())
        db.add(scene)
        db.commit()

    @staticmethod
    def _persist_colmap_poses(scene_id: str, sparse_txt_path: Path, db: Session) -> None:
        cameras = ReconstructionService._parse_cameras(sparse_txt_path / "cameras.txt")
        image_poses = ReconstructionService._parse_images(sparse_txt_path / "images.txt")

        frames = db.scalars(select(Frame).where(Frame.scene_id == scene_id)).all()
        frames_by_name = {Path(f.image_path).name: f for f in frames}

        for image_name, pose in image_poses.items():
            frame = frames_by_name.get(image_name)
            if not frame:
                continue
            frame.pose_json = pose
            frame.intrinsics_json = cameras.get(pose["camera_id"])
            db.add(frame)

        db.commit()

        poses_path = sparse_txt_path / "camera_poses.json"
        with poses_path.open("w", encoding="utf-8") as f:
            json.dump(image_poses, f, indent=2)

    @staticmethod
    def _parse_cameras(cameras_txt: Path) -> dict[int, dict]:
        result: dict[int, dict] = {}
        with cameras_txt.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                camera_id = int(parts[0])
                model = parts[1]
                width = int(parts[2])
                height = int(parts[3])
                params = [float(x) for x in parts[4:]]
                if model in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL"}:
                    fx = fy = params[0]
                    cx, cy = params[1], params[2]
                else:
                    fx, fy, cx, cy = params[0], params[1], params[2], params[3]
                result[camera_id] = {
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": fx,
                    "fy": fy,
                    "cx": cx,
                    "cy": cy,
                }
        return result

    @staticmethod
    def _parse_images(images_txt: Path) -> dict[str, dict]:
        result: dict[str, dict] = {}
        with images_txt.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        for i in range(0, len(lines), 2):
            parts = lines[i].split()
            image_id = int(parts[0])
            qvec = [float(v) for v in parts[1:5]]
            tvec = [float(v) for v in parts[5:8]]
            camera_id = int(parts[8])
            name = parts[9]
            R_cw = qvec_to_rotmat(qvec)
            t_cw = np.array(tvec, dtype=np.float64).reshape(3, 1)
            R_wc = R_cw.T
            C = (-R_wc @ t_cw).reshape(3)
            result[name] = {
                "image_id": image_id,
                "camera_id": camera_id,
                "qvec_wxyz": qvec,
                "tvec": tvec,
                "rotation_cw": R_cw.tolist(),
                "rotation_wc": R_wc.tolist(),
                "position_wc": C.tolist(),
            }
        return result
