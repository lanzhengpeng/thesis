import json
from typing import Annotated, List, Literal, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    convert_to_messages,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from paas_core.agent.core.config import settings


# =============================================================================
# 辅助函数：规范化消息
# =============================================================================
# LangServe 通过 HTTP 传入的消息可能被反序列化为裸 BaseMessage
# （type='human' 但 class 是 BaseMessage），OpenAI 转换器无法识别。
# 这里先根据 type 字段转成具体子类，再用 convert_to_messages 统一处理字典消息。
def _normalize_message(msg):
    if isinstance(msg, BaseMessage) and type(msg) is BaseMessage:
        msg_type = getattr(msg, "type", "").lower()
        content = getattr(msg, "content", "")
        additional_kwargs = getattr(msg, "additional_kwargs", {})
        response_metadata = getattr(msg, "response_metadata", {})
        msg_id = getattr(msg, "id", None)

        kwargs = {
            "content": content,
            "additional_kwargs": additional_kwargs,
            "response_metadata": response_metadata,
            "id": msg_id,
        }
        if msg_type == "human":
            return HumanMessage(**kwargs)
        if msg_type == "ai":
            return AIMessage(**kwargs)
        if msg_type == "tool":
            return ToolMessage(**kwargs, tool_call_id="")
        if msg_type == "system":
            return SystemMessage(**kwargs)
    return msg


def _normalize_messages(messages):
    normalized = [_normalize_message(m) for m in messages]
    return convert_to_messages(normalized)


# =============================================================================
# 1. 状态定义
# =============================================================================
# ReAct 子图只需要维护消息历史。使用 add_messages 可以让 LangGraph 自动合并
# 各节点返回的消息列表，避免手动拼接状态。
class ReActState(TypedDict):
    messages: Annotated[list, add_messages]


# =============================================================================
# 2. 子图构建函数
# =============================================================================
# 这是一个可复用的基础 ReAct 组件：输入 system_prompt 和 tools，返回一个编译好的
# StateGraph。调用方只需传入初始消息即可执行“思考 → 调用工具 → 再思考”的循环。
def build_basic_react_agent(
    system_prompt: str,
    tools: List,
    reflect_prompt: str | None = None,
):
    # 初始化 LLM 并绑定工具；使用项目统一配置中的模型与 API 端点
    # parallel_tool_calls=False 强制模型每次只生成一个工具调用，
    # 确保 ReAct 子图按“思考 → 单个工具 → 再思考”顺序执行，避免并行工具。
    model = ChatOpenAI(
        model=settings.AGENT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )
    model_with_tools = model.bind_tools(tools, parallel_tool_calls=False)

    # 用于反思节点的模型实例，不绑定工具，确保只输出思考内容
    reflect_model = ChatOpenAI(
        model=settings.AGENT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )

    # 建立工具名到工具对象的映射，方便在工具执行节点中快速查找并调用
    tool_map = {t.name: t for t in tools}

    # -------------------------------------------------------------------------
    # 节点 A：模型调用（思考节点）
    # -------------------------------------------------------------------------
    # 每次调用前都将系统提示词注入到消息列表最前面，确保模型始终遵循角色设定。
    def call_model(state: ReActState):
        messages = _normalize_messages(state["messages"])
        response = model_with_tools.invoke(
            [SystemMessage(content=system_prompt)] + messages
        )
        return {"messages": [response]}

    # -------------------------------------------------------------------------
    # 节点 B：工具执行节点
    # -------------------------------------------------------------------------
    # 取出模型最后一条消息中的 tool_calls，逐个调用对应工具，并将结果包装成
    # ToolMessage 返回。ToolMessage 必须携带 tool_call_id，否则 LangGraph 会报错。
    def call_tools(state: ReActState):
        messages = _normalize_messages(state["messages"])
        last_message = messages[-1]
        tool_calls = last_message.tool_calls

        tool_messages = []
        for tc in tool_calls:
            result = tool_map[tc["name"]].invoke(tc["args"])
            tool_messages.append(
                ToolMessage(content=json.dumps(result), tool_call_id=tc["id"])
            )
        return {"messages": tool_messages}

    # -------------------------------------------------------------------------
    # 节点 C：观察后反思节点
    # -------------------------------------------------------------------------
    # 工具执行结束后，先用一个不绑定工具的模型进行显式反思，确保模型在观察到
    # 结果后先思考，再决定下一步动作。reflect_prompt 为空时不启用该节点。
    def reflect(state: ReActState):
        if not reflect_prompt:
            return {"messages": []}
        messages = _normalize_messages(state["messages"])
        response = reflect_model.invoke(
            [SystemMessage(content=reflect_prompt)] + messages
        )
        return {"messages": [response]}

    # -------------------------------------------------------------------------
    # 3. 组装状态图
    # -------------------------------------------------------------------------
    builder = StateGraph(ReActState)
    builder.add_node("call_model", call_model)
    builder.add_node("call_tools", call_tools)
    if reflect_prompt:
        builder.add_node("reflect", reflect)

    # 从 START 进入模型节点
    builder.add_edge(START, "call_model")

    # 条件路由：如果模型产生了 tool_calls，就进入工具节点；否则结束子图。
    # 这是 ReAct 循环的核心分支逻辑。
    def should_continue(state: ReActState) -> Literal["call_tools", "__end__"]:
        messages = _normalize_messages(state["messages"])
        last_msg = messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "call_tools"
        return END

    builder.add_conditional_edges("call_model", should_continue)

    # 工具执行完后，先进入反思节点进行显式思考，再回到模型节点进行下一轮决策。
    if reflect_prompt:
        builder.add_edge("call_tools", "reflect")
        builder.add_edge("reflect", "call_model")
    else:
        builder.add_edge("call_tools", "call_model")

    # 返回编译后的图，调用方可以像普通 Runnable 一样 invoke / astream 使用
    return builder.compile()
