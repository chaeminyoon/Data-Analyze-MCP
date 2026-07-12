<p align="center">
  <a href="LLM_INTEGRATION.md">English</a> | <a href="LLM_INTEGRATION.ko.md">한국어</a>
</p>

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

연결 직후 클라이언트가 `initialize` → `tools/list`를 보내면 서버가 등록된 툴 전체(현재 60개)의
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

## 3. 실측 세션: 분석 → 처리 → 시각화 (4턴)

> 환경: 서버 `DataAnalysis` (60 tools) · 데이터 `house_price.csv` (545행)
> 아래 모든 `result`는 서버가 실제 반환한 값입니다.

### 턴 1 — 분석: 데이터 파악

**사용자:** `house_price.csv 분석해줘`

**LLM의 판단:** 구체적 지시가 없는 '분석' 요청 → 기본 정보 + 핵심 수치 컬럼의 이상치 점검

```json
→ tools/call: get_dataset_info
{ "csv_path": "house_price.csv" }
```

```json
← result
{
  "filename": "house_price.csv",
  "shape": [545, 12],
  "columns": ["area", "bedrooms", "bathrooms", "stories", "parking",
              "mainroad", "guestroom", "basement", "hotwaterheating",
              "airconditioning", "furnishingstatus", "price"],
  "dtypes": { "area": "int64", "price": "int64", "furnishingstatus": "str", "...": "..." },
  "missing_values": { "area": 0, "price": 0, "...": 0 }
}
```

```json
→ tools/call: detect_outliers
{ "csv_path": "house_price.csv", "column": "price" }
```

```json
← result (일부)
{
  "outlier_count": 34,
  "outlier_percentage": 6.24,
  "outlier_values": [2653482, 2507725, 1953679, "..."],
  "lower_bound": 212358.5,
  "upper_bound": 1314170.5,
  "method": "iqr"
}
```

**LLM 답변:** "545행 × 12컬럼의 주택 가격 데이터입니다. 결측치는 없지만
`price`에서 IQR 기준 이상치 34개(6.2%)가 탐지됩니다 — 상한 131만을 크게
넘는 고가 주택들입니다. 분석 전에 제거할지 결정하세요."

### 턴 2 — 처리: 이상치 제거

**사용자:** `price 이상치를 제거해줘`

```json
→ tools/call: remove_outliers
{ "csv_path": "house_price.csv", "column": "price" }
```

```json
← result
{
  "rows_removed": 34,
  "original_shape": [545, 12],
  "new_shape": [511, 12],
  "method": "iqr"
}
```

**LLM 답변:** "34행을 제거해 511행이 되었습니다. 캐시가 갱신되어 이후
분석·시각화는 정제된 데이터 기준으로 수행됩니다."

### 턴 3 — 전/후 비교를 한 장으로

**사용자:** `처리 전후를 한 장으로 비교해서 보여줘`

**LLM의 판단:** 전처리 직후의 비교 요청 → `plot_before_after` (디스크의 원본 vs
캐시의 처리본을 같은 축으로 나란히) → `view_chart`로 인라인 표시

```json
→ tools/call: plot_before_after
{ "csv_path": "house_price.csv", "column": "price" }
```

```json
← result
".../outputs/before_after_price.png"
```

```json
→ tools/call: view_chart
{ "file_path": "before_after_price.png" }
```

```
← result (MCP 이미지 콘텐츠)
[image content: image/png, 35732 base64 chars — 클라이언트가 대화창에 인라인 렌더링]
```

**LLM 답변:** "왼쪽(제거 전, 545행)에는 130만 이상의 이상치 꼬리가 보이지만
오른쪽(제거 후, 511행)에서는 사라졌습니다. 두 패널은 같은 축을 공유하므로
분포 변화를 그대로 비교할 수 있습니다." (차트가 대화창에 표시됨)

### 턴 4 — 시각화: 정제된 데이터로 자동 추천

**사용자:** `이제 어떤 시각화가 좋을지 추천하고 제일 좋은 걸로 그려줘`

```json
→ tools/call: recommend_visualizations
{ "csv_path": "house_price.csv" }
```

```json
← result (일부)
{
  "column_roles": { "area": "numeric", "price": "numeric",
                    "bedrooms": "discrete", "furnishingstatus": "categorical", "...": "..." },
  "recommendations": [
    { "chart": "scatter", "columns": ["area", "price", "bedrooms"],
      "reason": "Strongest numeric relationship (|r|=0.80): 'area' vs 'price'",
      "tool_call": { "tool": "plot_scatter",
                     "params": { "csv_path": "house_price.csv", "x_column": "area",
                                 "y_column": "price", "hue_column": "bedrooms" } } },
    { "chart": "boxplot", "columns": ["area", "bedrooms"], "...": "..." }
  ]
}
```

```json
→ tools/call: plot_auto
{ "csv_path": "house_price.csv" }
```

```json
← result (일부)
{
  "chart": "scatter",
  "columns": ["area", "price", "bedrooms"],
  "reason": "Strongest numeric relationship (|r|=0.80): 'area' vs 'price'",
  "output_path": ".../outputs/scatter_area_vs_price.png"
}
```

**LLM 답변:** "정제된 데이터에서는 area-price 상관이 |r|=0.80으로 가장
강합니다 (제거 전에는 이상치 때문에 0.33에 불과했습니다). 산점도를 생성했고
bedrooms로 색을 구분했습니다."

> 턴 2의 전처리가 턴 4의 시각화를 바꿉니다 — 이상치 제거만으로 상관계수가
> 0.33 → 0.80으로 올라간 것이 추천 이유(reason)에 그대로 반영됩니다.

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
python generate_all_test_data.py          # house_price.csv 등 생성
python examples/demo_session.py           # 위 4턴을 그대로 재실행, JSON 로그 출력
```
