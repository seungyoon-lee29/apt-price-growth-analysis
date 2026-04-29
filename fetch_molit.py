"""
fetch_molit.py
--------------
국토교통부 실거래가 Open API 호출 → DataFrame 변환 → parquet 캐시
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import pandas as pd
import requests

from .config import (
    MOLIT_API_KEY, MOLIT_ENDPOINTS, RAW_DIR,
    REQUEST_DELAY_SEC, MAX_RETRIES,
)


# ------------------------------------------------------------------
# 저수준: 단일 (지역코드, 년월) API 호출
# ------------------------------------------------------------------
def _fetch_single(
    dataset: str,
    lawd_cd: str,
    deal_ymd: str,
    num_rows: int = 1000,
) -> list[dict]:
    """
    한 개 (지역코드, 년월) 쿼리를 페이지네이션하며 전부 긁어온다.
    반환: 레코드 리스트 (row == XML <item>)
    """
    url = MOLIT_ENDPOINTS[dataset]
    records: list[dict] = []
    page_no = 1

    while True:
        params = {
            "serviceKey": MOLIT_API_KEY,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": page_no,
            "numOfRows": num_rows,
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(1 + attempt)

        items, total_count = _parse_xml(resp.text)
        records.extend(items)

        # 페이지네이션 종료 조건
        if page_no * num_rows >= total_count or len(items) == 0:
            break
        page_no += 1
        time.sleep(REQUEST_DELAY_SEC)

    return records


def _parse_xml(xml_text: str) -> tuple[list[dict], int]:
    """국토부 실거래가 API 응답 XML → (records, totalCount)"""
    root = ET.fromstring(xml_text)

    # 에러 처리
    result_code = root.findtext(".//resultCode")
    if result_code and result_code not in ("00", "000"):
        msg = root.findtext(".//resultMsg") or "unknown"
        raise RuntimeError(f"MOLIT API error {result_code}: {msg}")

    total_count = int(root.findtext(".//totalCount") or 0)
    records = []
    for item in root.findall(".//item"):
        records.append({child.tag: (child.text or "").strip() for child in item})
    return records, total_count


# ------------------------------------------------------------------
# 고수준: 기간 × 지역 × 데이터셋 수집
# ------------------------------------------------------------------
def fetch_range(
    dataset: str,
    region_codes: dict[str, str],
    start_ym: str,   # "202401"
    end_ym: str,     # "202604"
    cache: bool = True,
) -> pd.DataFrame:
    """
    region_codes: {"강남구": "11680", ...}
    """
    cache_path = RAW_DIR / f"{dataset}_{start_ym}_{end_ym}.parquet"
    if cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    all_months = _month_range(start_ym, end_ym)
    frames: list[pd.DataFrame] = []

    for region_name, code in region_codes.items():
        for ym in all_months:
            try:
                rows = _fetch_single(dataset, code, ym)
            except Exception as e:
                print(f"[WARN] {dataset} {region_name} {ym} skipped: {e}")
                continue
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df["region"] = region_name
            df["lawd_cd"] = code
            df["deal_ymd"] = ym
            frames.append(df)
            time.sleep(REQUEST_DELAY_SEC)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    if cache:
        out.to_parquet(cache_path, index=False)
    return out


def _month_range(start_ym: str, end_ym: str) -> list[str]:
    """'202401' ~ '202604' → ['202401', '202402', ...]"""
    months = []
    y, m = int(start_ym[:4]), int(start_ym[4:])
    ey, em = int(end_ym[:4]), int(end_ym[4:])
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


# ------------------------------------------------------------------
# 데이터셋별 정제 (컬럼 표준화)
# ------------------------------------------------------------------
def normalize_offi_trade(df: pd.DataFrame) -> pd.DataFrame:
    """오피스텔 매매 자료 → 표준 컬럼"""
    if df.empty:
        return df
    rename_map = {
        "offiNm": "building_name",
        "umdNm": "dong",
        "jibun": "jibun",
        "excluUseAr": "area_m2",          # 전용면적
        "dealAmount": "price_manwon",      # 거래금액 (만원, 콤마 포함 문자열)
        "floor": "floor",
        "buildYear": "build_year",
        "dealYear": "deal_year",
        "dealMonth": "deal_month",
        "dealDay": "deal_day",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df["price_manwon"] = (
        df["price_manwon"].astype(str).str.replace(",", "").str.strip()
    )
    df["price_manwon"] = pd.to_numeric(df["price_manwon"], errors="coerce")
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["build_year"] = pd.to_numeric(df["build_year"], errors="coerce")
    df["floor"] = pd.to_numeric(df["floor"], errors="coerce")
    df["deal_date"] = pd.to_datetime(
        df["deal_year"] + "-" + df["deal_month"].str.zfill(2) + "-" + df["deal_day"].str.zfill(2),
        errors="coerce",
    )
    # 평당가(만원/평) = 가격 / (전용면적 * 0.3025)
    df["price_per_pyeong"] = df["price_manwon"] / (df["area_m2"] * 0.3025)
    return df


def normalize_offi_rent(df: pd.DataFrame) -> pd.DataFrame:
    """오피스텔 전월세 자료 → 표준 컬럼"""
    if df.empty:
        return df
    rename_map = {
        "offiNm": "building_name",
        "umdNm": "dong",
        "jibun": "jibun",
        "excluUseAr": "area_m2",
        "deposit": "deposit_manwon",       # 보증금 (만원, 콤마)
        "monthlyRent": "monthly_rent",     # 월세 (만원, 0이면 순수 전세)
        "floor": "floor",
        "buildYear": "build_year",
        "dealYear": "deal_year",
        "dealMonth": "deal_month",
        "dealDay": "deal_day",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for col in ["deposit_manwon", "monthly_rent"]:
        df[col] = df[col].astype(str).str.replace(",", "").str.strip()
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["build_year"] = pd.to_numeric(df["build_year"], errors="coerce")
    df["deal_date"] = pd.to_datetime(
        df["deal_year"] + "-" + df["deal_month"].str.zfill(2) + "-" + df["deal_day"].str.zfill(2),
        errors="coerce",
    )
    df["contract_type"] = df["monthly_rent"].apply(
        lambda x: "전세" if pd.isna(x) or x == 0 else "월세"
    )
    return df
