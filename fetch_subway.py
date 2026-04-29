"""
fetch_subway.py
---------------
서울교통공사 지하철역 좌표 수집 → 역세권 판정용 기준 데이터

데이터 출처:
- 서울 열린데이터광장: 서울교통공사_지하철역 위치 정보
- 공공데이터포털에도 동일 데이터 존재
- CSV 다운로드 방식이 API보다 간편하므로 CSV 스냅샷 기반 로직으로 구성
"""

from __future__ import annotations

import pandas as pd

from .config import RAW_DIR


SUBWAY_CACHE = RAW_DIR / "subway_stations.parquet"


def load_subway_stations(csv_path: str | None = None) -> pd.DataFrame:
    """
    지하철역 좌표 로드.
    csv_path 가 주어지면 CSV → parquet 캐시. 아니면 캐시에서 로드.

    기대 컬럼:
      - station_name, line, lat, lon
    서울 열린데이터광장 원본 컬럼명이 다르면 여기서 리네임.
    """
    if csv_path:
        raw = pd.read_csv(csv_path, encoding="utf-8-sig")
        # 원본 컬럼 예: "역사명", "호선", "위도", "경도"
        rename_map = {
            "역사명": "station_name",
            "전철역명": "station_name",
            "호선": "line",
            "노선명": "line",
            "위도": "lat",
            "경도": "lon",
        }
        raw = raw.rename(columns={k: v for k, v in rename_map.items() if k in raw.columns})
        keep = [c for c in ["station_name", "line", "lat", "lon"] if c in raw.columns]
        df = raw[keep].dropna(subset=["lat", "lon"]).drop_duplicates(
            subset=["station_name", "line"]
        )
        df.to_parquet(SUBWAY_CACHE, index=False)
        return df

    if SUBWAY_CACHE.exists():
        return pd.read_parquet(SUBWAY_CACHE)

    raise FileNotFoundError(
        "지하철역 좌표 캐시가 없습니다. "
        "서울 열린데이터광장에서 '지하철역 위치 정보' CSV를 받아 "
        "load_subway_stations(csv_path=...)로 한 번 불러주세요."
    )
