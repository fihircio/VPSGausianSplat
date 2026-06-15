#!/usr/bin/env python3
"""Create an offline Google 3D AOI manifest skeleton from a JSON registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.google3d.manifest import create_aoi_manifest_skeleton


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="AOI registry JSON config")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("backend/storage/google3d"),
        help="Root folder for Google 3D scaffold output",
    )
    parser.add_argument("--aoi-id", help="AOI id to scaffold; defaults to the first AOI in config")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing scaffold JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = create_aoi_manifest_skeleton(
        config_path=args.config,
        output_root=args.output_root,
        aoi_id=args.aoi_id,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
