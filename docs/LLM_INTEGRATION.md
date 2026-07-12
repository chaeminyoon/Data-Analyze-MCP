<p align="center">
  <a href="LLM_INTEGRATION.md">English</a> | <a href="LLM_INTEGRATION.ko.md">한국어</a>
</p>

# LLM ↔ MCP Integration Guide (with a captured real session)

This document shows **exactly what inputs and outputs flow when you connect this MCP server
to an LLM (API or local)**. The session log below is not a simulation — it is **raw data
captured** by launching the server over the MCP stdio protocol and having an LLM-role client
call the actual tools.

```
User ──natural language──▶ LLM ──tools/call(JSON)──▶ MCP server ──pandas/sklearn/matplotlib──▶ results
     ◀───────answer─────── LLM ◀──result(JSON)──────
```

The LLM never executes code itself. It **only decides which tool to call with which
arguments**; every actual computation (profiling, tests, modeling, chart generation) runs
on the server. The LLM just reads the returned JSON and interprets it for the user.

---

## 1. How to connect

### A. Claude Desktop / Claude Code (API)

Register in `claude_desktop_config.json` or `.mcp.json`:

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

Once registered, Claude auto-discovers the full tool set and picks tools on its own for
requests like "analyze this CSV". (If you ran `pip install -e .`, PYTHONPATH is unnecessary.)

### B. OpenAI API (bundled LangGraph client)

```bash
export MODEL_NAME=gpt-4o-mini OPENAI_API_KEY=sk-...
python data_client.py
```

Either way, nothing changes on the LLM side — MCP exposes the tool schemas in a standard
format, so any LLM/client that supports tool calling behaves identically.

---

## 2. Wire protocol: the JSON that actually flows

Right after connecting, the client sends `initialize` → `tools/list` and the server returns
the name, description, and JSON schema of every registered tool (currently 60). Tool
invocations after that are JSON-RPC `tools/call`:

```json
// LLM → server
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

// server → LLM
{
  "jsonrpc": "2.0", "id": 3,
  "result": {
    "content": [{ "type": "text", "text": "{ \"test\": \"One-Way ANOVA\", \"p_value\": 0.0, ... }" }],
    "isError": false
  }
}
```

From the session log below, the framing is omitted and only `arguments` (input) and
`result` (output) are shown.

---

## 3. Captured session: analyze → process → visualize (4 turns)

> Environment: server `DataAnalysis` (60 tools) · data `house_price.csv` (545 rows)
> Every `result` below is a value the server actually returned.

### Turn 1 — Analyze: understand the data

**User:** `analyze house_price.csv`

**LLM's reasoning:** an "analyze" request with no specifics → basic info + outlier check
on the key numeric column

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
← result (excerpt)
{
  "outlier_count": 34,
  "outlier_percentage": 6.24,
  "outlier_values": [2653482, 2507725, 1953679, "..."],
  "lower_bound": 212358.5,
  "upper_bound": 1314170.5,
  "method": "iqr"
}
```

**LLM's answer:** "This is house-price data with 545 rows × 12 columns. No missing
values, but 34 outliers (6.2%) are detected in `price` by the IQR rule — expensive
houses far above the 1.31M upper bound. Decide whether to remove them before analysis."

### Turn 2 — Process: remove the outliers

**User:** `remove the price outliers`

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

**LLM's answer:** "Removed 34 rows, leaving 511. The cache is updated, so subsequent
analysis and visualization run on the cleaned data."

### Turn 3 — Before/after in a single image

**User:** `show me a before/after comparison in one image`

**LLM's reasoning:** a comparison request right after preprocessing → `plot_before_after`
(the original from disk vs the processed version from cache, side by side on the same
axes) → `view_chart` to display inline

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
← result (MCP image content)
[image content: image/png, 35732 base64 chars — the client renders it inline in the conversation]
```

**LLM's answer:** "On the left (before removal, 545 rows) the outlier tail above 1.3M is
visible; on the right (after removal, 511 rows) it is gone. The two panels share the same
axes, so the change in distribution compares directly." (chart displayed in the conversation)

### Turn 4 — Visualize: auto recommendations on the cleaned data

**User:** `now recommend the best visualization and draw the top pick`

```json
→ tools/call: recommend_visualizations
{ "csv_path": "house_price.csv" }
```

```json
← result (excerpt)
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
← result (excerpt)
{
  "chart": "scatter",
  "columns": ["area", "price", "bedrooms"],
  "reason": "Strongest numeric relationship (|r|=0.80): 'area' vs 'price'",
  "output_path": ".../outputs/scatter_area_vs_price.png"
}
```

**LLM's answer:** "On the cleaned data, the area-price correlation is the strongest at
|r|=0.80 (it was only 0.33 before removal, because of the outliers). Generated a scatter
plot, colored by bedrooms."

> Turn 2's preprocessing changes Turn 4's visualization — the correlation rising from
> 0.33 → 0.80 purely from outlier removal shows up verbatim in the recommendation `reason`.

---

## 4. Key points

| Item | Description |
|---|---|
| **Division of labor** | LLM = tool selection, arguments, interpretation / server = every actual computation |
| **File outputs** | Chart tools return a file path (string) — PNG/HTML are created under `MCP_OUTPUT_DIR` |
| **Error handling** | Invalid input returns `isError: true` + a clear message → the LLM reads it and corrects itself (e.g. "Column 'x' must be numeric" → retries with another column) |
| **Conversation context** | Preprocessing tools (`remove_outliers`, …) update the cache, so chained requests like "now remove the outliers and draw it again" flow naturally |
| **Model independence** | Attach it to Claude, GPT, or any tool-calling LLM and it behaves the same — MCP standardizes the tool schemas |

## 5. Reproduce this session

```bash
pip install -e .
python generate_all_test_data.py          # generates house_price.csv and friends
python examples/demo_session.py           # re-runs the 4 turns above, printing the JSON log
```
