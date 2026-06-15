"""WGS84, ECEF, and local ENU coordinate helpers.

The functions here intentionally avoid external dependencies so AOI setup and
validation can run offline before Google API credentials exist.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_B = WGS84_A * (1.0 - WGS84_F)
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
WGS84_EP2 = (WGS84_A**2 - WGS84_B**2) / WGS84_B**2


@dataclass(frozen=True)
class WGS84Point:
    lat: float
    lon: float
    h: float = 0.0

    @classmethod
    def from_mapping(cls, value: dict) -> "WGS84Point":
        return cls(lat=float(value["lat"]), lon=float(value["lon"]), h=float(value.get("h", 0.0)))

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "h": self.h}


@dataclass(frozen=True)
class ECEFPoint:
    x: float
    y: float
    z: float

    @classmethod
    def from_iterable(cls, value: Iterable[float]) -> "ECEFPoint":
        x, y, z = value
        return cls(float(x), float(y), float(z))

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass(frozen=True)
class ENUPoint:
    e: float
    n: float
    u: float

    @classmethod
    def from_iterable(cls, value: Iterable[float]) -> "ENUPoint":
        e, n, u = value
        return cls(float(e), float(n), float(u))

    def to_list(self) -> list[float]:
        return [self.e, self.n, self.u]


def wgs84_to_ecef(point: WGS84Point) -> ECEFPoint:
    lat = math.radians(point.lat)
    lon = math.radians(point.lon)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)

    x = (n + point.h) * cos_lat * math.cos(lon)
    y = (n + point.h) * cos_lat * math.sin(lon)
    z = (n * (1.0 - WGS84_E2) + point.h) * sin_lat
    return ECEFPoint(x, y, z)


def ecef_to_wgs84(point: ECEFPoint) -> WGS84Point:
    p = math.hypot(point.x, point.y)
    if p == 0.0:
        lat = math.copysign(math.pi / 2.0, point.z)
        lon = 0.0
        h = abs(point.z) - WGS84_B
        return WGS84Point(math.degrees(lat), math.degrees(lon), h)

    lon = math.atan2(point.y, point.x)
    theta = math.atan2(point.z * WGS84_A, p * WGS84_B)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)
    lat = math.atan2(
        point.z + WGS84_EP2 * WGS84_B * sin_theta**3,
        p - WGS84_E2 * WGS84_A * cos_theta**3,
    )
    sin_lat = math.sin(lat)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    h = p / math.cos(lat) - n
    return WGS84Point(math.degrees(lat), math.degrees(lon), h)


def enu_basis(origin: WGS84Point) -> tuple[tuple[float, float, float], ...]:
    lat = math.radians(origin.lat)
    lon = math.radians(origin.lon)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)
    return (
        (-sin_lon, cos_lon, 0.0),
        (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat),
        (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat),
    )


def ecef_to_enu(point: ECEFPoint, origin: WGS84Point) -> ENUPoint:
    origin_ecef = wgs84_to_ecef(origin)
    dx = point.x - origin_ecef.x
    dy = point.y - origin_ecef.y
    dz = point.z - origin_ecef.z
    east, north, up = enu_basis(origin)
    return ENUPoint(
        east[0] * dx + east[1] * dy + east[2] * dz,
        north[0] * dx + north[1] * dy + north[2] * dz,
        up[0] * dx + up[1] * dy + up[2] * dz,
    )


def enu_to_ecef(point: ENUPoint, origin: WGS84Point) -> ECEFPoint:
    origin_ecef = wgs84_to_ecef(origin)
    east, north, up = enu_basis(origin)
    x = origin_ecef.x + east[0] * point.e + north[0] * point.n + up[0] * point.u
    y = origin_ecef.y + east[1] * point.e + north[1] * point.n + up[1] * point.u
    z = origin_ecef.z + east[2] * point.e + north[2] * point.n + up[2] * point.u
    return ECEFPoint(x, y, z)


def wgs84_to_enu(point: WGS84Point, origin: WGS84Point) -> ENUPoint:
    return ecef_to_enu(wgs84_to_ecef(point), origin)


def enu_to_wgs84(point: ENUPoint, origin: WGS84Point) -> WGS84Point:
    return ecef_to_wgs84(enu_to_ecef(point, origin))
