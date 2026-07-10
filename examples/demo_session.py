"""Replay the 4-turn LLM↔MCP session documented in docs/LLM_INTEGRATION.md.

This script plays the LLM's role with scripted tool decisions, so you can see
the exact MCP inputs/outputs without needing an API key or a local model.
Run from the repository root (after `python generate_all_test_data.py`):

    python examples/demo_session.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = "customer_churn.csv"

env = {
    **os.environ,
    "PYTHONPATH": os.path.join(REPO, "src"),
    "MPLBACKEND": "Agg",
    "MCP_OUTPUT_DIR": os.path.join(REPO, "outputs"),
}
server = StdioServerParameters(
    command=sys.executable, args=["-m", "data_analysis"], env=env, cwd=REPO
)

# (user message, [(tool, arguments), ...]) — the decisions a tool-calling LLM
# would make for each turn.
TURNS = [
    (
        "customer_churn.csv 데이터 분석해줘",
        [("get_dataset_info", {"csv_path": CSV})],
    ),
    (
        "이 데이터에 어떤 시각화가 좋을지 추천하고, 제일 좋은 걸로 그려줘",
        [
            ("recommend_visualizations", {"csv_path": CSV, "target_column": "churn"}),
            ("plot_auto", {"csv_path": CSV, "target_column": "churn"}),
        ],
    ),
    (
        "계약 유형별로 월 요금에 유의한 차이가 있는지 검정해줘",
        [
            (
                "test_anova",
                {"csv_path": CSV, "column": "monthly_charges", "group_column": "contract_type"},
            )
        ],
    ),
    (
        "churn을 예측하는 모델들을 비교해줘",
        [
            (
                "compare_models",
                {
                    "csv_path": CSV,
                    "target_column": "churn",
                    "feature_columns": [
                        "tenure", "contract_type", "monthly_charges",
                        "payment_method", "senior_citizen",
                    ],
                },
            )
        ],
    ),
]


def _shorten(text: str, limit: int = 900) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n... ({len(text) - limit} chars truncated)"


async def main() -> None:
    if not os.path.exists(os.path.join(REPO, CSV)):
        sys.exit("customer_churn.csv not found — run `python generate_all_test_data.py` first.")

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            print(f"connected: {init.serverInfo.name} · {len(tools.tools)} tools\n")

            for i, (user_msg, calls) in enumerate(TURNS, 1):
                print("=" * 72)
                print(f"[턴 {i}] 사용자: {user_msg}")
                for tool, args in calls:
                    print(f"\n→ tools/call: {tool}")
                    print(json.dumps(args, ensure_ascii=False, indent=2))
                    result = await session.call_tool(tool, args)
                    body = result.content[0].text if result.content else ""
                    print(f"← result (isError={result.isError})")
                    print(_shorten(body))
                print()


if __name__ == "__main__":
    asyncio.run(main())
