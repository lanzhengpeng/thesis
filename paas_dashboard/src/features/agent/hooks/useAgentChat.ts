import { useCallback, useMemo, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { Client } from "@langchain/langgraph-sdk";

const API_URL = import.meta.env.VITE_LANGGRAPH_API_URL ?? "http://localhost:8123";
const ASSISTANT_ID = "paas-agent";

export type ReactStepType = "think" | "tool";

export interface ThinkStep {
  type: "think";
  title: string;
  content: string;
  status: "loading" | "success" | "error";
}

export interface ToolStep {
  type: "tool";
  title: string;
  name: string;
  input?: string;
  output?: string;
  status: "loading" | "success" | "error";
}

export type ReactStep = ThinkStep | ToolStep;

export interface ReactCycle {
  id: string;
  steps: ReactStep[];
  /** 该 ReAct 迭代中 model 没有发起 tool call 的那次输出 */
  finalContent?: string;
  status: "loading" | "success" | "error";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  /** Agent 运行结束后最终模型输出 */
  content: string;
  status?: "loading" | "done" | "error";
  cycles?: ReactCycle[];
  createdAt: number;
}

export interface UseAgentChatResult {
  messages: ChatMessage[];
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

function updateAssistantMessage(
  messages: ChatMessage[],
  updater: (msg: ChatMessage) => ChatMessage
): ChatMessage[] {
  const lastIdx = messages.findLastIndex((m) => m.role === "assistant");
  if (lastIdx < 0) return messages;
  const next = [...messages];
  next[lastIdx] = updater({ ...next[lastIdx] });
  return next;
}

interface ParserState {
  cycles: ReactCycle[];
  currentCycle: ReactCycle | null;
  toolStack: ToolStep[];
  finalOutput: string;
  lastModelContent: string;
  rootActive: boolean;
  reflectBuffer: string;
  reflectActive: boolean;
  processedChainEvents: Set<string>;
  hasReactNodes: boolean;
  streamingOutput: string;
}

function createParserState(): ParserState {
  return {
    cycles: [],
    currentCycle: null,
    toolStack: [],
    finalOutput: "",
    lastModelContent: "",
    rootActive: false,
    reflectBuffer: "",
    reflectActive: false,
    processedChainEvents: new Set<string>(),
    hasReactNodes: false,
    streamingOutput: "",
  };
}

export function useAgentChat(): UseAgentChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<UseAgentChatResult["status"]>("idle");
  const [error, setError] = useState<string | null>(null);

  const parserRef = useRef<ParserState>(createParserState());

  const resetParser = useCallback(() => {
    parserRef.current = createParserState();
  }, []);

  const flush = useCallback(() => {
    const { cycles, finalOutput, rootActive } = parserRef.current;
    setMessages((prev) =>
      updateAssistantMessage(prev, (msg) => ({
        ...msg,
        cycles: [...cycles],
        content: finalOutput,
        status: rootActive ? "loading" : "done",
      }))
    );
  }, []);

  const removeEmptyCycles = useCallback(() => {
    parserRef.current.cycles = parserRef.current.cycles.filter(
      (c) => c.steps.length > 0 || c.finalContent
    );
  }, []);

  const parseEvent = useCallback(
    (chunk: unknown) => {
      const p = parserRef.current;

      const event: string = (chunk as any)?.event ?? "";
      const name: string = (chunk as any)?.name ?? "";
      const data: any = (chunk as any)?.data ?? {};
      const parentIds: string[] = (chunk as any)?.parent_ids ?? [];
      const runId: string = (chunk as any)?.run_id ?? "";
      const isRoot = parentIds.length === 0;
      const isReactNode = name.startsWith("react_");

      // LangGraph v2 会重复发送 chain 事件（task / checkpoint），
      // 用签名去重，避免产生重复 Cycle / 重复 Step。
      if (event === "on_chain_start" || event === "on_chain_end") {
        const signature = `${event}|${name}|${runId}|${parentIds.join(",")}`;
        if (p.processedChainEvents.has(signature)) return;
        p.processedChainEvents.add(signature);
      }

      if (event === "on_chain_start") {
        if (isRoot) {
          p.rootActive = true;
          flush();
        } else if (isReactNode) {
          p.hasReactNodes = true;
          p.currentCycle = {
            id: uid("cycle"),
            steps: [],
            status: "loading",
          };
          p.cycles.push(p.currentCycle);
          flush();
        } else if (name === "call_model") {
          if (!p.hasReactNodes) {
            if (p.currentCycle && p.currentCycle.status === "loading") {
              p.currentCycle.status = "success";
            }
            p.currentCycle = null;
          }

          // Within a ReAct node each model invocation represents a new reasoning
          // iteration; give it its own cycle so steps don't collapse together.
          if (!p.currentCycle || p.currentCycle.status !== "loading") {
            p.currentCycle = {
              id: uid("cycle"),
              steps: [],
              status: "loading",
            };
            p.cycles.push(p.currentCycle);
          }

          const pendingReflect = p.reflectBuffer;
          p.reflectBuffer = "";
          p.streamingOutput = "";
          p.finalOutput = "";

          const step: ThinkStep = {
            type: "think",
            title: "思考过程",
            content: pendingReflect,
            status: "loading",
          };
          p.currentCycle.steps.push(step);
          flush();
        } else if (name === "reflect") {
          p.reflectActive = true;
          p.reflectBuffer = "";
        } else if (name === "call_tools") {
          // 具体工具步骤由 on_tool_start/on_tool_end 创建
        }
        return;
      }

      if (event === "on_chain_end") {
        if (isRoot) {
          p.rootActive = false;
          const outMessages = data?.output?.messages;
          if (Array.isArray(outMessages) && outMessages.length > 0) {
            const last = outMessages[outMessages.length - 1];
            p.finalOutput = last?.content ?? "";
          }
          removeEmptyCycles();
          flush();
        } else if (isReactNode) {
          if (p.currentCycle) {
            p.currentCycle.status = "success";
            p.currentCycle = null;
          }
          removeEmptyCycles();
          flush();
        } else if (name === "call_model") {
          if (p.currentCycle) {
            const outMessages = data?.output?.messages;
            const thinkStep = p.currentCycle.steps
              .filter((s): s is ThinkStep => s.type === "think")
              .find((s) => s.status === "loading");

            if (Array.isArray(outMessages) && outMessages.length > 0) {
              const last = outMessages[outMessages.length - 1];
              const hasToolCalls =
                Array.isArray(last?.tool_calls) && last.tool_calls.length > 0;
              const hasContent =
                typeof last?.content === "string" &&
                last.content.trim().length > 0;

              if (hasContent) {
                p.lastModelContent = last.content;
                p.currentCycle.finalContent = last.content;
                p.currentCycle.status = "success";
                if (thinkStep) thinkStep.status = "success";
                p.streamingOutput = "";
                p.finalOutput = last.content;
                flush();
                return;
              }

              if (thinkStep && hasToolCalls && !thinkStep.content.trim()) {
                const idx = p.currentCycle.steps.indexOf(thinkStep);
                if (idx >= 0) p.currentCycle.steps.splice(idx, 1);
                p.streamingOutput = "";
                p.finalOutput = "";
                flush();
                return;
              }
            }

            if (thinkStep) thinkStep.status = "success";
            p.streamingOutput = "";
            p.finalOutput = "";
            flush();
          }
        } else if (name === "reflect") {
          p.reflectActive = false;
          flush();
        } else if (name === "call_tools") {
          // 工具块结束，具体工具步骤已在 on_tool_end 完成
        }
        return;
      }

      if (event === "on_chat_model_stream") {
        const content: string = data?.chunk?.content ?? "";
        if (!content) return;
        if (p.reflectActive) {
          p.reflectBuffer += content;
          flush();
        } else if (p.currentCycle) {
          const thinkStep = p.currentCycle.steps
            .filter((s): s is ThinkStep => s.type === "think")
            .find((s) => s.status === "loading");
          if (thinkStep) {
            thinkStep.content += content;
            p.streamingOutput += content;
            p.finalOutput = p.streamingOutput;
            flush();
          }
        }
        return;
      }

      if (event === "on_tool_start") {
        if (p.currentCycle) {
          const toolName = data?.tool ?? name ?? "工具";
          const step: ToolStep = {
            type: "tool",
            title: toolName,
            name: toolName,
            input: data?.input
              ? JSON.stringify(data.input, null, 2)
              : undefined,
            output: undefined,
            status: "loading",
          };
          p.toolStack.push(step);
          p.currentCycle.steps.push(step);
          flush();
        }
        return;
      }

      if (event === "on_tool_end") {
        const step = p.toolStack.pop();
        if (step) {
          step.output = formatToolOutput(data?.output);
          step.status = "success";
          flush();
        }
        return;
      }
    },
    [flush, removeEmptyCycles]
  );

  const handleError = useCallback((err: unknown) => {
    const message = err instanceof Error ? err.message : String(err);
    setError(message);
    setMessages((prev) =>
      updateAssistantMessage(prev, (msg) => ({ ...msg, status: "error" }))
    );
    setStatus("idle");
  }, []);

  const handleFinish = useCallback(() => {
    const p = parserRef.current;
    p.cycles.forEach((c) => {
      if (c.status === "loading") c.status = "success";
    });
    p.rootActive = false;
    removeEmptyCycles();
    if (!p.finalOutput && p.lastModelContent) {
      p.finalOutput = p.lastModelContent;
    }
    flush();
    setMessages((prev) =>
      updateAssistantMessage(prev, (msg) =>
        msg.status === "loading" ? { ...msg, status: "done" } : msg
      )
    );
    setStatus("idle");
  }, [flush, removeEmptyCycles]);

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
              // Log without awaiting the full body so the SDK can process
              // the stream incrementally.
              const clone = response.clone();
              void clone
                .text()
                .then((text) => console.log("[SDK RESPONSE]", text.slice(0, 2000)))
                .catch(() => {});
            }
            return response;
          },
        },
        onRequest: (url, init) => {
          if (url.toString().includes("/runs/stream")) {
            console.log("[SDK REQUEST BODY]", init.body);
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
    onLangChainEvent: parseEvent,
    onFinish: handleFinish,
  });

  const stop = useCallback(() => {
    void stream.stop();
  }, [stream.stop]);

  const send = useCallback(
    async (message: string, options?: SendOptions) => {
      if (!message.trim() || stream.isLoading) return;

      resetParser();
      setStatus("streaming");
      setError(null);

      if (options?.pushUserMessage !== false) {
        setMessages((prev) => [
          ...prev,
          {
            id: uid("user"),
            role: "user",
            content: message,
            createdAt: Date.now(),
          },
          {
            id: uid("assistant"),
            role: "assistant",
            content: "",
            status: "loading",
            cycles: [],
            createdAt: Date.now(),
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: uid("assistant"),
            role: "assistant",
            content: "",
            status: "loading",
            cycles: [],
            createdAt: Date.now(),
          },
        ]);
      }

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
    [stream.isLoading, stream.submit, resetParser]
  );

  return {
    messages,
    status,
    error,
    send,
    stop,
  };
}
