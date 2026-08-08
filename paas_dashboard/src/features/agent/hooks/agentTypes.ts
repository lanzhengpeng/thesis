/**
 * Agent UI 消息模型（cc-haha UIMessage 风格的平铺结构）。
 *
 * 与 cc-haha/desktop/src/types/chat.ts 中的 UIMessage 对齐：
 * 不再把思考/工具调用折叠成 ReAct Cycle，而是把每条可渲染内容都作为一条独立消息，
 * 方便 MessageList 按类型分发渲染。
 */

export type UIMessage =
  | UserTextMessage
  | AssistantTextMessage
  | ThinkingMessage
  | ToolUseMessage
  | ToolResultMessage
  | ErrorMessage

export interface UserTextMessage {
  id: string
  type: "user_text"
  content: string
  timestamp: number
}

export interface AssistantTextMessage {
  id: string
  type: "assistant_text"
  content: string
  timestamp: number
  /** 当前这条助手消息是否还在流式生成中 */
  status: "loading" | "done" | "error"
}

export interface ThinkingMessage {
  id: string
  type: "thinking"
  content: string
  timestamp: number
}

export interface ToolUseMessage {
  id: string
  type: "tool_use"
  toolName: string
  toolUseId: string
  input: string
  timestamp: number
}

export interface ToolResultMessage {
  id: string
  type: "tool_result"
  toolUseId: string
  content: string
  isError: boolean
  timestamp: number
}

export interface ErrorMessage {
  id: string
  type: "error"
  message: string
  timestamp: number
}
