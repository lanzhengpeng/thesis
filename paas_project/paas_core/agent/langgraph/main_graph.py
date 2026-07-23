"""
主图（Main Graph）。

目前结构：START -> react_0 -> react_1 --(completed)--> END
                              |
                              +--(incomplete)--> react_0
- react_0 是基础的 ReAct 子图，负责处理用户消息、思考并调用工具。
- react_1 是判别智能体，判断 react_0 的结果是否已完成用户任务。
  若 task_status 为 completed，则结束；若为 incomplete，则返回 react_0 继续处理。
后续如果增加需求分析、架构设计、代码生成等阶段，可以在这里扩展分支。
"""

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from paas_core.agent.langgraph.react_graph import build_basic_react_agent
from paas_core.agent.langgraph.react_info import (
    REACT_1_SYSTEM_PROMPT,
    REACT_1_TOOLS,
    REACT_SYSTEM_PROMPT,
    REACT_TOOLS,
    REFLECT_SYSTEM_PROMPT,
)
from paas_core.agent.langgraph.state import AgentState


def _last_ai_message(messages):
    """从消息列表中找到最后一条 AI 消息。"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _parse_task_status(content: str) -> Literal["completed", "incomplete"]:
    """从判别智能体的输出中解析任务状态。"""
    if "任务状态：已完成" in content or "任务状态: 已完成" in content:
        return "completed"
    return "incomplete"


def build_main_graph():
    # 编译好的 ReAct 子图，直接作为子图节点挂载到主图。
    react_agent = build_basic_react_agent(
        REACT_SYSTEM_PROMPT, REACT_TOOLS, reflect_prompt=REFLECT_SYSTEM_PROMPT
    )
    react_1_agent = build_basic_react_agent(
        REACT_1_SYSTEM_PROMPT, REACT_1_TOOLS, reflect_prompt=REFLECT_SYSTEM_PROMPT
    )

    def parse_task_status(state: AgentState) -> AgentState:
        """从判别智能体的输出中解析任务完成状态。"""
        last_ai = _last_ai_message(state.get("messages", []))
        task_status = "incomplete"
        if last_ai is not None:
            task_status = _parse_task_status(last_ai.content or "")
        return {"task_status": task_status}

    # 条件路由：根据 task_status 决定是结束还是回到 react_0
    def route_after_react_1(state: AgentState) -> Literal["react_0", "__end__"]:
        if state.get("task_status") == "completed":
            return END
        return "react_0"

    builder = StateGraph(AgentState)
    builder.add_node("react_0", react_agent)
    builder.add_node("react_1", react_1_agent)
    builder.add_node("parse_task_status", parse_task_status)

    # 主图流程：开始 -> ReAct -> 判别 -> 解析状态 -> 结束/返回
    builder.add_edge(START, "react_0")
    builder.add_edge("react_0", "react_1")
    builder.add_edge("react_1", "parse_task_status")
    builder.add_conditional_edges("parse_task_status", route_after_react_1)

    return builder.compile()


graph = build_main_graph()
