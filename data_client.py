"""Interactive LangGraph client for the DataAnalysis MCP server.

This is a reference client for testing outside of Claude Desktop/Code.
Configuration via environment variables (or a .env file):

    OPENAI_API_KEY     required
    MODEL_NAME         chat model id (default: gpt-4o-mini)
    AUTO_OPEN_RESULTS  "1" (default) opens newly generated charts in the OS
                       default viewer after each turn; "0" disables
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
AUTO_OPEN_RESULTS = os.getenv("AUTO_OPEN_RESULTS", "1") != "0"
OUTPUT_DIR = Path(os.getenv("MCP_OUTPUT_DIR", "outputs"))

# Launch the server package directly. Put ./src on PYTHONPATH so it runs from a
# fresh checkout without `pip install`; an installed package works too.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
_server_env = {**os.environ, "PYTHONPATH": os.pathsep.join([_SRC, os.environ.get("PYTHONPATH", "")])}
server_params = StdioServerParameters(
    command="python", args=["-m", "data_analysis"], env=_server_env
)


def snapshot_outputs() -> dict:
    """Map of result files -> mtime, used to detect charts created in a turn."""
    if not OUTPUT_DIR.exists():
        return {}
    return {f: f.stat().st_mtime for f in OUTPUT_DIR.iterdir() if f.is_file()}


def open_in_viewer(path: Path) -> None:
    """Open a file with the OS default application (cross-platform)."""
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif os.name == "nt":
        os.startfile(str(path))  # noqa: S606
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_new_outputs(before: dict) -> list[Path]:
    """Open every result file created/updated since ``before``; return them."""
    fresh = [f for f, mtime in snapshot_outputs().items() if before.get(f) != mtime]
    for f in sorted(fresh):
        open_in_viewer(f)
    return fresh


async def run() -> None:
    model = ChatOpenAI(model=MODEL_NAME)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await load_mcp_tools(session)
            agent = create_react_agent(model, tools)

            system_prompt = await load_mcp_prompt(
                session, "default_prompt", arguments={"message": ""}
            )
            conversation_history = [system_prompt[0]] if system_prompt else []

            print("\n" + "=" * 60)
            print(f" MCP 데이터 분석 시스템 - Model: {MODEL_NAME}")
            print("=" * 60)
            print("Tip: 이전 대화를 기억합니다. 자연스럽게 대화하세요!")
            print(" 예: '이제 이상치를 제거해줘', '그 결과를 시각화해줘'")
            print(" Commands: 'clear' - 대화 초기화, 'exit/종료' - 종료")
            print("=" * 60 + "\n")

            while True:
                try:
                    user_input = input("You: ")

                    if user_input.lower() in ("exit", "quit", "q", "종료"):
                        print("\n종료합니다. 감사합니다!")
                        break
                    if user_input.lower() == "clear":
                        conversation_history = conversation_history[:1]  # keep system msg
                        print("\n대화 기록이 초기화되었습니다.\n")
                        continue
                    if not user_input.strip():
                        continue

                    conversation_history.append(HumanMessage(content=user_input))
                    print("\n분석 중...\n")

                    before = snapshot_outputs()
                    response = await agent.ainvoke({"messages": conversation_history})
                    conversation_history = response["messages"]

                    print("=" * 60)
                    print("AI:", response["messages"][-1].content)
                    if AUTO_OPEN_RESULTS:
                        fresh = open_new_outputs(before)
                        if fresh:
                            names = ", ".join(f.name for f in fresh)
                            print(f"\n결과 파일을 열었습니다: {names}")
                    print("=" * 60 + "\n")

                except (EOFError, KeyboardInterrupt):
                    print("\n종료합니다.")
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"\n오류 발생: {exc}\n")
                    if len(conversation_history) > 1:
                        conversation_history.pop()


if __name__ == "__main__":
    asyncio.run(run())
