"""해양 데이터 사례 연구 — README '사례 연구' 섹션의 모든 차트를 재현한다.

두 개의 실측 데이터로 60개 도구가 하나의 분석 스토리로 이어지는 과정을 보여준다:

  1. NOAA NDBC 46042 부이 (몬터레이만) 2023년 표준기상 관측
     — 최초 실행 시 ndbc.noaa.gov 에서 자동 다운로드(~4MB), 이후 캐시 사용
  2. 한국 해양안전심판원(KMST) 재결 139건 (examples/data/kmst_accidents.csv 동봉)

실행:

    MCP_OUTPUT_DIR=outputs python examples/maritime_case_study.py
    # README용 이미지까지 갱신하려면:
    python examples/maritime_case_study.py --ship-readme-images

모든 차트는 MCP 도구의 무편집 출력이다. 각 장(chapter)의 주석은 "왜 이
도구/디자인인가"를 설명한다 — README의 사례 연구 본문과 1:1로 대응한다.
"""
import os
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

BUOY_URL = ("https://www.ndbc.noaa.gov/view_text_file.php"
            "?filename=46042h2023.txt.gz&dir=data/historical/stdmet/")
BUOY_RAW = ROOT / "examples" / "data" / "buoy_46042_2023_raw.txt"
BUOY_CSV = ROOT / "examples" / "data" / "buoy_46042_2023.csv"
KMST_CSV = ROOT / "examples" / "data" / "kmst_accidents.csv"
README_IMAGES = ROOT / "docs" / "images" / "maritime"

# 결측 센티널: NDBC는 99/999/9999로 결측을 표기한다.
_SENTINELS = [("WDIR", 999), ("WSPD", 99), ("GST", 99), ("WVHT", 99),
              ("DPD", 99), ("APD", 99), ("PRES", 9999), ("ATMP", 999),
              ("WTMP", 999)]
_RENAME = {"WDIR": "wind_dir", "WSPD": "wind_speed", "GST": "gust",
           "WVHT": "wave_height", "DPD": "dominant_period",
           "APD": "avg_period", "PRES": "pressure", "ATMP": "air_temp",
           "WTMP": "water_temp"}


def prepare_buoy_csv() -> str:
    """NDBC 원본을 내려받아 분석용 CSV로 변환한다 (캐시 존중)."""
    import pandas as pd

    if BUOY_CSV.exists():
        return str(BUOY_CSV)
    if not BUOY_RAW.exists():
        print(f"[다운로드] {BUOY_URL}")
        urllib.request.urlretrieve(BUOY_URL, BUOY_RAW)
    df = pd.read_csv(BUOY_RAW, sep=r"\s+", skiprows=[1]).rename(columns={"#YY": "YY"})
    df["datetime"] = pd.to_datetime(
        dict(year=df.YY, month=df.MM, day=df.DD, hour=df.hh, minute=df.mm)
    )
    out = df[["datetime", *(_RENAME)]].copy()
    for col, bad in _SENTINELS:
        out.loc[out[col] >= bad, col] = pd.NA
    out = out.rename(columns=_RENAME)
    out.to_csv(BUOY_CSV, index=False)
    print(f"[변환] {BUOY_CSV.name}: {out.shape[0]:,}행")
    return str(BUOY_CSV)


def main() -> None:
    ship = "--ship-readme-images" in sys.argv
    os.environ.setdefault("MPLBACKEND", "Agg")

    from data_analysis import theming
    from data_analysis.tools import composition, distribution, ml, statistics, visualization as vz

    buoy, kmst = prepare_buoy_csv(), str(KMST_CSV)
    theming.apply("modern")
    made: dict[str, str] = {}

    # ── 1장. 트렌드: 원시선을 지우지 않는 이동평균 ───────────────────────
    # 디자인 — 원시 관측(뮤트)이 배경에 남아 있어 스무딩이 데이터를
    # 감추지 않는다. 트렌드는 프라이머리 한 색만 쓴다.
    made["rolling.png"] = vz.plot_rolling(
        buoy, "datetime", "wave_height", window=252,
        title="Monterey Bay 유의파고 — 7일 이동평균 (NDBC 46042, 2023)")

    # ── 2장. 관계: 점이 만 개를 넘으면 산점도는 거짓말을 한다 ───────────
    # 디자인 — 밀도를 시퀀셜 램프(한 색상, 밝음→어두움)로 인코딩.
    made["hexbin.png"] = vz.plot_hexbin(
        buoy, "wind_speed", "wave_height",
        title="풍속 vs 유의파고 밀도 (12,585 관측)")

    # ── 3장. 분포: 검정(수치)과 Q-Q(시각)는 한 세트다 ───────────────────
    norm = statistics.test_normality(buoy, column="wave_height")
    made["qq.png"] = distribution.plot_qq(
        buoy, "wave_height", title="유의파고 Q-Q — 오른쪽 꼬리가 극한 파고다")["plot_path"]
    print(f"[3장] Shapiro p={norm['p_value']} → {norm['interpretation']}")

    # ── 4장. 예측 가능성: 정확도 하나가 아니라 곡선 두 개로 진단 ────────
    # 디자인 — train/validation 두 시리즈 + ±1σ 밴드(채움 15%).
    lc = ml.plot_learning_curve(
        buoy, "wave_height", cv=3,
        feature_columns=["wind_speed", "gust", "dominant_period",
                         "avg_period", "pressure"])
    made["learning_curve.png"] = lc["plot_path"]
    print(f"[4장] 검증 R²={lc['final_validation_score']}, "
          f"일반화 갭={lc['generalization_gap']}")

    # ── 5장. 사고 데이터: 우선순위(파레토)와 기여 분해(워터폴) ──────────
    # 디자인 — 파레토는 막대(개별 비율)와 누적선을 '단일 %축'에 올린다.
    # 워터폴은 +/−를 팔레트 1·2번 색으로 나누고 전 막대를 직접 라벨.
    pareto = composition.plot_pareto(
        kmst, "사고유형", title="해양사고 유형 파레토 (KMST 재결 139건)")
    made["pareto.png"] = pareto["plot_path"]
    made["waterfall.png"] = composition.plot_waterfall(
        kmst, "사고유형", "업무정지_개월",
        title="사고유형별 업무정지 처분 기여 (총 개월)")["plot_path"]
    print(f"[5장] 80%를 만드는 유형: {', '.join(pareto['categories_for_80pct'])}")

    # ── 6장. 답이 숫자 하나라면: 차트를 그리지 않는 것이 정답 ───────────
    tile = distribution.stat_tile(
        buoy, "wave_height", agg="max", compare_agg="mean",
        title="2023 최대 유의파고 (m)")
    made["stat_tile.png"] = tile["plot_path"]
    print(f"[6장] 최대 {tile['value']}m / 평균 {tile['compare_value']}m")

    print(f"\n생성된 차트 {len(made)}장:")
    for name, path in made.items():
        print(f"  {name} ← {path}")

    if ship:
        README_IMAGES.mkdir(parents=True, exist_ok=True)
        for name, path in made.items():
            shutil.copy(path, README_IMAGES / name)
        print(f"\nREADME 이미지 갱신 → {README_IMAGES}")


if __name__ == "__main__":
    main()
