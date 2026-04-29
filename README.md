# 공공 실거래가 아파트 상승률 분석

국토교통부 아파트 매매 실거래가 공공 API를 활용하여 **특정 시기별 아파트 가격 상승률**을 비교·분석하는 프로젝트입니다.

## 분석 대상 지역

| 지역 | 법정동코드(LAWD_CD) |
|------|---------------------|
| 성남시 분당구 | `41135` |
| 수원시 영통구 | `41117` |
| 광교 (영통구 내 이의동·하동·원천동) | 영통구 데이터에서 필터링 |

## 핵심 분석 내용

1. **시기별 가격 상승률 비교**: 3개월 윈도우 기반 중위 평당가 상승률 산출
2. **동별·단지별 상승률 랭킹**: 거래량 필터링 포함
3. **주상복합 제외 분석**: 보수적 제외 리스트 적용
4. **잔여 상승여력 추정**: 과거 상승률 패턴 기반 프로젝션

### 비교 기간

| 구분 | 기준 윈도우 | 비교 윈도우 |
|------|------------|------------|
| 기간 1 (2017→2022) | 2017년 4~6월 | 2022년 4~6월 |
| 기간 2 (2025→현재) | 2025년 6~8월 | 2026년 2~4월 |

### 산출 공식

```
상승률(%) = (비교 윈도우 중위 평당가 / 기준 윈도우 중위 평당가 - 1) × 100
```

- **평당가** = 거래금액(만원) ÷ (전용면적㎡ × 0.3025)
- 단월 비교와 3개월 윈도우 비교를 모두 산출하며, 3개월 윈도우가 거래량 부족에 의한 노이즈를 줄여주므로 더 안정적입니다.

---

## 필요한 API 키

이 프로젝트를 실행하려면 아래 API 키가 필요합니다.

### 1. 국토교통부 아파트 매매 실거래가 상세 자료 API (필수)

아파트 실거래 데이터를 가져오는 핵심 API입니다.

- **발급처**: [공공데이터포털 (data.go.kr)](https://www.data.go.kr/data/15057511/openapi.do)
- **API명**: `국토교통부_아파트매매 실거래 상세 자료`
- **Endpoint**: `RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`
- **환경변수명**: `MOLIT_APT_TRADE_DETAIL_API_KEY`

**발급 방법:**
1. [공공데이터포털](https://www.data.go.kr/) 회원가입 및 로그인
2. 위 링크에서 "활용신청" 클릭
3. 신청 후 마이페이지에서 **일반 인증키(Encoding)** 복사
4. `.env` 파일에 추가

### 2. 네이버 클라우드 플랫폼 Geocoding API (선택)

건물 주소를 위경도 좌표로 변환하여 역세권 판정에 사용합니다. 지오코딩이 필요 없으면 `--skip-geocode` 옵션으로 건너뛸 수 있습니다.

- **발급처**: [네이버 클라우드 플랫폼](https://www.ncloud.com/product/applicationService/maps)
- **API명**: Maps > Geocoding
- **환경변수명**: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

**발급 방법:**
1. [네이버 클라우드 플랫폼](https://www.ncloud.com/) 회원가입 및 로그인
2. 콘솔 > AI·Application Service > Maps 에서 애플리케이션 등록
3. Geocoding 서비스 활성화
4. Client ID와 Client Secret을 `.env` 파일에 추가

---

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/seungyoon-lee29/apt-price-growth-analysis.git
cd apt-price-growth-analysis
```

### 2. Python 환경 설정

Python 3.10 이상을 권장합니다.

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다:

```env
MOLIT_APT_TRADE_DETAIL_API_KEY=여기에_공공데이터포털_인증키_붙여넣기
NAVER_CLIENT_ID=여기에_네이버_클라이언트_ID
NAVER_CLIENT_SECRET=여기에_네이버_클라이언트_시크릿
```

### 4. 파이프라인 실행

```bash
# 전체 파이프라인 실행
python pipeline.py

# 지오코딩 건너뛰기 (네이버 API 없을 때)
python pipeline.py --skip-geocode
```

### 5. 스모크 테스트

API 호출 없이 mock 데이터로 파이프라인 로직을 검증합니다:

```bash
python smoke_test.py
```

---

## 프로젝트 구조

```
├── config.py              # 상수, 권역 분류, 세그먼트 기준 정의
├── fetch_molit.py         # 국토부 실거래가 API 호출 및 XML 파싱
├── fetch_subway.py        # 지하철역 좌표 데이터 로드
├── geocode.py             # 네이버 Geocoding API (주소→좌표 변환, 캐시)
├── load_csv.py            # CSV 데이터 로드 유틸리티
├── enrich.py              # 세그먼트 부착 (연차/면적/권역/역세권)
├── screen.py              # 가격 추이, 수익률 산출, 저평가 탐지
├── visualize.py           # 차트 생성 (matplotlib)
├── pipeline.py            # 메인 파이프라인 (오피스텔 스크리닝)
├── analyze_seoul_trends.py # 서울 오피스텔 월별 추이 분석
├── smoke_test.py          # mock 데이터 기반 스모크 테스트
├── requirements.txt       # Python 의존성
├── geocode_cache.csv      # 지오코딩 결과 캐시
├── BUNDANG_APT_GROWTH_HANDOFF.md  # 분석 결과 요약 문서
└── output/
    └── reports/           # 분석 결과 CSV 파일들
```

## 출력 파일 설명

`output/reports/` 디렉토리에 분석 결과가 CSV로 저장됩니다.

### 분당구

| 파일명 패턴 | 내용 |
|------------|------|
| `bundang_apt_trades_policy_windows_*.csv` | 원본 거래 데이터 (전체/주상복합 제외/제외된 거래) |
| `bundang_apt_growth_*_by_dong_*.csv` | 동별 상승률 |
| `bundang_apt_growth_*_by_apt_*.csv` | 단지별 상승률 |
| `bundang_apt_growth_*_by_apt_avg_volume_*.csv` | 평균 거래량 이상 단지만 필터링한 상승률 |
| `bundang_apt_upside_*_by_dong_*.csv` | 동별 잔여 상승여력 추정 |

### 수원시 영통구

`suwon_yeongtong_*` 접두사로 분당구와 동일한 구조입니다.

### 광교

`gwanggyo_*` 접두사로 두 가지 기준의 분석 결과가 포함됩니다:
- `gwanggyo_dong_area_*`: 광교 생활권 (이의동·하동·원천동)
- `gwanggyo_named_apts_*`: 단지명에 "광교"가 포함된 아파트

### 주상복합 제외

- `mixed_use_exclusion_list.csv`: 제외 대상 주상복합 단지 목록
- 파일명에 `no_mixed_use`가 포함된 파일은 주상복합을 제외한 결과입니다.

---

## 의존성

| 패키지 | 용도 |
|--------|------|
| pandas | 데이터 처리 |
| requests | API 호출 |
| python-dotenv | 환경변수 로드 (.env) |
| matplotlib / seaborn | 차트 생성 |
| openpyxl / xlrd | Excel 파일 입출력 |
| pyarrow | Parquet 캐시 저장 |
| tqdm | 진행률 표시 |

---

## 주의사항

- 공공데이터포털 API는 **일일 호출 횟수 제한**이 있습니다. 대량 수집 시 캐시를 활용하세요.
- 거래량이 적은 단지/기간은 중위값이 불안정할 수 있으므로, 결과 해석 시 반드시 `base_count`, `end_count` 등 거래 건수를 함께 확인하세요.
- 주상복합 제외 리스트는 기사 및 매물 정보 기반의 보수적 기준이며, 공식 분류가 아닙니다.

## 라이선스

이 프로젝트는 공공데이터를 활용한 개인 분석 프로젝트입니다. 데이터 출처: [공공데이터포털](https://www.data.go.kr/)
