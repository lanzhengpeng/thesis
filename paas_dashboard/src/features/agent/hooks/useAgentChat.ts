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

/** 从 judge（react_1）的输出中提取真正的最终回答，用于流式展示。 */
function extractFinalAnswer(judgeOutput: string): string {
  const useful = judgeOutput
    .split("\n")
    .filter(
      (line) =>
        !line.trim().startsWith("任务状态：") &&
        !line.trim().startsWith("任务状态:")
    )
    .join("\n")
    .trim();
  const marker = "最终回答：";
  const idx = useful.lastIndexOf(marker);
  if (idx >= 0) {
    return useful.slice(idx + marker.length).trim();
  }
  return "";
}

function cleanFinalAnswer(content: string): string {
  const lines = content.split("\n");
  const useful = lines.filter(
    (line) =>
      !line.trim().startsWith("任务状态：") && !line.trim().startsWith("任务状态:")
  );
  const joined = useful.join("\n").trim();
  const marker = "最终回答：";
  const idx = joined.lastIndexOf(marker);
  if (idx >= 0) {
    return joined.slice(idx + marker.length).trim();
  }
  return joined;
}

/** 从 LangGraph chunk 中安全提取字符串 content。 */
function getChunkContent(chunk: unknown): string {
  const raw = (chunk as any)?.content;
  if (typeof raw === "string") return raw;
  if (raw === null || raw === undefined) return "";
  // 某些模型/后端会把 content 包装成对象或数组，这里兜底转成字符串避免 [object Object]
  if (typeof raw === "object") {
    return JSON.stringify(raw);
  }
  return String(raw);
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
  /** 当前所在的 react_* 子图节点名称；react_1 为 judge，其输出应作为最终答案直接展示 */
  currentReactNode: string | null;
  /** react_1（judge）的原始输出缓存，用于流式提取最终回答 */
  judgeBuffer: string;
  /** 上次 flush 的状态快照，用于去重减少无效渲染 */
  lastSnapshot: string;
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
    currentReactNode: null,
    judgeBuffer: "",
    lastSnapshot: "",
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
    // 用轻量快照避免完全相同的状态重复触发 setMessages，减少无效重渲染
    const snapshot = `${rootActive}|${finalOutput.length}|${cycles.length}|${cycles
      .map((c) => `${c.status}:${c.steps.length}:${c.steps.map((s) => s.status).join(",")}`)
      .join(";")}`;
    if (snapshot === parserRef.current.lastSnapshot) return;
    parserRef.current.lastSnapshot = snapshot;
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
          p.currentReactNode = name;
          // react_1 是 judge 节点，其输出应作为消息级最终答案直接展示，
          // 不再为其创建可见的 ReAct cycle / think step，避免最终回答重复渲染。
          if (name === "react_1") {
            // 防止上个 react 节点的 cycle 未关闭
            if (p.currentCycle) {
              p.currentCycle.status = "success";
              p.currentCycle = null;
            }
            p.finalOutput = "";
            p.streamingOutput = "";
            p.judgeBuffer = "";
            flush();
            return;
          }
          p.currentCycle = {
            id: uid("cycle"),
            steps: [],
            status: "loading",
          };
          p.cycles.push(p.currentCycle);
          flush();
        } else if (name === "call_model") {
          // 每个 call_model 在当前 ReAct cycle 中追加一个 think step，
          // 不再为每次模型调用单独开 cycle（cycle 对应 react_ 节点）。
          // react_1（judge）内部的 call_model 不创建可见 think step。
          if (p.currentReactNode === "react_1") {
            return;
          }
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
        // 根节点结束时也要清理元信息，避免把"任务状态：已完成"等显示给用户
        p.finalOutput = cleanFinalAnswer(String(last?.content ?? ""));
      }
      removeEmptyCycles();
      flush();
        } else if (isReactNode) {
          if (p.currentCycle) {
            p.currentCycle.status = "success";
            p.currentCycle = null;
          }
          p.currentReactNode = null;
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
        const lastContent = getChunkContent(last);
        const hasContent = lastContent.trim().length > 0;

        if (hasContent) {
          p.lastModelContent = lastContent;
          p.currentCycle.finalContent = lastContent;
          if (thinkStep) thinkStep.status = "success";
          p.streamingOutput = "";
          p.finalOutput = lastContent;
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
      const content = getChunkContent(data?.chunk);
      if (!content) return;
      if (p.reflectActive) {
        p.reflectBuffer += content;
          flush();
        } else if (p.currentReactNode === "react_1") {
          // judge 节点（react_1）的输出即为最终回答，直接作为消息级答案展示，
          // 避免再生成一个可见的 think step 导致最终回答重复渲染。
          // 这里实时提取“最终回答：”之后的内容，避免把“任务状态：”等元信息也展示出来。
          p.judgeBuffer += content;
          p.finalOutput = extractFinalAnswer(p.judgeBuffer);
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
      p.finalOutput = cleanFinalAnswer(p.lastModelContent);
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
              // 仅在开发环境记录 SDK 响应的前 2000 字符，便于调试流式接口。
              if (import.meta.env.DEV) {
                const clone = response.clone();
                void clone
                  .text()
                  .then((text) => console.debug("[SDK RESPONSE]", text.slice(0, 2000)))
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
