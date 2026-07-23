from langchain_core.tools import tool


@tool
def search(query: str) -> str:
    """搜索外部信息并返回摘要。"""
    return f"搜索 '{query}' 的结果占位符。"
