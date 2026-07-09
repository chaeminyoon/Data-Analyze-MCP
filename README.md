# MCP Advanced Data Analysis System

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)
![Ollama](https://img.shields.io/badge/Ollama-Qwen3--70B-ff7a18?style=flat&logo=ollama&logoColor=white)

**32개의 전문가급 데이터 분석 도구**를 제공하는 MCP(Model Context Protocol) 기반 데이터 분석 시스템. OpenAI 및 Ollama 모델을 지원하며, 대화형 인터페이스를 통해 즉각적인 데이터 분석을 수행합니다.

---

## System Architecture

본 시스템은 **MCP 프로토콜**을 기반으로 LLM 에이전트가 32개의 데이터 분석 도구를 자동으로 호출하여 탐색, 전처리, 시각화, 모델링, 통계 분석을 수행합니다.

```mermaid
graph LR
    %% Styles
    classDef blue fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef purple fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef orange fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef green fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef gray fill:#fafafa,stroke:#333,stroke-width:2px

    User((사용자))
    
    subgraph Client [Client Layer]
        Agent[LangGraph<br/>Agent]
        Hist[대화<br/>기록]
    end
    
    LLM[LLM Engine<br/>OpenAI/Ollama]
    
    subgraph MCPLayer [MCP Server Layer]
        Server[FastMCP Server<br/>32 Tools]
        Cache[Smart<br/>Cache]
    end
    
    Files[(File System<br/>CSV, PNG)]

    User <-->|1. 질문/응답| Agent
    Agent <--> Hist
    Agent <-->|2. 프롬프트| LLM
    LLM -->|3. 도구 호출| Agent
    Agent <-->|4. MCP Protocol| Server
    Server <--> Cache
    Server <-->|5. 데이터 처리| Files
    Server -->|6. 결과| Agent

    class User gray
    class Agent,Hist blue
    class LLM orange
    class Server,Cache purple
    class Files green
```

## Core Components

| Component | Technology | Role |
|-----------|-----------|------|
| **LLM** | OpenAI (gpt-4o-mini) / Ollama (qwen2.5:72b) | 자연어 이해 및 도구 호출 결정 |
| **MCP Server** | FastMCP | 32개 데이터 분석 도구 제공 |
| **Agent Framework** | LangGraph + LangChain | 대화 상태 관리 및 도구 실행 |
| **Data Processing** | pandas, numpy, scikit-learn | 데이터 조작 및 ML 모델링 |
| **Visualization** | matplotlib, seaborn | 정적 시각화 (향후 Plotly 지원) |
| **Caching** | In-memory Dictionary | 스마트 캐싱으로 50% 성능 향상 |

---

## MCP Server Tools (32 Total)

본 시스템은 **7개 모듈**로 구성된 32개의 전문가급 도구를 제공합니다.

### 📂 Module 1: Data Exploration & Profiling (4 tools) — `tools/exploration.py`

| Tool | Description |
|------|-------------|
| `get_dataset_info` | 데이터셋 기본 정보 (shape, dtypes, 결측치) |
| `profile_dataset` | 종합 프로파일링 (통계량, 상관관계, 분포) |
| `detect_data_types` | 컬럼별 데이터 타입 자동 분류 |
| `find_duplicates` | 중복 행 탐지 및 카운트 |

### 🧹 Module 2: Data Preprocessing (5 tools) — `tools/preprocessing.py`

| Tool | Description |
|------|-------------|
| `handle_missing_values` | 결측치 처리 (mean, median, mode, drop, ffill) |
| `detect_outliers` | 이상치 탐지 (IQR, Z-score 방법) |
| `remove_outliers` | 이상치 제거 (탐지된 전체 제거) |
| `encode_categorical` | 범주형 변수 인코딩 (Label, One-hot) |
| `scale_features` | 특성 스케일링 (StandardScaler, MinMaxScaler) |

### 🛠️ Module 3: Feature Engineering (3 tools) — `tools/feature_engineering.py`

| Tool | Description |
|------|-------------|
| `create_derived_feature` | 수식 기반 파생 변수 생성 (`df.eval`) |
| `create_polynomial_features` | 다항·교호작용 피처 생성 |
| `extract_datetime_features` | 날짜/시간 피처 추출 (year, month, dayofweek 등) |

### 📊 Module 4: Visualization (9 tools) — `tools/visualization.py`

| Tool | Description |
|------|-------------|
| `plot_histogram` | 히스토그램 (bins, KDE, 색상, 레전드 커스터마이징) |
| `plot_boxplot` | 박스플롯 (이상치 시각화) |
| `plot_scatter` | 산점도 (레전드, 마커 크기, 투명도, 색상 팔레트) |
| `plot_correlation_heatmap` | 상관관계 히트맵 |
| `analyze_target_distribution` | 타겟 변수 분포 분석 및 불균형 탐지 |
| `plot_interactive_scatter` | 인터랙티브 산점도 (Plotly HTML) |
| `plot_interactive_histogram` | 인터랙티브 히스토그램 (Plotly HTML) |
| `plot_interactive_boxplot` | 인터랙티브 박스플롯 (Plotly HTML) |
| `plot_interactive_heatmap` | 인터랙티브 상관관계 히트맵 (Plotly HTML) |

### 🤖 Module 5: Machine Learning (3 tools) — `tools/ml.py`

| Tool | Description |
|------|-------------|
| `compare_models` | RandomForest, XGBoost, LogisticRegression, SVM 성능 비교 |
| `evaluate_model` | Confusion Matrix, Feature Importance, 상세 메트릭 평가 |
| `tune_hyperparameters` | GridSearchCV / RandomizedSearchCV 하이퍼파라미터 튜닝 |

### 📐 Module 6: Statistical Analysis (6 tools) — `tools/statistics.py`

| Tool | Description |
|------|-------------|
| `calculate_correlation` | 상관계수 계산 (Pearson, Spearman, Kendall) |
| `test_normality` | Shapiro-Wilk 정규성 검정 |
| `test_ttest` | 독립 T-검정 (두 그룹 평균 비교) |
| `test_anova`  | 일원 분산분석 (다중 그룹 비교) |
| `test_chi_square` | 카이제곱 독립성 검정 (범주형 변수) |
| `calculate_confidence_interval` | 신뢰구간 계산 (평균값 추정) |

### 💾 Module 7: Data Management (2 tools) — `tools/exploration.py`

| Tool | Description |
|------|-------------|
| `list_cached_datasets` | 현재 캐시된 데이터셋 목록 조회 |
| `clear_cache` | 메모리 캐시 초기화 (특정 파일 또는 전체) |

---

## Project Structure

```
Data-Analyze-MCP/
├── data_analysis/              # [Core] MCP 서버 패키지
│   ├── __main__.py             #   진입점 (python -m data_analysis)
│   ├── server.py               #   공유 FastMCP 인스턴스
│   ├── config.py               #   환경변수 기반 설정
│   ├── cache.py                #   데이터셋 캐시 / 로더
│   ├── helpers.py              #   공통 검증·플로팅·ML 헬퍼
│   ├── fonts.py                #   한글 폰트 설정
│   ├── prompts.py              #   MCP 기본 프롬프트
│   └── tools/                  #   도메인별 도구 모듈
│       ├── exploration.py      #     탐색·프로파일링
│       ├── preprocessing.py    #     결측치·이상치·인코딩·스케일링
│       ├── feature_engineering.py #  파생·다항·시계열 피처
│       ├── visualization.py    #     정적/인터랙티브 시각화
│       ├── ml.py               #     모델 비교·평가·튜닝
│       └── statistics.py       #     상관·가설검정
├── data_client.py              # [UI] LangGraph 기반 대화형 클라이언트
├── generate_all_test_data.py   # [Scripts] 테스트 데이터 생성기
├── requirements.txt            # 의존성 목록
├── README.md                   # 프로젝트 문서
└── .gitignore                  # Git 제외 설정
```

---

## Getting Started

### 1. Prerequisites

**필수 요구사항:**
- Python 3.11+
- OpenAI API Key 또는 Ollama 실행 중

**Ollama 사용 시 (무료):**
```bash
ollama pull qwen2.5:72b
```

### 2. Installation

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 3. Configuration

설정은 환경변수로 제어합니다 (코드 수정 불필요). `.env` 파일 또는 셸에서 지정:

**OpenAI 사용:**
```bash
export LLM_BACKEND=openai
export MODEL_NAME=gpt-4o-mini
export OPENAI_API_KEY=sk-...
```

**Ollama 사용 (무료, 기본값):**
```bash
export LLM_BACKEND=ollama
export MODEL_NAME=qwen2.5:72b
export OLLAMA_URL=http://localhost:11434
```

**기타 설정 (선택):** `MCP_OUTPUT_DIR`(생성물 저장 위치, 기본 `outputs/`),
`MCP_CLASSIFICATION_MAX_UNIQUE`(분류/회귀 판별 임계값).

---

## Usage

### Step 1: 클라이언트 실행

클라이언트가 서버(`python -m data_analysis`)를 stdio로 자동 기동하므로 별도로
서버를 띄울 필요가 없습니다.

```bash
python data_client.py
```

> 서버만 단독 실행하려면: `python -m data_analysis`

접속 성공 시:
```
============================================================
 MCP 데이터 분석 시스템 - Model: qwen2.5:72b
============================================================
Tip: 이전 대화를 기억합니다. 자연스럽게 대화하세요!
 예: '이제 이상치를 제거해줘', '그 결과를 시각화해줘'
 Commands: 'clear' - 대화 초기화, 'exit/종료' - 종료
============================================================

You:
```

### Step 2: 테스트 데이터 생성 (선택)

```bash
python generate_all_test_data.py
```

생성되는 파일:
- `customer_churn.csv` - 7,043행, 분류 문제
- `house_price.csv` - 545행, 회귀 문제
- `sales_timeseries.csv` - 1,000일, 시계열 분석

---

## Examples

### 데이터 탐색
```
You: customer_churn.csv를 프로파일링해줘

AI: [통계량, 결측치, 상관관계 등 종합 분석 결과 출력]
```

### 시각화 (커스터마이징)
```
You: area와 price의 산점도를 그려줘. bedrooms로 색상 구분하고, 
     레전드 제목은 '방 개수', 마커 크기는 80, 투명도는 0.7로 해줘

AI: [커스터마이징된 scatter_area_vs_price.png 생성]
```

### 통계 분석
```
You: contract_type별로 monthly_charges에 차이가 있는지 ANOVA 검정해줘

AI: ANOVA 결과:
    F-statistic: 245.67
    p-value: 0.0001
    해석: 계약 유형별로 월 요금에 유의한 차이가 있습니다 (p < 0.05).
```

### 머신러닝
```
You: customer_churn.csv에서 churn을 타겟으로 
     RandomForest, XGBoost, LogisticRegression을 비교하고 
     최고 성능 모델을 상세 평가해줘

AI: [모델 비교 결과]
    최고 모델: RandomForest (Accuracy: 0.82)
    
    [evaluate_model 자동 실행]
    Precision: 0.76
    Recall: 0.71
    F1-Score: 0.73
    Feature Importance:
    1. monthly_charges: 0.23
    2. tenure: 0.19
    ...
    [confusion_matrix_RandomForest.png 생성]
```

---

## Advanced Features

### Visualization Customization

**plot_scatter 파라미터:**
```python
plot_scatter(
    csv_path="house_price.csv",
    x_column="area",
    y_column="price",
    hue_column="bedrooms",
    title="주택 면적과 가격 관계",
    xlabel="면적 (sqft)",
    ylabel="가격 ($)",
    figsize_width=12,
    figsize_height=8,
    marker_size=80,
    alpha=0.7,
    color_palette="Set2",
    show_legend=True,
    legend_title="방 개수",
    legend_position="upper left"
)
```

### Conversation History

대화 기록을 유지하여 연속적인 분석 가능:

```
You: customer_churn.csv를 불러와서 결측치를 확인해줘
AI: [결측치 11개 발견]

You: 평균값으로 채워줘
AI: [결측치 처리 완료]

You: 이제 이상치를 탐지해줘
AI: [monthly_charges에서 23개 이상치 발견]
```

`clear` 명령어로 대화 초기화 가능.

---

## Performance

| Metric | Value |
|--------|-------|
| **도구 개수** | 32개 |
| **캐싱 효과** | ~50% 속도 향상 (반복 작업 시) |
| **응답 시간** | 2-5초 (Ollama GPU 사용 시) |
| **메모리** | 최소 8GB RAM |
| **비용** | $0 (Ollama) / $0.15/1M tokens (gpt-4o-mini) |

---

## License

MIT License
