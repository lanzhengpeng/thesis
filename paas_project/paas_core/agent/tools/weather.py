from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的当前天气（演示用，返回模拟数据）。

    示例："北京"、"Shanghai"
    """
    return f"{city} 当前天气：晴，气温 25°C，湿度 45%，微风。"
