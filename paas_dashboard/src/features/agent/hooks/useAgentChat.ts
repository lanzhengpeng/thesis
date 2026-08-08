import { useCallback, useMemo, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { Client } from "@langchain/langgraph-sdk";
import {
  AgentEventTranslator,
  type AgentChatState,
  type AgentServerMessage,
} from "./agentEvents.js";
import type {
  UIMessage,
  AssistantTextMessage,
  ThinkingMessage,
  ToolUseMessage,
} from "./agentTypes.js";

export type {
  UIMessage,
  UserTextMessage,
  AssistantTextMessage,
  ThinkingMessage,
  ToolUseMessage,
  ToolResultMessage,
  ErrorMessage,
} from "./agentTypes.js";

const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL ?? "http://localhost:8123";
const ASSISTANT_ID = "paas-agent";

export interface UseAgentChatResult {
  messages: UIMessage[];
  status: "idle" | "streaming" | "error";
  error: string | null;
  send: (message: string, options?: SendOptions) => Promise<void>;
  stop: () => void;
}

export interface SendOptions {
  /** @deprecated LangGraph Platform 会自动维护 thread 历史，此字段保留仅作 API 兼容 */
  history?: { role: "user" | "assistant"; content: string }[];
  /** 是否自动在内部 messages 追加 user 消息；外部已追加时可设为 false */
  pushUserMessage?: boolean;
}

interface AgentState {
  messages: Array<{ type: string; content: string } & Record<string, unknown>>;
  task_status?: "completed" | "incomplete";
}

let idCounter = 0;
function uid(prefix = "msg") {
  return `${prefix}-${++idCounter}-${Date.now().toString(36)}`;
}

function formatToolOutput(output: unknown): string {
  if (output === null || output === undefined) return "";
  if (typeof output === "string") {
    try {
      const parsed = JSON.parse(output);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return output;
    }
  }
  return JSON.stringify(output, null, 2);
}

function formatToolInput(input: Record<string, unknown>): string {
  return JSON.stringify(input, null, 2);
}

interface ChatState {
  messages: UIMessage[];
  /** 当前流式助手消息的 id */
  currentAssistantId: string | null;
  /** 当前正在接收的 thinking 消息 id */
  activeThinkingId: string | null;
  /** 当前正在执行的工具调用 id */
  activeToolUseId: string | null;
  /** 内容缓冲区，在确定是 thinking 还是最终回答前临时存放 */
  contentBuffer: string;
  /** 当前 UI 状态 */
  chatState: AgentChatState;
  /** 上次 flush 的状态快照，用于去重减少无效渲染 */
  lastSnapshot: string;
}

function createChatState(): ChatState {
  return {
    messages: [],
    currentAssistantId: null,
    activeThinkingId: null,
    activeToolUseId: null,
    contentBuffer: "",
    chatState: "idle",
    lastSnapshot: "",
  };
}

function findMessageById(messages: UIMessage[], id: string): UIMessage | undefined {
  return messages.find((m) => m.id === id);
}

function updateMessageById(
  messages: UIMessage[],
  id: string,
  updater: (msg: UIMessage) => UIMessage
): UIMessage[] {
  return messages.map((m) => (m.id === id ? updater(m) : m));
}

/** 将 contentBuffer 刷新为 thinking 消息（工具调用前的模型推理）。 */
function flushBufferAsThinking(state: ChatState): void {
  const text = state.contentBuffer.trim();
  if (!text) return;
  state.messages.push({
    id: uid("think"),
    type: "thinking",
    content: text,
    timestamp: Date.now(),
  });
  state.contentBuffer = "";
}

/** 将 contentBuffer 刷新为 assistant_text 消息（最终回答）。 */
function flushBufferAsAssistant(state: ChatState): void {
  const text = state.contentBuffer.trim();
  state.contentBuffer = "";
  if (!text) return;
  if (state.currentAssistantId) {
    const assistant = findMessageById(
      state.messages,
      state.currentAssistantId
    ) as AssistantTextMessage | undefined;
    if (assistant) {
      assistant.content = text;
      assistant.status = "done";
    }
  } else {
    state.messages.push({
      id: uid("assistant"),
      type: "assistant_text",
      content: text,
      timestamp: Date.now(),
      status: "done",
    });
  }
}

/** 创建或更新临时流式助手消息，用于展示当前 contentBuffer 的实时预览。 */
function updateStreamingAssistant(state: ChatState): void {
  const text = state.contentBuffer.trim();
  if (state.currentAssistantId) {
    const assistant = findMessageById(
      state.messages,
      state.currentAssistantId
    ) as AssistantTextMessage | undefined;
    if (assistant) {
      assistant.content = text;
    }
  } else if (text) {
    const assistant: AssistantTextMessage = {
      id: uid("assistant"),
      type: "assistant_text",
      content: text,
      timestamp: Date.now(),
      status: "loading",
    };
    state.messages.push(assistant);
    state.currentAssistantId = assistant.id;
  }
}

/**
 * cc-haha 风格的 reducer：用语义化消息驱动 UI 状态。
 *
 * 直接维护 UIMessage[] 平铺数组，不再分组为 ReAct Cycle。
 */
function dispatchMessage(state: ChatState, msg: AgentServerMessage): void {
  switch (msg.type) {
    case "status": {
      state.chatState = msg.state;
      break;
    }

    case "content_start": {
      if (msg.blockType === "text") {
        state.activeThinkingId = null;
      }
      break;
    }

    case "thinking": {
      state.chatState = "streaming";
      if (state.activeThinkingId) {
        const think = findMessageById(
          state.messages,
          state.activeThinkingId
        ) as ThinkingMessage | undefined;
        if (think) {
          think.content += msg.text;
        }
      } else {
        const think: ThinkingMessage = {
          id: uid("think"),
          type: "thinking",
          content: msg.text,
          timestamp: Date.now(),
        };
        state.messages.push(think);
        state.activeThinkingId = think.id;
      }
      break;
    }

    case "content_delta": {
      const text = msg.text ?? "";
      if (!text) break;
      state.chatState = "streaming";

      state.contentBuffer += text;
      updateStreamingAssistant(state);
      break;
    }

    case "tool_use_start": {
      state.chatState = "tool_executing";

      // 工具调用前的模型推理 → thinking
      flushBufferAsThinking(state);
      // 清除临时助手消息（如果还没有内容）
      if (state.currentAssistantId) {
        const assistant = findMessageById(
          state.messages,
          state.currentAssistantId
        ) as AssistantTextMessage | undefined;
        if (assistant && !assistant.content.trim()) {
          state.messages = state.messages.filter((m) => m.id !== assistant.id);
        }
        state.currentAssistantId = null;
      }

      const tool: ToolUseMessage = {
        id: uid("tool"),
        type: "tool_use",
        toolName: msg.toolName,
        toolUseId: msg.toolUseId,
        input: formatToolInput(msg.input),
        timestamp: Date.now(),
      };
      state.messages.push(tool);
      state.activeToolUseId = msg.toolUseId;
      break;
    }

    case "tool_use_complete": {
      // 工具输入已经补齐，无需额外操作
      break;
    }

    case "tool_result": {
      state.messages.push({
        id: uid("tool-result"),
        type: "tool_result",
        toolUseId: msg.toolUseId,
        content: formatToolOutput(msg.content),
        isError: msg.isError,
        timestamp: Date.now(),
      });
      state.activeToolUseId = null;
      break;
    }

    case "message_complete": {
      // 流结束，将缓冲区内容作为最终回答
      flushBufferAsAssistant(state);
      state.currentAssistantId = null;
      state.activeThinkingId = null;
      state.activeToolUseId = null;
      state.contentBuffer = "";
      state.chatState = "idle";
      break;
    }

    case "error": {
      if (state.currentAssistantId) {
        const assistant = findMessageById(
          state.messages,
          state.currentAssistantId
        ) as AssistantTextMessage | undefined;
        if (assistant) {
          assistant.status = "error";
        }
      }
      state.messages.push({
        id: uid("error"),
        type: "error",
        message: msg.message,
        timestamp: Date.now(),
      });
      state.currentAssistantId = null;
      state.activeThinkingId = null;
      state.activeToolUseId = null;
      state.chatState = "idle";
      break;
    }

    default:
      break;
  }
}

export function useAgentChat(): UseAgentChatResult {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [status, setStatus] = useState<UseAgentChatResult["status"]>("idle");
  const [error, setError] = useState<string | null>(null);

  const stateRef = useRef<ChatState>(createChatState());
  const translatorRef = useRef(new AgentEventTranslator());

  const resetState = useCallback(() => {
    stateRef.current = createChatState();
    translatorRef.current.reset();
  }, []);

  const flush = useCallback(() => {
    const state = stateRef.current;
    const snapshot = `${state.chatState}|${state.messages.length}|${state.messages
      .map((m) => {
        if (m.type === "assistant_text") return `a:${m.content.length}:${m.status}`;
        if (m.type === "thinking") return `t:${m.content.length}`;
        if (m.type === "tool_use") return `u:${m.toolName}`;
        if (m.type === "tool_result") return `r:${m.content.length}:${m.isError}`;
        return m.type;
      })
      .join(",")}`;
    if (snapshot === state.lastSnapshot) return;
    state.lastSnapshot = snapshot;
    setMessages([...state.messages]);
  }, []);

  const dispatchEvents = useCallback(
    (chunk: unknown) => {
      const msgs = translatorRef.current.translate(chunk);
      for (const msg of msgs) {
        dispatchMessage(stateRef.current, msg);
      }
      flush();
    },
    [flush]
  );

  const handleError = useCallback(
    (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      const state = stateRef.current;
      flushBufferAsThinking(state);
      if (state.currentAssistantId) {
        state.messages = updateMessageById(
          state.messages,
          state.currentAssistantId,
          (m) =>
            m.type === "assistant_text" ? { ...m, status: "error" } : m
        );
        state.currentAssistantId = null;
      }
      state.activeThinkingId = null;
      state.activeToolUseId = null;
      state.contentBuffer = "";
      state.chatState = "idle";
      flush();
      setStatus("idle");
    },
    [flush]
  );

  const handleFinish = useCallback(() => {
    const state = stateRef.current;
    flushBufferAsAssistant(state);
    state.currentAssistantId = null;
    state.activeThinkingId = null;
    state.activeToolUseId = null;
    state.contentBuffer = "";
    state.chatState = "idle";
    flush();
    setStatus("idle");
  }, [flush]);

  const client = useMemo(
    () =>
      new Client({
        apiUrl: API_URL,
        callerOptions: {
          fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
            const response = await fetch(input, init);
            if (
              typeof input === "string" &&
              input.includes("/runs/stream")
            ) {
              if (import.meta.env.DEV) {
                const clone = response.clone();
                void clone
                  .text()
                  .then((text) =>
                    console.debug("[SDK RESPONSE]", text.slice(0, 2000))
                  )
                  .catch(() => {});
              }
            }
            return response;
          },
        },
        onRequest: (url, init) => {
          if (import.meta.env.DEV && url.toString().includes("/runs/stream")) {
            // eslint-disable-next-line no-console
            console.debug("[SDK REQUEST BODY]", init.body);
          }
          return init;
        },
      }),
    []
  );

  const stream = useStream<AgentState>({
    client,
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
    reconnectOnMount: false,
    onError: handleError,
    onLangChainEvent: dispatchEvents,
    onFinish: handleFinish,
  });

  const stop = useCallback(() => {
    void stream.stop();
  }, [stream]);

  const send = useCallback(
    async (message: string, options?: SendOptions) => {
      if (!message.trim() || stream.isLoading) return;

      resetState();
      setStatus("streaming");
      setError(null);

      const nextMessages = [...stateRef.current.messages];
      if (options?.pushUserMessage !== false) {
        nextMessages.push({
          id: uid("user"),
          type: "user_text",
          content: message,
          timestamp: Date.now(),
        });
      }
      stateRef.current.messages = nextMessages;
      stateRef.current.currentAssistantId = null;
      stateRef.current.activeThinkingId = null;
      stateRef.current.activeToolUseId = null;
      flush();

      await stream.submit(
        {
          messages: [{ type: "human", content: message }],
          task_status: "incomplete",
        },
        {
          streamMode: ["values", "events"],
          config: { recursion_limit: 30 },
        }
      );
    },
    [stream, resetState, flush]
  );

  return {
    messages,
    status,
    error,
    send,
    stop,
  };
}
