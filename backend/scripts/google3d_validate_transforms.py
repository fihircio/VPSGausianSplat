#!/usr/bin/env python3
"""Smoke-check WGS84/ECEF/ENU round trips for the Google 3D scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.google3d.aoi import AOIRegistry
from backend.services.google3d.transforms import ecef_to_wgs84, enu_to_ecef, wgs84_to_ecef, wgs84_to_enu


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--aoi-id")
    parser.add_argument("--max-latlon-error", type=float, default=1e-8)
    parser.add_argument("--max-height-error", type=float, default=1e-4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = AOIRegistry.load(args.config)
    aoi = registry.get(args.aoi_id) if args.aoi_id else registry.aois[0]
    failures = []
    checks = []
    for point in (aoi.origin_wgs84, *aoi.polygon_wgs84):
        ecef = wgs84_to_ecef(point)
        round_trip = ecef_to_wgs84(ecef)
        enu = wgs84_to_enu(point, aoi.origin_wgs84)
        via_enu = ecef_to_wgs84(enu_to_ecef(enu, aoi.origin_wgs84))
        latlon_error = max(abs(point.lat - round_trip.lat), abs(point.lon - round_trip.lon))
        height_error = abs(point.h - round_trip.h)
        enu_latlon_error = max(abs(point.lat - via_enu.lat), abs(point.lon - via_enu.lon))
        enu_height_error = abs(point.h - via_enu.h)
        check = {
            "lat": point.lat,
            "lon": point.lon,
            "ecef_round_trip_latlon_error": latlon_error,
            "ecef_round_trip_height_error_m": height_error,
            "enu_round_trip_latlon_error": enu_latlon_error,
            "enu_round_trip_height_error_m": enu_height_error,
        }
        checks.append(check)
        if latlon_error > args.max_latlon_error or enu_latlon_error > args.max_latlon_error:
            failures.append(check)
        if height_error > args.max_height_error or enu_height_error > args.max_height_error:
            failures.append(check)
    result = {"aoi_id": aoi.aoi_id, "ok": not failures, "checks": checks}
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
