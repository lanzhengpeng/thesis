"""
主图（Main Graph）。

结构：START -> react_0 -> END
- react_0 是基础的 ReAct 子图，负责处理用户消息、思考并调用工具。
  模型输出直接作为最终回答返回给前端。
"""

from langgraph.graph import END, START, StateGraph

from paas_core.agent.langgraph.react_graph import build_basic_react_agent
from paas_core.agent.langgraph.react_info import (
    REACT_SYSTEM_PROMPT,
    REACT_TOOLS,
    REFLECT_SYSTEM_PROMPT,
)
from paas_core.agent.langgraph.state import AgentState


def build_main_graph():
    react_agent = build_basic_react_agent(
        REACT_SYSTEM_PROMPT, REACT_TOOLS, reflect_prompt=REFLECT_SYSTEM_PROMPT
    )

    builder = StateGraph(AgentState)
    builder.add_node("react_0", react_agent)
    builder.add_edge(START, "react_0")
    builder.add_edge("react_0", END)

    return builder.compile()


graph = build_main_graph()
