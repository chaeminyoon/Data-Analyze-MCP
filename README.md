# MCP Advanced Data Analysis System

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)
![Ollama](https://img.shields.io/badge/Ollama-Qwen3--70B-ff7a18?style=flat&logo=ollama&logoColor=white)

**26개의 전문가급 데이터 분석 도구**를 제공하는 MCP(Model Context Protocol) 기반 데이터 분석 시스템. OpenAI 및 Ollama 모델을 지원하며, 대화형 인터페이스를 통해 즉각적인 데이터 분석을 수행합니다.

---

## System Architecture

본 시스템은 **MCP 프로토콜**을 기반으로 LLM 에이전트가 26개의 데이터 분석 도구를 자동으로 호출하여 탐색, 전처리, 시각화, 모델링, 통계 분석을 수행합니다.

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
        Server[FastMCP Server<br/>26 Tools]
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
| **MCP Server** | FastMCP | 26개 데이터 분석 도구 제공 |
| **Agent Framework** | LangGraph + LangChain | 대화 상태 관리 및 도구 실행 |
| **Data Processing** | pandas, numpy, scikit-learn | 데이터 조작 및 ML 모델링 |
| **Visualization** | matplotlib, seaborn | 정적 시각화 (향후 Plotly 지원) |
| **Caching** | In-memory Dictionary | 스마트 캐싱으로 50% 성능 향상 |

---

## MCP Server Tools (26 Total)

본 시스템은 **6개 모듈**로 구성된 26개의 전문가급 도구를 제공합니다.

### 📂 Module 1: Data Exploration & Profiling (4 tools)

| Tool | Description |
|------|-------------|
| `get_dataset_info` | 데이터셋 기본 정보 (shape, dtypes, 결측치) |
| `profile_dataset` | 종합 프로파일링 (통계량, 상관관계, 분포) |
| `detect_data_types` | 컬럼별 데이터 타입 자동 분류 |
| `find_duplicates` | 중복 행 탐지 및 카운트 |

### 🧹 Module 2: Data Preprocessing (5 tools)

| Tool | Description |
|------|-------------|
| `handle_missing_values` | 결측치 처리 (mean, median, mode, drop, ffill) |
| `detect_outliers` | 이상치 탐지 (IQR, Z-score 방법) |
| `remove_outliers` | 이상치 제거 또는 처리 |
| `encode_categorical` | 범주형 변수 인코딩 (Label, One-hot) |
| `scale_features` | 특성 스케일링 (StandardScaler, MinMaxScaler) |

### 📊 Module 3: Exploratory Data Analysis (7 tools)

| Tool | Description |
|------|-------------|
| `plot_histogram` | 히스토그램 (bins, KDE, 색상, 레전드 커스터마이징) |
| `plot_boxplot` | 박스플롯 (이상치 시각화) |
| `plot_scatter` | 산점도 (레전드, 마커 크기, 투명도, 색상 팔레트) |
| `plot_correlation_heatmap` | 상관관계 히트맵 |
| `calculate_correlation` | 상관계수 계산 (Pearson, Spearman, Kendall) |
| `analyze_target_distribution` | 타겟 변수 분포 분석 및 불균형 탐지 |

### 🤖 Module 4: Machine Learning (2 tools)

| Tool | Description |
|------|-------------|
| `compare_models` | RandomForest, XGBoost, LogisticRegression, SVM 성능 비교 |
| `evaluate_model` | Confusion Matrix, Feature Importance, 상세 메트릭 평가 |

### 📐 Module 5: Statistical Analysis (5 tools)

| Tool | Description |
|------|-------------|
| `test_normality` | Shapiro-Wilk 정규성 검정 |
| `test_ttest` | 독립 T-검정 (두 그룹 평균 비교) |
| `test_anova`  | 일원 분산분석 (다중 그룹 비교) |
| `test_chi_square` | 카이제곱 독립성 검정 (범주형 변수) |
| `calculate_confidence_interval` | 신뢰구간 계산 (평균값 추정) |

### 💾 Module 6: Data Management (3 tools)

| Tool | Description |
|------|-------------|
| `list_cached_datasets` | 현재 캐시된 데이터셋 목록 조회 |
| `clear_cache` | 메모리 캐시 전체 초기화 |
| **Smart Caching** | 자동 DataFrame 캐싱 (~50% 성능 향상) |

---

## Project Structure

```
d:\MCP_SVR
├── data_server_v.3.0.py        # [Core] MCP 서버 (26개 도구)
├── data_client.py              # [UI] LangGraph 기반 대화형 클라이언트
├── generate_all_test_data.py  # [Scripts] 테스트 데이터 생성기
├── test_data/                  # [Input] 테스트 데이터셋
│   ├── customer_churn.csv      # 분류: 고객 이탈 예측 (7,043행)
│   ├── house_price.csv         # 회귀: 주택 가격 예측 (545행)
│   └── sales_timeseries.csv    # 시계열: 매출 분석 (1,000일)
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
pip install pandas numpy matplotlib seaborn scikit-learn scipy xgboost
pip install mcp langchain-mcp-adapters langgraph langchain-openai langchain-ollama
```

### 3. Configuration

**OpenAI 사용:**
```python
# data_client.py
OLLAMA_HOST = None  # OpenAI 사용
MODEL_NAME = "gpt-4o-mini"
```

**Ollama 사용 (무료):**
```python
# data_client.py
OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2.5:72b"
```

---

## Usage

### Step 1: 서버 시작

```bash
python data_server_v.3.0.py
```

### Step 2: 클라이언트 실행 (별도 터미널)

```bash
python data_client.py
```

접속 성공 시:
```
============================================================
 MCP 데이터 분석 시스템 (v.3.0) - Model: qwen2.5:72b
============================================================
Tip: 이전 대화를 기억합니다. 자연스럽게 대화하세요!
 예: '이제 이상치를 제거해줘', '그 결과를 시각화해줘'
 Commands: 'clear' - 대화 초기화, 'exit/종료' - 종료
============================================================

You:
```

### Step 3: 테스트 데이터 생성 (선택)

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
| **도구 개수** | 26개 |
| **캐싱 효과** | ~50% 속도 향상 (반복 작업 시) |
| **응답 시간** | 2-5초 (Ollama GPU 사용 시) |
| **메모리** | 최소 8GB RAM |
| **비용** | $0 (Ollama) / $0.15/1M tokens (gpt-4o-mini) |

---

## License

MIT License
