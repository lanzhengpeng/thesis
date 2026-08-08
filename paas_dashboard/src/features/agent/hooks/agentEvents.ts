/**
 * Agent 流式事件翻译层。
 *
 * 把 @langchain/langgraph-sdk 吐出的原始 LangGraph 事件（on_chain_start、
 * on_chat_model_stream、on_tool_start、on_tool_end …）翻译成 cc-haha 风格的
 * 语义化消息：status / content_start / content_delta / thinking /
 * tool_use_start / tool_use_complete / tool_result / message_complete / error。
 *
 * 主图结构：START -> react_0 -> END
 * react_0 子图：call_model -> call_tools -> reflect -> call_model (loop)
 *   - call_model 输出 → content_delta（最终回答区域）
 *   - reflect 输出 → thinking（可折叠思考块）
 *   - 工具调用 → tool_use / tool_result
 */

export type AgentChatState =
  | "idle"
  | "thinking"
  | "tool_executing"
  | "streaming"

export type AgentServerMessage =
  | AgentStatusMessage
  | AgentContentStartMessage
  | AgentContentDeltaMessage
  | AgentThinkingMessage
  | AgentToolUseStartMessage
  | AgentToolUseCompleteMessage
  | AgentToolResultMessage
  | AgentMessageCompleteMessage
  | AgentErrorMessage

export interface AgentStatusMessage {
  type: "status"
  state: AgentChatState
  verb?: string
}

export interface AgentContentStartMessage {
  type: "content_start"
  blockType: "text" | "tool_use"
  toolName?: string
  toolUseId?: string
}

export interface AgentContentDeltaMessage {
  type: "content_delta"
  text?: string
  toolInput?: string
}

export interface AgentThinkingMessage {
  type: "thinking"
  text: string
}

export interface AgentToolUseStartMessage {
  type: "tool_use_start"
  toolName: string
  toolUseId: string
  input: Record<string, unknown>
}

export interface AgentToolUseCompleteMessage {
  type: "tool_use_complete"
  toolName: string
  toolUseId: string
  input: Record<string, unknown>
}

export interface AgentToolResultMessage {
  type: "tool_result"
  toolUseId: string
  content: string
  isError: boolean
}

export interface AgentMessageCompleteMessage {
  type: "message_complete"
  usage?: {
    input_tokens?: number
    output_tokens?: number
  }
}

export interface AgentErrorMessage {
  type: "error"
  message: string
  code?: string
}

/**
 * 翻译器内部状态机。
 */
export interface AgentEventTranslatorState {
  /** 根图是否还在运行 */
  rootActive: boolean
  /** 当前是否在 reflect 节点内 */
  reflectActive: boolean
  /** 当前正在执行的工具 */
  currentTool: { name: string; id: string; input: unknown } | null
  /** 已处理过的 chain 事件签名，用于去重 */
  processedChainEvents: Set<string>
  /** 工具调用计数器 */
  toolCounter: number
}

export function createTranslatorState(): AgentEventTranslatorState {
  return {
    rootActive: false,
    reflectActive: false,
    currentTool: null,
    processedChainEvents: new Set(),
    toolCounter: 0,
  }
}

function chainEventSignature(chunk: Record<string, unknown>): string {
  const event = String(chunk.event ?? "")
  const name = String(chunk.name ?? "")
  const runId = String(chunk.run_id ?? "")
  const parentIds = Array.isArray(chunk.parent_ids) ? chunk.parent_ids.join(",") : ""
  return `${event}|${name}|${runId}|${parentIds}`
}

function isRootEvent(chunk: Record<string, unknown>): boolean {
  const parentIds = chunk.parent_ids
  return Array.isArray(parentIds) && parentIds.length === 0
}

function getChunkContent(chunk: unknown): string {
  const raw = (chunk as Record<string, unknown>)?.content
  if (typeof raw === "string") return raw
  if (raw === null || raw === undefined) return ""
  if (typeof raw === "object") return JSON.stringify(raw)
  return String(raw)
}

function safeJsonStringify(value: unknown): string {
  if (value === null || value === undefined) return ""
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return value
    }
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

/**
 * 翻译单个 LangGraph 事件为 cc-haha 风格的语义消息列表。
 */
export function translateLangGraphEvent(
  state: AgentEventTranslatorState,
  chunk: unknown
): { messages: AgentServerMessage[]; nextState: AgentEventTranslatorState } {
  const messages: AgentServerMessage[] = []
  const next: AgentEventTranslatorState = { ...state }

  if (!chunk || typeof chunk !== "object") {
    return { messages, nextState: next }
  }

  const raw = chunk as Record<string, unknown>
  const event = String(raw.event ?? "")
  const name = String(raw.name ?? "")
  const data = (raw.data ?? {}) as Record<string, unknown>

  // chain 事件去重
  if (event === "on_chain_start" || event === "on_chain_end") {
    const sig = chainEventSignature(raw)
    if (next.processedChainEvents.has(sig)) {
      return { messages, nextState: next }
    }
    next.processedChainEvents.add(sig)
  }

  if (event === "on_chain_start") {
    if (isRootEvent(raw)) {
      next.rootActive = true
      messages.push({ type: "status", state: "thinking", verb: "思考" })
      return { messages, nextState: next }
    }

    if (name === "react_0") {
      messages.push({ type: "content_start", blockType: "text" })
      return { messages, nextState: next }
    }

    if (name === "call_model") {
      messages.push({ type: "status", state: "streaming" })
      return { messages, nextState: next }
    }

    if (name === "reflect") {
      next.reflectActive = true
      messages.push({ type: "status", state: "thinking", verb: "反思" })
      return { messages, nextState: next }
    }

    if (name === "call_tools") {
      messages.push({ type: "status", state: "tool_executing", verb: "执行工具" })
      return { messages, nextState: next }
    }

    return { messages, nextState: next }
  }

  if (event === "on_chain_end") {
    if (isRootEvent(raw)) {
      next.rootActive = false
      next.reflectActive = false
      messages.push({ type: "message_complete" })
      return { messages, nextState: next }
    }

    if (name === "react_0") {
      return { messages, nextState: next }
    }

    if (name === "call_model") {
      return { messages, nextState: next }
    }

    if (name === "reflect") {
      next.reflectActive = false
      return { messages, nextState: next }
    }

    if (name === "call_tools") {
      messages.push({ type: "status", state: "thinking", verb: "思考" })
      return { messages, nextState: next }
    }

    return { messages, nextState: next }
  }

  if (event === "on_chat_model_stream") {
    const content = getChunkContent(data.chunk)
    if (!content) return { messages, nextState: next }

    if (next.reflectActive) {
      // reflect 节点输出 → 可折叠思考块
      messages.push({ type: "thinking", text: content })
      return { messages, nextState: next }
    }

    // call_model 输出 → 最终回答区域（内容直接展示）
    messages.push({ type: "status", state: "streaming" })
    messages.push({ type: "content_delta", text: content })
    return { messages, nextState: next }
  }

  if (event === "on_tool_start") {
    next.toolCounter += 1
    const toolName = String(data.tool ?? name ?? "工具")
    const toolUseId = `tool_${next.toolCounter}`
    const input = (data.input ?? {}) as Record<string, unknown>
    next.currentTool = { name: toolName, id: toolUseId, input }

    messages.push({
      type: "content_start",
      blockType: "tool_use",
      toolName,
      toolUseId,
    })
    messages.push({
      type: "tool_use_start",
      toolName,
      toolUseId,
      input,
    })
    messages.push({
      type: "tool_use_complete",
      toolName,
      toolUseId,
      input,
    })
    return { messages, nextState: next }
  }

  if (event === "on_tool_end") {
    const tool = next.currentTool
    next.currentTool = null
    const toolUseId = tool?.id ?? `tool_${next.toolCounter}`
    const output = safeJsonStringify(data.output)
    const isError =
      typeof data.output === "string" &&
      (data.output.startsWith("Error:") || data.output.includes("exception"))

    messages.push({
      type: "tool_result",
      toolUseId,
      content: output,
      isError,
    })
    return { messages, nextState: next }
  }

  return { messages, nextState: next }
}

/**
 * 有状态翻译器。适合在 hook 里长期持有。
 */
export class AgentEventTranslator {
  state = createTranslatorState()

  translate(chunk: unknown): AgentServerMessage[] {
    const { messages, nextState } = translateLangGraphEvent(this.state, chunk)
    this.state = nextState
    return messages
  }

  reset(): void {
    this.state = createTranslatorState()
  }
}
