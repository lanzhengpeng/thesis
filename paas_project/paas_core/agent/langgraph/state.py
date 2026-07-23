from typing import Annotated, Literal, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# 主图状态：维护消息历史与任务完成状态，由 ReAct 子图执行后写回。
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # task_status 由 react_1 判别后更新：completed 表示任务完成，incomplete 表示需要回到 react_0 继续处理。
    task_status: Annotated[Literal["completed", "incomplete"], lambda x, y: y]
