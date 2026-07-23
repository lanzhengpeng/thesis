from langchain_core.tools import tool


@tool
def query_database(sql: str) -> str:
    """执行数据库查询并返回结果。"""
    return f"查询 '{sql}' 的结果占位符。"
