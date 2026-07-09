"""Interactive LangGraph client for the DataAnalysis MCP server.

Configuration is read from environment variables so the same script works
against OpenAI or a self-hosted Ollama instance without code edits:

    LLM_BACKEND   "ollama" (default) | "openai"
    MODEL_NAME    model id (default: qwen2.5:72b for ollama)
    OLLAMA_URL    base url for the ollama server
"""
import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.2.209:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:72b")

# Launch the server package directly; no more version-suffixed filenames.
server_params = StdioServerParameters(command="python", args=["-m", "data_analysis"])


def build_model():
    """Instantiate the chat model for the configured backend."""
    if LLM_BACKEND == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=os.getenv("MODEL_NAME", "gpt-4o-mini"))

    from langchain_ollama import ChatOllama

    return ChatOllama(model=MODEL_NAME, base_url=OLLAMA_URL, temperature=0, num_ctx=8192)


async def run() -> None:
    model = build_model()

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
                        print("\n👋 종료합니다. 감사합니다!")
                        break
                    if user_input.lower() == "clear":
                        conversation_history = conversation_history[:1]  # keep system msg
                        print("\n🔄 대화 기록이 초기화되었습니다.\n")
                        continue
                    if not user_input.strip():
                        continue

                    conversation_history.append(HumanMessage(content=user_input))
                    print("\n🤔 분석 중...\n")

                    response = await agent.ainvoke({"messages": conversation_history})
                    conversation_history = response["messages"]

                    print("=" * 60)
                    print("AI:", response["messages"][-1].content)
                    print("=" * 60 + "\n")

                except (EOFError, KeyboardInterrupt):
                    print("\n👋 종료합니다.")
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"\n❌ 오류 발생: {exc}\n")
                    if len(conversation_history) > 1:
                        conversation_history.pop()


if __name__ == "__main__":
    asyncio.run(run())
