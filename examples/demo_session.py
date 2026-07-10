"""Replay the analysis -> preprocessing -> visualization session from
docs/LLM_INTEGRATION.md.

This script plays the LLM's role with scripted tool decisions, so you can see
the exact MCP inputs/outputs without needing an API key. Run from the
repository root (after `python generate_all_test_data.py`):

    python examples/demo_session.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = "house_price.csv"

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
# would make for each turn: 분석 -> 처리 -> 전후 비교 -> 시각화.
TURNS = [
    (
        "house_price.csv 분석해줘",
        [
            ("get_dataset_info", {"csv_path": CSV}),
            ("detect_outliers", {"csv_path": CSV, "column": "price"}),
        ],
    ),
    (
        "price 이상치를 제거해줘",
        [("remove_outliers", {"csv_path": CSV, "column": "price"})],
    ),
    (
        "처리 전후를 한 장으로 비교해서 보여줘",
        [
            ("plot_before_after", {"csv_path": CSV, "column": "price"}),
            ("view_chart", {"file_path": "before_after_price.png"}),
        ],
    ),
    (
        "이제 어떤 시각화가 좋을지 추천하고 제일 좋은 걸로 그려줘",
        [
            ("recommend_visualizations", {"csv_path": CSV}),
            ("plot_auto", {"csv_path": CSV}),
        ],
    ),
]


def _describe(result) -> str:
    """Render a tool result for the terminal (image content -> summary line)."""
    if not result.content:
        return "(empty)"
    block = result.content[0]
    if getattr(block, "type", "") == "image":
        return f"[image content: {block.mimeType}, {len(block.data)} base64 chars — 클라이언트가 인라인 렌더링]"
    text = block.text
    return text if len(text) <= 900 else text[:900] + f"\n... ({len(text) - 900} chars truncated)"


async def main() -> None:
    if not os.path.exists(os.path.join(REPO, CSV)):
        sys.exit("house_price.csv not found — run `python generate_all_test_data.py` first.")

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
                    print(f"← result (isError={result.isError})")
                    print(_describe(result))
                print()


if __name__ == "__main__":
    asyncio.run(main())
