import subprocess
from pathlib import Path

from backend.utils.config import get_settings


def extract_video_frames(video_path: Path, output_dir: Path, fps: int | None = None) -> None:
    settings = get_settings()
    fps_value = fps or settings.default_video_fps
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "frame_%06d.jpg"
    cmd = [
        settings.ffmpeg_bin,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps_value}",
        str(output_pattern),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
