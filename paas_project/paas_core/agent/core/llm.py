from langchain_openai import ChatOpenAI

from .config import settings


def create_llm(temperature: float = 0.7) -> ChatOpenAI | None:
    try:
        return ChatOpenAI(
            model=settings.AGENT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=temperature,
        )
    except Exception as exc:
        print(f"[Agent] LLM 初始化失败: {exc}")
        return None
