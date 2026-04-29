"""
geocode.py
----------
네이버 클라우드 플랫폼 Geocoding API를 이용해 주소 → 좌표 변환.
결과를 geocode_cache.csv에 캐싱하여 중복 호출 방지.
"""

from __future__ import annotations

from pathlib import Path
import os
import time

import pandas as pd
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"

BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "geocode_cache.csv"
SAVE_EVERY = 100


def _geocode_one(address: str) -> tuple[float | None, float | None]:
    """단일 주소를 좌표로 변환."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return None, None
    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"query": address},
            headers={
                "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
                "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
            },
            timeout=5,
        )
        data = resp.json()
        if data.get("meta", {}).get("totalCount", 0) > 0:
            addr = data["addresses"][0]
            return float(addr["y"]), float(addr["x"])
    except Exception:
        pass
    return None, None


def load_cache() -> pd.DataFrame:
    """캐시 파일 로드."""
    if CACHE_PATH.exists():
        cache = pd.read_csv(CACHE_PATH)
        expected_cols = ["address", "lat", "lon"]
        for col in expected_cols:
            if col not in cache.columns:
                cache[col] = None
        return cache[expected_cols].drop_duplicates(subset=["address"], keep="last")
    return pd.DataFrame(columns=["address", "lat", "lon"])


def save_cache(cache_df: pd.DataFrame) -> None:
    cache_df = cache_df[["address", "lat", "lon"]].drop_duplicates(
        subset=["address"], keep="last"
    )
    cache_df.to_csv(CACHE_PATH, index=False, encoding="utf-8-sig")


def geocode_buildings(
    trade_df: pd.DataFrame,
    rent_df: pd.DataFrame | None = None,
    *,
    skip_api: bool = False,
) -> pd.DataFrame:
    """
    거래 데이터에서 유니크한 건물 주소를 추출하고 지오코딩.

    Returns:
        DataFrame with columns: [building_key, address, lat, lon]
        building_key = "region|dong|building_name"
    """
    # 유니크 건물 추출
    dfs = [trade_df[["region", "dong", "building_name", "road_name", "sigungu_raw"]]]
    if rent_df is not None:
        dfs.append(rent_df[["region", "dong", "building_name", "road_name", "sigungu_raw"]])

    buildings = pd.concat(dfs).drop_duplicates(subset=["region", "dong", "building_name"])
    buildings["building_key"] = (
        buildings["region"].astype(str) + "|"
        + buildings["dong"].astype(str) + "|"
        + buildings["building_name"].astype(str)
    )

    # 주소 생성: 도로명이 있으면 "시군구(앞2단어) + 도로명", 없으면 "시군구 + 동 + 건물명"
    def _make_address(row):
        road = str(row.get("road_name", "")).strip()
        sigungu = str(row.get("sigungu_raw", "")).strip()
        if road and road not in ("-", "nan", ""):
            # 시군구에서 동 제외하고 도로명 붙이기
            parts = sigungu.split()
            base = " ".join(parts[:2]) if len(parts) >= 2 else sigungu
            return f"{base} {road}"
        dong = str(row.get("dong", "")).strip()
        name = str(row.get("building_name", "")).strip()
        return f"{sigungu} {name}" if name else sigungu

    buildings["address"] = buildings.apply(_make_address, axis=1)

    # 캐시 로드
    cache = load_cache()
    cached_success = set(
        cache.loc[cache["lat"].notna() & cache["lon"].notna(), "address"].tolist()
    )

    # 좌표가 없는 캐시 엔트리는 재시도 대상으로 남긴다.
    to_geocode = buildings[~buildings["address"].isin(cached_success)][["address"]].drop_duplicates()

    if skip_api:
        print(
            f"  지오코딩 API 스킵. 성공 캐시 {len(cached_success)}건만 사용"
        )
    elif len(to_geocode) > 0:
        print(f"  지오코딩 필요: {len(to_geocode)}건 (성공 캐시: {len(cached_success)}건)")
        pending_rows: list[dict[str, float | None | str]] = []
        for idx, row in enumerate(
            tqdm(to_geocode.itertuples(index=False), total=len(to_geocode), desc="  Geocoding"),
            start=1,
        ):
            lat, lon = _geocode_one(row.address)
            pending_rows.append({"address": row.address, "lat": lat, "lon": lon})
            time.sleep(0.05)  # rate limit

            if len(pending_rows) >= SAVE_EVERY or idx == len(to_geocode):
                pending_df = pd.DataFrame(pending_rows)
                if cache.empty:
                    cache = pending_df
                else:
                    cache = pd.concat([cache, pending_df], ignore_index=True)
                save_cache(cache)
                cache = load_cache()
                pending_rows.clear()

        print(f"  지오코딩 완료. 캐시 저장: {len(cache)}건")
    else:
        print(f"  모든 주소 캐시 히트 ({len(cached_success)}건)")

    # 건물 키에 좌표 매핑
    result = buildings[["building_key", "address"]].merge(
        cache[["address", "lat", "lon"]], on="address", how="left"
    )

    hit = result["lat"].notna().sum()
    print(f"  좌표 매핑 성공: {hit}/{len(result)} ({hit/len(result)*100:.1f}%)")

    return result[["building_key", "lat", "lon"]].drop_duplicates(subset=["building_key"])
