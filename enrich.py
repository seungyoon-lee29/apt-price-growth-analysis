"""
enrich.py
---------
DataFrame에 세그먼트 속성(신축/구축, 역세권, 권역)을 부착.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from config import AGE_SEGMENTS, AREA_SEGMENTS, SEOUL_ZONES, METRO_ZONES, SUBWAY_DISTANCE


# ------------------------------------------------------------------
# 1. 준공 연차
# ------------------------------------------------------------------
def add_age_segment(df: pd.DataFrame, ref_year: Optional[int] = None) -> pd.DataFrame:
    if df.empty:
        return df
    ref_year = ref_year or datetime.now().year
    df = df.copy()
    df["age_years"] = ref_year - df["build_year"]

    def _classify(age):
        if pd.isna(age):
            return "미상"
        for name, (lo, hi) in AGE_SEGMENTS.items():
            if lo <= age < hi:
                return name
        return "미상"

    df["age_segment"] = df["age_years"].apply(_classify)
    return df


# ------------------------------------------------------------------
# 2. 면적 세그먼트
# ------------------------------------------------------------------
def add_area_segment(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()

    def _classify(a):
        if pd.isna(a):
            return "미상"
        for name, (lo, hi) in AREA_SEGMENTS.items():
            if lo <= a < hi:
                return name
        return "미상"

    df["area_segment"] = df["area_m2"].apply(_classify)
    return df


# ------------------------------------------------------------------
# 3. 권역 분류
# ------------------------------------------------------------------
def add_zone(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    # 서울 구 → 권역
    gu_to_zone = {}
    for zone, gus in SEOUL_ZONES.items():
        for gu in gus:
            gu_to_zone[gu] = zone
    for zone, areas in METRO_ZONES.items():
        for area in areas:
            gu_to_zone[area] = zone

    df = df.copy()
    df["zone"] = df["region"].map(gu_to_zone).fillna("기타")
    return df


# ------------------------------------------------------------------
# 4. 역세권 판정
# ------------------------------------------------------------------
def nearest_station_distance(
    df_buildings: pd.DataFrame,
    df_stations: pd.DataFrame,
) -> pd.Series:
    """각 건물에서 가장 가까운 지하철역까지 거리(m)."""
    if df_buildings.empty or df_stations.empty:
        return pd.Series(dtype=float)

    b_lat = df_buildings["lat"].to_numpy()[:, None]
    b_lon = df_buildings["lon"].to_numpy()[:, None]
    s_lat = df_stations["lat"].to_numpy()[None, :]
    s_lon = df_stations["lon"].to_numpy()[None, :]

    lat1, lon1, lat2, lon2 = map(np.radians, (b_lat, b_lon, s_lat, s_lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    dist = 2 * 6_371_000 * np.arcsin(np.sqrt(a))
    return pd.Series(dist.min(axis=1), index=df_buildings.index)


def add_subway_segment(
    df: pd.DataFrame,
    df_stations: pd.DataFrame,
    geocoded: pd.DataFrame,
) -> pd.DataFrame:
    """
    geocoded: ['building_key', 'lat', 'lon']
    building_key = "region|dong|building_name"
    """
    if df.empty:
        return df
    df = df.copy()
    df["building_key"] = (
        df["region"].astype(str) + "|"
        + df["dong"].astype(str) + "|"
        + df["building_name"].astype(str)
    )
    df = df.merge(
        geocoded[["building_key", "lat", "lon"]], on="building_key", how="left"
    )

    has_coord = df["lat"].notna() & df["lon"].notna()
    df["dist_to_station_m"] = np.nan
    if has_coord.any():
        df.loc[has_coord, "dist_to_station_m"] = nearest_station_distance(
            df.loc[has_coord, ["lat", "lon"]].reset_index(drop=True),
            df_stations,
        ).values

    def _classify(d):
        if pd.isna(d):
            return "미상"
        if d <= SUBWAY_DISTANCE["1급역세권"]:
            return "1급역세권"
        if d <= SUBWAY_DISTANCE["일반역세권"]:
            return "일반역세권"
        return "비역세권"

    df["subway_segment"] = df["dist_to_station_m"].apply(_classify)
    return df
