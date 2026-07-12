<div align="center">

# Data-Analyze-MCP

**자연어 한 마디로 데이터 분석, 전처리, 시각화까지 — LLM을 위한 MCP 데이터 분석 서버**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://modelcontextprotocol.io/)
[![Tools](https://img.shields.io/badge/Tools-60-2a78d6.svg)](#mcp-server-tools-60-total)
[![Claude](https://img.shields.io/badge/Claude-Desktop%20%7C%20Code-d97757.svg)](https://claude.ai/)
[![CI](https://github.com/chaeminyoon/Data-Analyze-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/chaeminyoon/Data-Analyze-MCP/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

[빠른 시작](#quick-start) · [시연](#demo--분석--처리--시각화) · [활용 시나리오](#활용-시나리오) · [차트 테마](#chart-themes) · [도구 목록](#mcp-server-tools-60-total) · [LLM 연동 가이드](docs/LLM_INTEGRATION.md)

<img src="docs/images/showcase.png" alt="자연어 요청으로 생성된 차트와 테마 예시" width="90%">

</div>

---

## Features

- **Auto Visualization** — 어떤 CSV를 넣어도 컬럼 역할(수치/범주/날짜/ID 등)을 자동 판별해 알맞은 차트를 추천하고 그 자리에서 렌더링 (`recommend_visualizations` → `plot_auto`)
- **차트 테마 시스템** — `modern`(기본), `dark`, `minimal`, `vibrant`, `classic` 5종. 대화 중 "어둡게 바꿔줘" 한 마디면 이후 모든 차트의 디자인이 전환됨 (`set_chart_style`)
- **계산으로 검증된 팔레트** — 모든 테마가 4가지 접근성 검사(OKLCH 명도 밴드·채도 하한·3종 색각이상 시뮬레이션 인접쌍 분리 ΔE≥12·배경 대비 3:1)를 **pytest로 강제** 통과. 검증기는 순수 파이썬 구현([`palette_check.py`](src/data_analysis/palette_check.py))으로 CI에서 매 커밋 실행
- **결과 즉시 확인** — 차트를 MCP 이미지로 대화창에 인라인 표시(`view_chart`), CLI에서는 OS 뷰어 자동 오픈, 웹 결과 갤러리(`data-analysis-viewer`)로 실시간 모니터링
- **60개 전문 도구** — 프로파일링, 전처리(결측/이상치/인코딩/스케일링), 피처 엔지니어링, 정적/인터랙티브 시각화, 구성·비교 차트, 분포·데이터 품질 진단, 가설검정, 모델 비교/평가/튜닝/진단
- **한국어 우선** — 한글 컬럼명과 축 레이블 지원, 한국어 응답 시스템 프롬프트 내장
- **어떤 데이터든 안전하게** — 빈 파일, 전체 NaN, 단일 클래스, 고카디널리티 등 엣지 입력도 크래시 없이 명확한 에러로 응답하여 LLM이 스스로 회복

## Demo — 분석 → 처리 → 시각화

실제 사용 흐름 그대로입니다. 사용자는 자연어로 묻고, LLM이 MCP 툴을 골라 호출하며,
아래 수치와 차트는 전부 서버가 실제로 반환한 무편집 결과물입니다.

**1. 분석** — 데이터를 파악합니다.

```
You: house_price.csv 분석해줘
AI:  545행 x 12컬럼입니다. price 컬럼에서 이상치 34개(6.2%)가 탐지됩니다.
     [get_dataset_info, detect_outliers 호출]
```

**2. 처리** — 이상치를 제거하고, 전/후를 한 장으로 비교합니다.

```
You: 이상치 제거하고 전후를 비교해서 보여줘
AI:  34행을 제거했습니다. (545, 12) → (511, 12)
     전/후 비교 차트입니다 — 왼쪽의 130만 이상 꼬리가 오른쪽에서 사라졌습니다.
     [remove_outliers → plot_before_after → view_chart 호출, 차트 인라인 표시]
```

<div align="center"><img src="docs/images/demo_before_after.png" width="92%"></div>

`plot_before_after`는 디스크의 원본과 캐시의 처리본을 같은 축으로 나란히 그려,
전처리가 무엇을 바꿨는지 한 장에서 비교됩니다.

**3. 시각화** — 정제된 데이터로 자동 추천을 받아 그립니다.

```
You: 어떤 시각화가 좋을지 추천하고 그려줘
AI:  area-price 상관이 |r|=0.80으로 가장 강합니다 (제거 전 0.33 → 제거 후 0.80).
     산점도를 생성했고 bedrooms로 색을 구분했습니다.
     [recommend_visualizations → plot_auto → view_chart 호출, 차트 인라인 표시]
```

<div align="center"><img src="docs/images/demo_scatter.png" width="75%"></div>

전처리가 시각화를 바꿉니다 — 이상치 제거만으로 상관계수가 0.33에서 0.80으로 올라간 것이
그대로 차트에 드러납니다. 이 대화의 실제 MCP 요청/응답 JSON은
[docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md)에 있습니다.

## Chart Themes

모든 차트 도구는 활성 테마를 통해 그려집니다. 대화 중 전환할 수 있고
(`set_chart_style`), 서버 시작 시 `MCP_CHART_THEME` 환경변수로도 지정합니다.

| dark | minimal | vibrant |
|:---:|:---:|:---:|
| <img src="docs/images/demo_dark.png" width="100%"> | <img src="docs/images/demo_minimal.png" width="100%"> | <img src="docs/images/demo_vibrant.png" width="100%"> |

| 테마 | 용도 |
|---|---|
| `modern` (기본) | 차분한 전문가 팔레트, 옅은 그리드, 좌측 정렬 타이틀 |
| `dark` | 다크 배경 전용으로 재계산된 팔레트 — 대시보드, 발표 |
| `minimal` | 뮤트 톤, 그리드 최소화 — 보고서, 논문 |
| `vibrant` | 고채도, 강한 대비 — 프레젠테이션 강조 |
| `classic` | matplotlib/plotly 기본 스타일 (레거시 호환용, 접근성 미검증) |

`classic`을 제외한 모든 팔레트는 색각이상 시뮬레이션(protan/deutan/tritan)에서
인접 슬롯 간 ΔE ≥ 25를 유지하고, 각 테마의 배경 위에서 대비 3:1을 전부 충족합니다.
슬롯 **순서 자체가 안전장치**입니다 — 인접쌍 최소 ΔE를 최대화하는 순서를 전수 탐색으로
골랐기 때문에, 시리즈 색을 임의로 재배열하면 테스트가 실패합니다. 팔레트가 8색을
넘어야 하는 상황은 색을 늘리는 대신 'Other' 접기(`fold_other`)나 소형 다중
(`plot_small_multiples`)으로 해결합니다. 이중축(두 y축) 도구는 의도적으로 없습니다.

## 활용 시나리오

60개 도구는 낱개가 아니라 **작업 흐름**으로 쓰일 때 힘을 냅니다. 자주 쓰는 네 가지
흐름과, 각 단계에서 LLM이 실제로 호출하게 되는 도구 체인입니다.

### 1. 처음 보는 데이터, 10분 안에 파악하기

```
"이 CSV 믿어도 되는 데이터야? 구조부터 품질까지 훑어줘"
```

`profile_dataset` → `plot_missingness`(결측이 무작위인지 구조적인지) →
`find_duplicates` → `recommend_visualizations` → `plot_auto` 상위 추천 렌더링.
결측 진단이 먼저인 이유: **품질을 모르는 데이터의 차트는 그럴듯한 거짓말**이 되기
쉽습니다. 결측 5% 이상이면 자동 추천 목록에 결측 진단이 알아서 올라옵니다.

### 2. 보고서·발표 자료 만들기

```
"보고서용으로 미니멀하게 바꾸고, 매출 상위 요인을 파레토로 정리해줘"
```

`set_chart_style("minimal")` → `plot_pareto`(상위 몇 개가 80%인지) →
`plot_stacked_bar(normalize=True)`(구성 비교) → `stat_tile`(핵심 수치 카드) →
생성된 PNG를 문서에 그대로 삽입. 발표 슬라이드는 `set_chart_style("dark")` 한
번이면 같은 차트가 다크 배경용 팔레트로 다시 나옵니다 — 모든 테마가 색각이상·대비
검사를 통과했으므로 **회의실 프로젝터에서도, 색각이상 동료에게도 같은 정보**가
전달됩니다.

### 3. 모델 개발 루프

```
"이탈 예측 모델 만들어보고, 데이터를 더 모아야 할지 판단해줘"
```

`compare_models`(베이스라인) → `tune_hyperparameters` →
`plot_learning_curve`(검증 곡선이 아직 오르는 중이면 데이터 추가가 답) →
`plot_roc_pr`(불균형이면 PR이 진실) → `plot_calibration`(임계값 기반 의사결정 전제)
→ 회귀라면 `plot_residuals`(R²가 못 보는 구조 결함). 정확도 숫자 하나가 아니라
**"왜 이 모델을 믿어도 되는가"의 증거 세트**가 남습니다.

### 4. 비즈니스 질문에 차트 하나로 답하기

| 질문 | 한 방에 답하는 도구 |
|---|---|
| "매출의 80%를 만드는 채널은?" | `plot_pareto` |
| "전분기 대비 총액이 왜 줄었지?" | `plot_waterfall` (항목별 기여 분해) |
| "지역×상품별 평균 단가는?" | `plot_pivot_heatmap` |
| "작년과 올해, 지점별로 뭐가 달라졌어?" | `plot_slope` |
| "이번 달 핵심 지표 하나만" | `stat_tile` (답이 숫자면 차트를 그리지 않는 것이 정답) |

## Quick Start

```bash
git clone https://github.com/chaeminyoon/Data-Analyze-MCP.git
cd Data-Analyze-MCP
pip install -e .                        # 서버 + 클라이언트 + 뷰어 설치
python generate_all_test_data.py        # 데모 데이터 3종 생성 (선택)
```

### Claude Desktop / Claude Code

`claude_desktop_config.json` 또는 `.mcp.json`:

```json
{
  "mcpServers": {
    "data-analysis": {
      "command": "data-analysis"
    }
  }
}
```

이후 Claude에게 그냥 말하면 됩니다: *"house_price.csv 분석하고 이상치 제거한 다음 시각화해줘"*
— 차트가 대화창 안에 바로 표시됩니다.

### OpenAI API (동봉 클라이언트)

```bash
export OPENAI_API_KEY=sk-... MODEL_NAME=gpt-4o-mini
python data_client.py
```

턴이 끝날 때마다 새 차트가 OS 기본 뷰어로 자동으로 열립니다 (`AUTO_OPEN_RESULTS=0`으로 끔).

### 실시간 결과 갤러리

```bash
data-analysis-viewer            # http://127.0.0.1:8400
```

분석과 나란히 띄워두면 생성되는 결과물이 3초마다 자동 갱신됩니다.
PNG는 그리드로 렌더링, 인터랙티브 Plotly HTML은 새 탭으로 열립니다. 추가 의존성 없음.

## MCP Server Tools (60 Total)

<details>
<summary><b>Exploration & Profiling</b> (4) — 데이터 파악</summary>

| Tool | Description |
|------|-------------|
| `get_dataset_info` | 데이터셋 기본 정보 (shape, dtypes, 결측치) |
| `profile_dataset` | 종합 프로파일링 (통계량, 상관관계, 분포) |
| `detect_data_types` | 컬럼 역할 자동 분류 (수치/범주/날짜/ID/텍스트) |
| `find_duplicates` | 중복 행 탐지 및 카운트 |
</details>

<details>
<summary><b>Preprocessing</b> (5) — 정제</summary>

| Tool | Description |
|------|-------------|
| `handle_missing_values` | 결측치 처리 (mean, median, mode, drop, ffill) |
| `detect_outliers` | 이상치 탐지 (IQR, Z-score) |
| `remove_outliers` | 이상치 제거 (탐지된 전체) |
| `encode_categorical` | 범주형 인코딩 (Label, One-hot) |
| `scale_features` | 스케일링 (Standard, MinMax) |
</details>

<details>
<summary><b>Feature Engineering</b> (3) — 피처 생성</summary>

| Tool | Description |
|------|-------------|
| `create_derived_feature` | 수식 기반 파생 변수 (`df.eval`) |
| `create_polynomial_features` | 다항·교호작용 피처 |
| `extract_datetime_features` | 날짜/시간 피처 (year, month, dayofweek 등) |
</details>

<details open>
<summary><b>Auto Visualization</b> (2) — 자동 추천·렌더링</summary>

| Tool | Description |
|------|-------------|
| `recommend_visualizations` | 데이터 자동 분석 → 근거 있는 차트 추천 + 실행 가능한 tool_call |
| `plot_auto` | 컬럼 1~3개(또는 생략)로 차트 자동 선택·렌더링 (`interactive` 지원) |

수치→히스토그램 · 범주→막대 · 수치×수치→산점도 · 수치×범주(≤8레벨)→박스플롯 ·
수치×범주(9~16레벨)→소형 다중 · 날짜×수치→라인 · 범주×범주→교차표 · +범주→hue/그룹.
추천 목록에는 시간×구성→영역 차트, 결측 5% 이상→결측 진단이 자동 포함됩니다.
</details>

<details>
<summary><b>Chart Style</b> (2) — 디자인 테마</summary>

| Tool | Description |
|------|-------------|
| `list_chart_styles` | 사용 가능한 테마 목록과 현재 테마 |
| `set_chart_style` | 이후 모든 차트의 디자인 전환 (modern/dark/minimal/vibrant/classic) |
</details>

<details>
<summary><b>Visualization</b> (15) — 정적 PNG + 인터랙티브 HTML</summary>

| Tool | Description |
|------|-------------|
| `plot_histogram` / `plot_boxplot` / `plot_scatter` | 커스터마이징 가능한 기본 차트 |
| `plot_before_after` | 전처리 전/후를 같은 축으로 나란히 비교 (histogram/boxplot) |
| `plot_line` | 시계열 라인 (그룹·리샘플링, `interactive`) |
| `plot_rolling` | 원시 시계열(뮤트) + 이동평균(프라이머리) — 노이즈 속 트렌드 |
| `plot_bar` | 범주 빈도/집계 막대 (top_n, `interactive`) |
| `plot_correlation_heatmap` | 상관관계 히트맵 (다이버징 램프) |
| `plot_pivot_heatmap` | 범주×범주×수치 집계 히트맵 — "몇 건"이 아니라 "얼마나" |
| `plot_hexbin` | 밀도 헥스빈 — 수만 행에서 산점도가 뭉개질 때의 대체재 |
| `analyze_target_distribution` | 타깃 분포 + 불균형 탐지 |
| `plot_interactive_scatter/histogram/boxplot/heatmap` | Plotly HTML (줌·호버) |
</details>

<details>
<summary><b>Composition & Comparison</b> (6) — 구성·비교</summary>

| Tool | Description |
|------|-------------|
| `plot_stacked_bar` | 스택 막대 (100% 정규화 지원, 9레벨 이상 'Other' 접기, 세그먼트 간 간격) |
| `plot_area` | 스택 영역 — 시간에 따른 총량과 구성 변화 (리샘플링 지원) |
| `plot_slope` | 슬로프 차트 — 두 시점 간 항목별 변화, 양끝 직접 라벨 |
| `plot_small_multiples` | 소형 다중 — 카테고리별 미니 차트를 공유 축으로 배열 (색 순환 대신 분할) |
| `plot_pareto` | 파레토 — 상위 몇 개가 80%를 만드는지, 단일 %축 (이중축 없음) |
| `plot_waterfall` | 워터폴 — 총량 변화의 항목별 기여 분해 (+/− 색 구분, 직접 라벨) |
</details>

<details>
<summary><b>Distribution & Data Quality</b> (5) — 분포·품질 진단</summary>

| Tool | Description |
|------|-------------|
| `plot_ecdf` | 경험적 누적분포 — 히스토그램이 감추는 정확한 백분위를 그대로 읽음 |
| `plot_violin` | 바이올린 — 박스플롯이 감추는 쌍봉 분포 노출 (사분위 내장) |
| `plot_missingness` | 결측 진단 2패널 — 컬럼별 결측률 + 행 순서 결측 매트릭스(구조적 공백 탐지) |
| `plot_qq` | Q-Q 플롯 — `test_normality` 검정의 시각 짝꿍 (왜도·두꺼운 꼬리 진단) |
| `stat_tile` | 히어로 숫자 타일 — 답이 숫자 하나일 때 차트 대신 쓰는 카드 |
</details>

<details>
<summary><b>Machine Learning</b> (8) — 모델링·진단</summary>

| Tool | Description |
|------|-------------|
| `compare_models` | RandomForest / XGBoost / LogisticRegression / Linear 성능 비교 |
| `evaluate_model` | Confusion Matrix, Feature Importance, 상세 메트릭 |
| `tune_hyperparameters` | GridSearchCV / RandomizedSearchCV |
| `plot_roc_pr` | ROC + PR 커브 나란히 (불균형 데이터에서 ROC 단독의 착시 방지, 다중클래스 OvR) |
| `plot_calibration` | 캘리브레이션 커브 — 확률이 정직한지 (임계값 기반 의사결정의 전제) |
| `plot_feature_importance` | 중요도/|계수| 수평 막대 — 단일 색, 직접 라벨 |
| `plot_residuals` | 잔차 vs 예측 + 잔차 분포 — R²가 못 보는 구조적 결함 탐지 |
</details>

<details>
<summary><b>Statistical Analysis</b> (6) — 가설검정</summary>

| Tool | Description |
|------|-------------|
| `calculate_correlation` | Pearson / Spearman / Kendall |
| `test_normality` | Shapiro-Wilk 정규성 검정 |
| `test_ttest` / `test_anova` | 그룹 간 평균 비교 |
| `test_chi_square` | 범주형 독립성 검정 |
| `calculate_confidence_interval` | 평균 신뢰구간 |
</details>

<details>
<summary><b>Data & Results Management</b> (4) — 캐시·결과물</summary>

| Tool | Description |
|------|-------------|
| `list_cached_datasets` / `clear_cache` | 인메모리 데이터셋 캐시 관리 |
| `view_chart` | 차트를 대화창에 인라인 표시 (MCP 이미지 콘텐츠) |
| `list_outputs` | 생성된 결과물 목록 (최신순) |
</details>

## Architecture

```mermaid
graph LR
    classDef blue fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef purple fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef orange fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef green fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef gray fill:#fafafa,stroke:#333,stroke-width:2px

    User((사용자))
    subgraph Client [Client Layer]
        Agent[Claude 또는<br/>LangGraph Agent]
    end
    LLM[LLM Engine<br/>Claude / OpenAI]
    subgraph MCPLayer [MCP Server]
        Server[FastMCP<br/>60 Tools]
        Theme[Chart<br/>Themes]
        Cache[Dataset<br/>Cache]
    end
    Files[(CSV · PNG · HTML)]
    Viewer[결과 갤러리<br/>:8400]

    User <-->|자연어| Agent
    Agent <-->|프롬프트/응답| LLM
    Agent <-->|MCP tools/call| Server
    Server <--> Cache
    Server <--> Theme
    Server <-->|read/write| Files
    Files -->|실시간 갱신| Viewer
    Viewer --> User

    class User gray
    class Agent blue
    class LLM orange
    class Server,Cache,Theme purple
    class Files,Viewer green
```

역할 분담: LLM은 *어떤 툴을 어떤 인자로 부를지*만 결정하고, 실제 연산(pandas/sklearn/matplotlib)은
전부 서버가 수행합니다. 잘못된 입력은 `isError`와 명확한 메시지로 반환되어 LLM이 스스로 수정합니다.

## Project Structure

<details>
<summary>펼쳐 보기</summary>

```
Data-Analyze-MCP/
├── src/data_analysis/          # MCP 서버 패키지 (python -m data_analysis)
│   ├── server.py               #   공유 FastMCP 인스턴스 + 테마 초기화
│   ├── theming.py              #   차트 테마 시스템 (5종 프리셋 + 시퀀셜/다이버징 램프)
│   ├── palette_check.py        #   팔레트 접근성 검증기 (OKLCH·CVD·WCAG, 의존성 없음)
│   ├── viewer.py               #   결과 갤러리 웹 UI (:8400)
│   ├── config.py               #   환경변수 기반 설정
│   ├── cache.py / helpers.py   #   데이터셋 캐시 · 공통 헬퍼 · 마크 스펙
│   ├── fonts.py / prompts.py   #   한글 폰트 · 시스템 프롬프트
│   └── tools/                  #   도메인별 60개 도구
│       ├── exploration.py         ├── preprocessing.py
│       ├── feature_engineering.py ├── visualization.py
│       ├── composition.py         ├── distribution.py
│       ├── auto_viz.py            ├── style.py
│       ├── results.py             ├── ml.py
│       └── statistics.py
├── data_client.py              # LangGraph 대화형 클라이언트 (OpenAI)
├── examples/demo_session.py    # LLM-MCP 세션 재현 스크립트
├── docs/LLM_INTEGRATION.md     # 실측 인풋/아웃풋 가이드
├── scripts/generate_demo_images.py  # README 데모 이미지 재생성 (무편집 툴 출력)
├── generate_all_test_data.py   # 데모 데이터 3종 생성기
└── pyproject.toml              # src-layout 패키지 (pip install -e .)
```
</details>

## Configuration

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `MCP_CHART_THEME` | `modern` | 시작 시 차트 테마 (modern/dark/minimal/vibrant/classic) |
| `MCP_OUTPUT_DIR` | `outputs/` | 차트·내보내기 저장 위치 |
| `MODEL_NAME` | `gpt-4o-mini` | 동봉 클라이언트의 모델 ID |
| `AUTO_OPEN_RESULTS` | `1` | CLI 결과 자동 열기 (0=끔) |
| `MCP_CLASSIFICATION_MAX_UNIQUE` | `10` | 분류/회귀 판별 임계값 |

## Documentation

- [LLM 연동 가이드](docs/LLM_INTEGRATION.md) — Claude/OpenAI 연결법 + 실측 4턴 세션의 MCP JSON 전문
- [세션 재현](examples/demo_session.py) — API 키 없이 문서의 인풋/아웃풋 그대로 재실행

---

<div align="center">
<sub>Python 3.11+ · FastMCP · pandas / scikit-learn / matplotlib / seaborn / plotly · 데모 데이터셋 3종 동봉</sub>
</div>
