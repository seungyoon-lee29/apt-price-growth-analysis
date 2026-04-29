"""
load_csv.py
-----------
실거래가 CSV 파일(data.go.kr 다운로드)을 로드하고 통일된 컬럼으로 정규화.
"""

from __future__ import annotations

import glob
import unicodedata
import pandas as pd
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent

# 서울 + 포함할 수도권 지역
TARGET_REGIONS = {
    # 서울 25개 구
    "서울특별시",
    # 수도권 추가 (고양시 덕양구, 성남시 분당구)
    "경기도 고양시 덕양구",
    "경기도 성남시 분당구",
}


def _find_csv(keyword: str) -> Optional[str]:
    """파일명에 keyword가 포함된 CSV를 찾는다 (macOS NFD 대응)."""
    keyword_nfc = unicodedata.normalize("NFC", keyword)
    keyword_nfd = unicodedata.normalize("NFD", keyword)
    for f in sorted(BASE_DIR.glob("*.csv")):
        name = f.name
        if (keyword_nfc in name or keyword_nfd in name) and "지하철" not in unicodedata.normalize("NFC", name):
            return str(f)
    return None


def _read_raw(path: str) -> pd.DataFrame:
    """실거래가 CSV 공통 로더. 상단 안내문(~15줄) 스킵."""
    for skip in range(20, -1, -1):
        try:
            df = pd.read_csv(path, encoding="euc-kr", skiprows=skip)
            if "시군구" in df.columns:
                return df
        except Exception:
            continue
    # cp949 시도
    for skip in range(20, -1, -1):
        try:
            df = pd.read_csv(path, encoding="cp949", skiprows=skip)
            if "시군구" in df.columns:
                return df
        except Exception:
            continue
    raise ValueError(f"Cannot parse CSV: {path}")


def _parse_sigungu(df: pd.DataFrame) -> pd.DataFrame:
    """시군구 컬럼을 시도/구/동으로 분리."""
    parts = df["시군구"].str.strip().str.split(expand=True)
    # 서울특별시 강남구 역삼동 → 3개
    # 경기도 고양시 덕양구 화정동 → 4개
    df = df.copy()
    if parts.shape[1] >= 3:
        df["시도"] = parts[0]
        # 구 = 서울이면 [1], 경기도면 [1]+" "+[2]
        def _extract_gu(row):
            if row[0] == "서울특별시":
                return row[1]
            elif row[0] in ("경기도", "인천광역시"):
                return f"{row[1]} {row[2]}" if row[2] is not None else row[1]
            return row[1]

        def _extract_dong(row):
            if row[0] == "서울특별시":
                return row[2] if len(row.dropna()) >= 3 else ""
            elif row[0] in ("경기도", "인천광역시"):
                return row[3] if len(row.dropna()) >= 4 else ""
            return row[2] if len(row.dropna()) >= 3 else ""

        df["구"] = parts.apply(_extract_gu, axis=1)
        df["동"] = parts.apply(_extract_dong, axis=1)

        # 서울 + 고양시 덕양구 + 분당구만 필터
        def _match_region(row):
            if row["시도"] == "서울특별시":
                return True
            key = f"{row['시도']} {row['구']}"
            return key in TARGET_REGIONS
        mask = df.apply(_match_region, axis=1)
        df = df[mask].copy()
    return df


def load_officetel_trade(path: str | None = None) -> pd.DataFrame:
    """오피스텔 매매 실거래가 로드 및 정규화."""
    if path is None:
        path = _find_csv("오피스텔(매매)")
    if path is None:
        raise FileNotFoundError("오피스텔 매매 CSV를 찾을 수 없습니다.")

    raw = _read_raw(path)
    df = _parse_sigungu(raw)

    out = pd.DataFrame()
    out["region"] = df["구"]
    out["dong"] = df["동"].fillna("")
    out["jibun"] = df["번지"].astype(str).str.strip()
    out["building_name"] = df["단지명"].astype(str).str.strip()
    out["area_m2"] = pd.to_numeric(df["전용면적(㎡)"], errors="coerce")
    out["deal_ym"] = df["계약년월"].astype(str)
    out["deal_day"] = df["계약일"].astype(str).str.strip()
    out["deal_date"] = pd.to_datetime(
        out["deal_ym"] + out["deal_day"].str.zfill(2),
        format="%Y%m%d", errors="coerce"
    )
    out["price_manwon"] = (
        df["거래금액(만원)"].astype(str)
        .str.replace(",", "").str.strip()
        .pipe(pd.to_numeric, errors="coerce")
    )
    out["floor"] = pd.to_numeric(df["층"], errors="coerce")
    out["build_year"] = pd.to_numeric(df["건축년도"], errors="coerce")
    out["road_name"] = df["도로명"].astype(str).str.strip() if "도로명" in df.columns else ""
    out["trade_type"] = df["거래유형"].astype(str).str.strip() if "거래유형" in df.columns else ""
    out["sigungu_raw"] = df["시군구"]
    out["sido"] = df["시도"]

    # 평당가 (1평 = 3.3058㎡)
    out["price_per_pyeong"] = out["price_manwon"] / (out["area_m2"] / 3.3058)

    # 해제 거래 제외
    if "해제사유발생일" in df.columns:
        cancel_mask = df["해제사유발생일"].astype(str).str.strip().isin(["", "-", "nan", "None"])
        out = out[cancel_mask].copy()

    return out.reset_index(drop=True)


def load_officetel_rent(path: str | None = None) -> pd.DataFrame:
    """오피스텔 전월세 실거래가 로드 및 정규화."""
    if path is None:
        path = _find_csv("오피스텔(전월세)")
    if path is None:
        raise FileNotFoundError("오피스텔 전월세 CSV를 찾을 수 없습니다.")

    raw = _read_raw(path)
    df = _parse_sigungu(raw)

    out = pd.DataFrame()
    out["region"] = df["구"]
    out["dong"] = df["동"].fillna("")
    out["jibun"] = df["번지"].astype(str).str.strip()
    out["building_name"] = df["단지명"].astype(str).str.strip()
    out["contract_type"] = df["전월세구분"].astype(str).str.strip()
    out["area_m2"] = pd.to_numeric(df["전용면적(㎡)"], errors="coerce")
    out["deal_ym"] = df["계약년월"].astype(str)
    out["deal_day"] = df["계약일"].astype(str).str.strip()
    out["deal_date"] = pd.to_datetime(
        out["deal_ym"] + out["deal_day"].str.zfill(2),
        format="%Y%m%d", errors="coerce"
    )
    out["deposit_manwon"] = (
        df["보증금(만원)"].astype(str)
        .str.replace(",", "").str.strip()
        .pipe(pd.to_numeric, errors="coerce")
    )
    out["monthly_rent"] = (
        df["월세금(만원)"].astype(str)
        .str.replace(",", "").str.strip()
        .pipe(pd.to_numeric, errors="coerce")
    )
    out["floor"] = pd.to_numeric(df["층"], errors="coerce")
    out["build_year"] = pd.to_numeric(df["건축년도"], errors="coerce")
    out["road_name"] = df["도로명"].astype(str).str.strip() if "도로명" in df.columns else ""
    out["sigungu_raw"] = df["시군구"]
    out["sido"] = df["시도"]

    return out.reset_index(drop=True)


def load_subway_stations(path: Optional[str] = None) -> pd.DataFrame:
    """지하철역 좌표 CSV 로드."""
    if path is None:
        # macOS NFD 대응: 모든 csv를 순회하며 키워드 매칭
        candidates = []
        for f in BASE_DIR.glob("*.csv"):
            name_nfc = unicodedata.normalize("NFC", f.name)
            if ("지하철" in name_nfc or "역사" in name_nfc) and "좌표" in name_nfc:
                candidates.append(f)
        if not candidates:
            raise FileNotFoundError("지하철역 좌표 CSV를 찾을 수 없습니다.")
        path = str(candidates[0])

    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=enc)
            if "위도" in df.columns:
                break
        except Exception:
            continue
    else:
        raise ValueError(f"지하철역 CSV 파싱 실패: {path}")

    out = pd.DataFrame()
    out["station_name"] = df["역명"].astype(str).str.strip()
    out["line"] = df["호선"].astype(str)
    out["lat"] = pd.to_numeric(df["위도"], errors="coerce")
    out["lon"] = pd.to_numeric(df["경도"], errors="coerce")
    return out.dropna(subset=["lat", "lon"]).reset_index(drop=True)
