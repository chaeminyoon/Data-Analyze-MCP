# LLM ↔ MCP 연동 가이드 (실측 세션 포함)

이 문서는 **LLM(API 또는 로컬)에 이 MCP 서버를 연결하면 실제로 어떤 인풋/아웃풋이 오가는지**를
보여줍니다. 아래 세션 로그는 시뮬레이션이 아니라, MCP stdio 프로토콜로 서버를 띄우고
LLM 역할의 클라이언트가 실제 툴을 호출해 **캡처한 원본 데이터**입니다.

```
사용자 ──자연어──▶ LLM ──tools/call(JSON)──▶ MCP 서버 ──pandas/sklearn/matplotlib──▶ 결과
      ◀──한국어 답변── LLM ◀──result(JSON)────
```

LLM은 코드를 직접 실행하지 않습니다. **어떤 툴을 어떤 인자로 부를지만 결정**하고,
실제 연산(프로파일링·검정·모델링·차트 생성)은 전부 서버가 수행합니다.
LLM은 돌아온 JSON을 읽고 한국어로 해석해 줄 뿐입니다.

---

## 1. 연결 방법

### A. Claude Desktop / Claude Code (API 형태)

`claude_desktop_config.json` 또는 `.mcp.json`에 등록:

```json
{
  "mcpServers": {
    "data-analysis": {
      "command": "python",
      "args": ["-m", "data_analysis"],
      "env": {
        "PYTHONPATH": "/path/to/Data-Analyze-MCP/src",
        "MCP_OUTPUT_DIR": "/path/to/outputs"
      }
    }
  }
}
```

등록하면 Claude가 툴 전체를 자동 인식하고, "이 CSV 분석해줘" 같은 요청에서
스스로 툴을 선택해 호출합니다. (`pip install -e .` 했다면 PYTHONPATH 불필요)

### B. OpenAI API (동봉된 LangGraph 클라이언트)

```bash
export MODEL_NAME=gpt-4o-mini OPENAI_API_KEY=sk-...
python data_client.py
```

어느 경우든 LLM 쪽에는 아무 차이가 없습니다 — MCP가 툴 스키마를 표준 형식으로
노출하므로, 툴 호출을 지원하는 LLM/클라이언트라면 무엇이든 동일하게 동작합니다.

---

## 2. 와이어 프로토콜: 실제로 오가는 JSON

연결 직후 클라이언트가 `initialize` → `tools/list`를 보내면 서버가 등록된 툴 전체(현재 40개)의
이름·설명·JSON 스키마를 반환합니다. 이후 툴 호출은 JSON-RPC `tools/call`입니다:

```json
// LLM → 서버
{
  "jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": {
    "name": "test_anova",
    "arguments": {
      "csv_path": "customer_churn.csv",
      "column": "monthly_charges",
      "group_column": "contract_type"
    }
  }
}

// 서버 → LLM
{
  "jsonrpc": "2.0", "id": 3,
  "result": {
    "content": [{ "type": "text", "text": "{ \"test\": \"One-Way ANOVA\", \"p_value\": 0.0, ... }" }],
    "isError": false
  }
}
```

아래 세션 로그부터는 프레이밍을 생략하고 `arguments`(인풋)와 `result`(아웃풋)만 표기합니다.

---

## 3. 실측 세션: 4턴 데이터 분석 대화

> 환경: 서버 `DataAnalysis` · 데이터 `customer_churn.csv` (7,043행)
> 아래 모든 `result`는 서버가 실제 반환한 값입니다.

### 턴 1 — 데이터 파악

**사용자:** `customer_churn.csv 데이터 분석해줘`

**LLM의 판단:** 구체적 지시가 없는 '분석' 요청 → 프로파일링부터 시작 (시스템 프롬프트 규칙)

```json
→ tools/call: get_dataset_info
{ "csv_path": "customer_churn.csv" }
```

```json
← result
{
  "filename": "customer_churn.csv",
  "shape": [7043, 12],
  "columns": ["gender", "senior_citizen", "partner", "dependents", "tenure",
              "phone_service", "internet_service", "contract_type",
              "payment_method", "monthly_charges", "total_charges", "churn"],
  "dtypes": { "tenure": "int64", "monthly_charges": "float64", "churn": "str", "...": "..." },
  "missing_values": { "gender": 0, "tenure": 0, "...": 0 }
}
```

**LLM 답변:** "7,043행 × 12컬럼의 통신사 고객 데이터입니다. 수치형 4개(tenure,
monthly_charges 등), 범주형 8개이며 결측치는 없습니다. 타깃으로 보이는 `churn`
컬럼이 있어 이탈 분석에 적합합니다."

### 턴 2 — 시각화 추천 + 렌더링 (auto-viz 파이프라인)

**사용자:** `이 데이터에 어떤 시각화가 좋을지 추천하고, 제일 좋은 걸로 그려줘`

**LLM의 판단:** 차트 종류 미지정 → `recommend_visualizations` 먼저, 그 다음 `plot_auto`

```json
→ tools/call: recommend_visualizations
{ "csv_path": "customer_churn.csv", "target_column": "churn" }
```

```json
← result (일부)
{
  "column_roles": { "tenure": "numeric", "contract_type": "categorical",
                    "churn": "categorical", "...": "..." },
  "recommendations": [
    { "chart": "target_distribution", "columns": ["churn"],
      "reason": "Class balance of target 'churn' — checks for imbalance before modeling",
      "tool_call": { "tool": "analyze_target_distribution",
                     "params": { "csv_path": "customer_churn.csv", "target_column": "churn" } } },
    { "chart": "boxplot", "columns": ["tenure", "churn"],
      "reason": "How 'tenure' differs across 'churn' classes",
      "tool_call": { "tool": "plot_boxplot", "params": { "...": "..." } } },
    { "chart": "scatter", "columns": ["tenure", "total_charges", "gender"],
      "reason": "Strongest numeric relationship (|r|=0.77): 'tenure' vs 'total_charges'",
      "tool_call": { "tool": "plot_scatter", "params": { "...": "..." } } }
  ],
  "skipped_columns": [],
  "hint": "Render any recommendation via plot_auto(...) or by calling rec['tool_call'] directly."
}
```

```json
→ tools/call: plot_auto
{ "csv_path": "customer_churn.csv", "target_column": "churn" }
```

```json
← result (일부)
{
  "chart": "target_distribution",
  "columns": ["churn"],
  "reason": "Class balance of target 'churn' — checks for imbalance before modeling",
  "output_path": ".../outputs/target_distribution_churn.png",
  "alternatives": [ { "chart": "boxplot", "columns": ["tenure", "churn"], "...": "..." } ]
}
```

**LLM 답변:** "서버가 8가지 시각화를 추천했고, 1순위인 **타깃 분포 차트**를
생성했습니다 (`target_distribution_churn.png`). 모델링 전 클래스 불균형을
확인하기 위함입니다. 다음 후보로는 이탈 여부별 tenure 박스플롯, tenure-총요금
산점도(상관 0.77)가 있습니다."

### 턴 3 — 통계 검정

**사용자:** `계약 유형별로 월 요금에 유의한 차이가 있는지 검정해줘`

**LLM의 판단:** 수치형 1개 × 3개 그룹 비교 → 일원 ANOVA

```json
→ tools/call: test_anova
{ "csv_path": "customer_churn.csv",
  "column": "monthly_charges", "group_column": "contract_type" }
```

```json
← result
{
  "column": "monthly_charges", "group_column": "contract_type",
  "num_groups": 3, "test": "One-Way ANOVA",
  "statistic": 241.4065, "p_value": 0.0,
  "is_significant": "True", "alpha": 0.05,
  "interpretation": "At least one group mean is significantly different"
}
```

**LLM 답변:** "계약 유형(3그룹)에 따라 월 요금에 **통계적으로 유의한 차이**가
있습니다 (F=241.41, p<0.001). 월 단위 계약 고객이 약정 할인 없이 더 높은
요금을 내는 패턴입니다."

### 턴 4 — 머신러닝 모델 비교

**사용자:** `churn을 예측하는 모델들을 비교해줘`

**LLM의 판단:** 턴 1~3에서 파악한 유의미한 피처들을 선택해 분류 모델 비교

```json
→ tools/call: compare_models
{ "csv_path": "customer_churn.csv", "target_column": "churn",
  "feature_columns": ["tenure", "contract_type", "monthly_charges",
                      "payment_method", "senior_citizen"] }
```

```json
← result
{
  "task_type": "classification",
  "models": {
    "RandomForest":       { "score": 0.6494, "metric": "accuracy" },
    "LogisticRegression": { "score": 0.6671, "metric": "accuracy" },
    "XGBoost":            { "score": 0.6593, "metric": "accuracy" }
  },
  "best_model": "LogisticRegression",
  "best_score": 0.6671
}
```

**LLM 답변:** "3개 모델을 비교한 결과 **LogisticRegression이 정확도 66.7%로
최고**입니다 (XGBoost 65.9%, RandomForest 64.9%). 선형 모델이 가장 좋다는 건
피처-이탈 관계가 비교적 단순하다는 신호입니다. `evaluate_model`로 confusion
matrix와 피처 중요도를 확인해 보시겠어요?"

---

## 4. 핵심 포인트

| 항목 | 설명 |
|---|---|
| **역할 분담** | LLM = 툴 선택·인자 결정·결과 해석 / 서버 = 모든 실제 연산 |
| **파일 결과물** | 차트 툴은 파일 경로(문자열)를 반환 — PNG/HTML은 `MCP_OUTPUT_DIR`에 생성 |
| **에러 처리** | 잘못된 입력은 `isError: true` + 명확한 메시지로 반환 → LLM이 읽고 스스로 수정 (예: "Column 'x' must be numeric" → 다른 컬럼으로 재시도) |
| **대화 맥락** | 전처리 툴(`remove_outliers` 등)은 캐시를 갱신하므로 "이제 이상치 제거하고 다시 그려줘" 같은 연쇄 요청이 자연스럽게 이어짐 |
| **모델 독립성** | Claude, GPT 등 툴 호출을 지원하는 어떤 LLM에 붙여도 동일 — MCP가 툴 스키마를 표준화 |

## 5. 이 세션 재현하기

```bash
pip install -e .
python generate_all_test_data.py          # customer_churn.csv 생성
python examples/demo_session.py           # 위 4턴을 그대로 재실행, JSON 로그 출력
```
