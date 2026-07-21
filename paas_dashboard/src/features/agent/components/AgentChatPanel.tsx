import { useEffect, useMemo, useRef, useState } from "react";
import { useChat } from "ai/react";
import { Bubble, Sender } from "@ant-design/x";
import type { BubbleItemType, Info } from "@ant-design/x/es/bubble/interface";
import { XMarkdown } from "@ant-design/x-markdown";
import { markedHighlight } from "marked-highlight";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import "../styles/agent-chat.css";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const AGENT_EVENT_RE = /<<<AGENT_EVENT\|([\s\S]*?)\|AGENT_EVENT>>>/g;

type ChatMode = "chat" | "requirements" | "generating";

interface Question {
  id: string;
  text: string;
  reason?: string;
  suggestions?: string[];
}

interface RequirementsPayload {
  session_id: string;
  task: string;
  questions: Question[];
  requirements_doc: Record<string, any>;
}

interface ThinkingStep {
  id: string;
  title: string;
  detail?: string;
  status: "running" | "done" | "error";
  timestamp: number;
}

interface AgentStepPayload {
  id: string;
  title: string;
  detail?: string;
  status: "running" | "done" | "error";
}

/**
 * 将后端 SSE 流解析为纯文本流，供 Vercel AI SDK useChat 在 streamMode: 'text' 下消费。
 * 自定义事件标记会作为普通文本帧透传，由组件在 messages 中统一识别，避免在 fetch
 * 层截断导致 useChat 内部状态机错乱。
 */
async function customFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const response = await fetch(input, init);

  if (!response.ok || !response.body) {
    return response;
  }

  const contentType = response.headers.get("content-type") || "";
  const isSSE = contentType.includes("text/event-stream");

  // 非 SSE 直接透传，方便在控制台看到后端真实返回。
  if (!isSSE) {
    return response;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let buffer = "";
      let dataBuffer: string[] = [];

      const flushEvent = () => {
        if (dataBuffer.length > 0) {
          const data = dataBuffer.join("\n");
          controller.enqueue(encoder.encode(data));
          dataBuffer = [];
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          buffer += decoder.decode();
          if (buffer.trimEnd()) {
            buffer.split("\n").forEach((line) => {
              if (line.startsWith("data:")) {
                dataBuffer.push(line.slice(5).replace(/^\s/, ""));
              }
            });
          }
          flushEvent();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, "");
          if (line === "") {
            flushEvent();
          } else if (line.startsWith("data:")) {
            dataBuffer.push(line.slice(5).replace(/^\s/, ""));
          }
        }
      }

      controller.close();
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

function findLastAssistantMessage(
  messages: { role: string; id: string; content: string }[]
) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") return messages[i];
  }
  return null;
}

function safeRenderContent(content: string, role: string): string {
  if (role !== "assistant") return content;
  AGENT_EVENT_RE.lastIndex = 0;
  const withoutMarkers = content.replace(AGENT_EVENT_RE, "").trim();
  if (!withoutMarkers) return "";
  try {
    const parsed = JSON.parse(withoutMarkers);
    return "```json\n" + JSON.stringify(parsed, null, 2) + "\n```";
  } catch {
    return withoutMarkers;
  }
}

function updateSteps(
  prev: ThinkingStep[],
  payload: AgentStepPayload
): ThinkingStep[] {
  const next: ThinkingStep = { ...payload, timestamp: Date.now() };
  const idx = prev.findIndex((s) => s.id === next.id);
  if (idx >= 0) {
    return prev.map((s, i) => (i === idx ? next : s));
  }
  return [...prev, next];
}

function ThinkingSteps({
  steps,
  expanded,
  onToggle,
}: {
  steps: ThinkingStep[];
  expanded: boolean;
  onToggle: () => void;
}) {
  if (steps.length === 0) return null;
  const doneCount = steps.filter((s) => s.status === "done").length;
  return (
    <div className="agent-chat-thinking-panel">
      <button
        type="button"
        className="agent-chat-thinking-toggle"
        onClick={onToggle}
      >
        {expanded ? "收起" : "展开"}执行步骤 ({doneCount}/{steps.length})
      </button>
      {expanded && (
        <div className="agent-chat-thinking-list">
          {steps.map((step) => (
            <div
              key={step.id}
              className={`agent-chat-thinking-item agent-chat-thinking-item--${step.status}`}
            >
              <span className="agent-chat-thinking-icon">
                {step.status === "running"
                  ? "⏳"
                  : step.status === "error"
                  ? "❌"
                  : "✅"}
              </span>
              <span className="agent-chat-thinking-title">{step.title}</span>
              {step.detail ? (
                <span className="agent-chat-thinking-detail">{step.detail}</span>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface AgentChatPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function AgentChatPanel({ isOpen, onToggle }: AgentChatPanelProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const [mode, setMode] = useState<ChatMode>("chat");
  const [requirements, setRequirements] = useState<RequirementsPayload | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [generatingText, setGeneratingText] = useState<string>("");
  const [generatingError, setGeneratingError] = useState<string | null>(null);
  const [isSubmittingAnswers, setIsSubmittingAnswers] = useState<boolean>(false);
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const generateAbortRef = useRef<AbortController | null>(null);

  const {
    messages,
    input,
    setInput,
    handleSubmit,
    isLoading,
    stop,
    error,
    setMessages,
  } = useChat({
    api: `${BASE_URL}/admin/agent/chat`,
    streamMode: "text",
    experimental_prepareRequestBody: ({ messages: chatMessages }) => {
      const lastMessage = chatMessages[chatMessages.length - 1];
      return { message: lastMessage?.content || "" };
    },
    fetch: customFetch,
    keepLastMessageOnError: true,
  });

  // 监听消息中的自定义事件标记，触发模式切换、步骤更新与结果展示。
  // 注意：最终 Markdown 答案已经在 SSE 文本帧中通过 useChat 流式写入 assistant 消息，
  // 因此这里解析到 pipeline_result 时只切换模式与收起步骤面板，不再追加重复消息。
  useEffect(() => {
    const lastAssistant = findLastAssistantMessage(messages);
    if (!lastAssistant) return;

    AGENT_EVENT_RE.lastIndex = 0;
    const matches = [...lastAssistant.content.matchAll(AGENT_EVENT_RE)];
    if (matches.length === 0) return;

    matches.forEach((m) => {
      try {
        const event = JSON.parse(m[1]);
        if (event.type === "requirements_gathering" && event.payload) {
          setMode("requirements");
          setRequirements(event.payload as RequirementsPayload);
          setAnswers({});
          setThinkingSteps([]);
          setStepsExpanded(true);
        } else if (event.type === "agent_step" && event.payload) {
          setThinkingSteps((prev) =>
            updateSteps(prev, event.payload as AgentStepPayload)
          );
        } else if (event.type === "pipeline_result" && event.payload) {
          setMode("chat");
          setRequirements(null);
          setStepsExpanded(false);
        }
      } catch {
        // 忽略无法解析的标记
      }
    });
  }, [messages]);

  const markdownConfig = useMemo(
    () =>
      markedHighlight({
        langPrefix: "hljs language-",
        highlight(code, lang) {
          const language = hljs.getLanguage(lang) ? lang : "plaintext";
          return hljs.highlight(code, { language }).value;
        },
      }),
    []
  );

  const items = useMemo<BubbleItemType[]>(() => {
    const list: BubbleItemType[] = messages
      .map((msg) => {
        const rendered = safeRenderContent(msg.content, msg.role);
        if (msg.role === "assistant" && !rendered.trim()) return null;
        return {
          key: msg.id,
          role: msg.role === "user" ? "user" : "ai",
          content: rendered,
        } as BubbleItemType;
      })
      .filter(Boolean) as BubbleItemType[];

    if (mode === "generating") {
      list.push({
        key: "generating",
        role: "ai",
        content: generatingText || "正在生成模块，请稍候...",
        loading: !generatingText && !generatingError,
      } as BubbleItemType);
    }

    if (
      isLoading &&
      mode === "chat" &&
      (list.length === 0 || list[list.length - 1].role === "user")
    ) {
      list.push({
        key: "loading",
        role: "ai",
        content: "",
        loading: true,
      } as BubbleItemType);
    }

    return list;
  }, [messages, mode, generatingText, generatingError, isLoading]);

  const lastAiKey = useMemo(() => {
    for (let i = items.length - 1; i >= 0; i--) {
      if (items[i].role === "ai") return items[i].key;
    }
    return null;
  }, [items]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [items]);

  const handleSubmitAnswers = async () => {
    if (!requirements || isSubmittingAnswers) return;

    setIsSubmittingAnswers(true);
    setGeneratingError(null);

    try {
      const res = await fetch(
        `${BASE_URL}/admin/agent/sessions/${requirements.session_id}/answers`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answers }),
        }
      );
      if (!res.ok) {
        throw new Error(`提交失败：${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      const nextQuestions: Question[] = data.questions || [];
      const confirmed = data.status === "requirements_confirmed";

      if (confirmed || nextQuestions.length === 0) {
        setMode("generating");
        setRequirements(null);
        setAnswers({});
        await triggerGenerate(requirements.session_id);
      } else {
        setRequirements((prev) =>
          prev
            ? {
                ...prev,
                questions: nextQuestions,
                requirements_doc:
                  data.requirements_doc || prev.requirements_doc,
              }
            : null
        );
        setAnswers({});
      }
    } catch (err) {
      setGeneratingError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmittingAnswers(false);
    }
  };

  const triggerGenerate = async (sessionId: string) => {
    setMode("generating");
    setGeneratingText("");
    setGeneratingError(null);
    setThinkingSteps([]);
    setStepsExpanded(true);

    const abortController = new AbortController();
    generateAbortRef.current = abortController;

    let currentGeneratingText = "";

    try {
      const res = await fetch(
        `${BASE_URL}/admin/agent/sessions/${sessionId}/generate`,
        {
          method: "POST",
          headers: { Accept: "text/event-stream" },
          signal: abortController.signal,
        }
      );
      if (!res.ok) {
        throw new Error(`生成请求失败：${res.status} ${res.statusText}`);
      }
      if (!res.body) {
        throw new Error("响应体为空");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let dataBuffer: string[] = [];
      let receivedResult = false;

      const flushEvent = () => {
        if (dataBuffer.length === 0) return;
        const frame = dataBuffer.join("\n");
        dataBuffer = [];
        if (!frame.trim()) return;

        AGENT_EVENT_RE.lastIndex = 0;
        const match = AGENT_EVENT_RE.exec(frame);
        if (match) {
          try {
            const event = JSON.parse(match[1]);
            if (event.type === "agent_step" && event.payload) {
              setThinkingSteps((prev) =>
                updateSteps(prev, event.payload as AgentStepPayload)
              );
            } else if (event.type === "pipeline_result" && event.payload) {
              receivedResult = true;
              setStepsExpanded(false);
              // 把已流式输出的 Markdown 固化为一条正式 assistant 消息
              const finalContent = currentGeneratingText.trimEnd();
              if (finalContent) {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `gen-result-${Date.now()}`,
                    role: "assistant",
                    content: finalContent,
                    createdAt: new Date(),
                  } as any,
                ]);
              }
              setGeneratingText("");
              setMode("chat");
            }
          } catch {
            // 忽略无法解析的标记
          }
          return;
        }

        // 普通文本帧追加到生成内容
        currentGeneratingText += frame;
        setGeneratingText(currentGeneratingText);
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          buffer += decoder.decode();
          if (buffer.trimEnd()) {
            buffer.split("\n").forEach((line) => {
              if (line.startsWith("data:")) {
                dataBuffer.push(line.slice(5).replace(/^\s/, ""));
              }
            });
          }
          flushEvent();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, "");
          if (line === "") {
            flushEvent();
          } else if (line.startsWith("data:")) {
            dataBuffer.push(line.slice(5).replace(/^\s/, ""));
          }
        }
      }

      if (!receivedResult) {
        throw new Error("生成响应中未找到结果标记");
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setGeneratingError("生成已取消");
      } else {
        setGeneratingError(err instanceof Error ? err.message : String(err));
      }
      setMode("chat");
    } finally {
      generateAbortRef.current = null;
    }
  };

  const handleCancelRequirements = () => {
    setMode("chat");
    setRequirements(null);
    setAnswers({});
  };

  const renderRequirementsCard = () => {
    if (!requirements) return null;
    return (
      <div
        style={{
          padding: 16,
          borderRadius: 8,
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          maxHeight: "calc(100vh - 200px)",
          overflowY: "auto",
        }}
      >
        <h4 style={{ margin: "0 0 12px", fontSize: 15, color: "#0f172a" }}>
          需求确认
        </h4>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "#64748b" }}>
          请回答以下问题，帮助我更好地理解你的模块需求。
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {requirements.questions.map((q) => (
            <div key={q.id}>
              <label
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#334155",
                  marginBottom: 6,
                }}
              >
                {q.text}
              </label>
              {q.reason && (
                <div
                  style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}
                >
                  {q.reason}
                </div>
              )}
              {q.suggestions && q.suggestions.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 6,
                    marginBottom: 8,
                  }}
                >
                  {q.suggestions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() =>
                        setAnswers((prev) => ({ ...prev, [q.id]: s }))
                      }
                      style={{
                        padding: "4px 10px",
                        fontSize: 12,
                        borderRadius: 12,
                        border: "1px solid #cbd5e1",
                        background: "#ffffff",
                        color: "#475569",
                        cursor: "pointer",
                        lineHeight: 1.4,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "#f1f5f9";
                        e.currentTarget.style.borderColor = "#94a3b8";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "#ffffff";
                        e.currentTarget.style.borderColor = "#cbd5e1";
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              <textarea
                value={answers[q.id] || ""}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                }
                rows={2}
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  fontSize: 13,
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
                placeholder="请输入你的回答..."
              />
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
          <button
            onClick={handleSubmitAnswers}
            disabled={isSubmittingAnswers}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "none",
              background: isSubmittingAnswers ? "#93c5fd" : "#3b82f6",
              color: "#fff",
              cursor: isSubmittingAnswers ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {isSubmittingAnswers ? "提交中..." : "提交答案"}
          </button>
          <button
            onClick={handleCancelRequirements}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "1px solid #cbd5e1",
              background: "#fff",
              color: "#64748b",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            取消
          </button>
        </div>
        {generatingError && (
          <div style={{ marginTop: 12, color: "#ef4444", fontSize: 13 }}>
            {generatingError}
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        width: isOpen ? 320 : 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRight: isOpen ? "1px solid #e2e8f0" : "none",
        background: "#ffffff",
        flexShrink: 0,
        overflow: "hidden",
        opacity: isOpen ? 1 : 0,
        transition: "width 300ms ease-in-out, opacity 300ms ease-in-out",
      }}
    >
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid #e2e8f0",
          background: "#fafafa",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: 16, color: "#0f172a" }}>
            AI 智能体助手
          </h3>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#64748b" }}>
            输入自然语言任务，自动生成并部署模块；也可咨询平台使用问题
          </p>
        </div>
        <button
          onClick={onToggle}
          aria-label={isOpen ? "收起侧边栏" : "展开侧边栏"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            borderRadius: 6,
            border: "1px solid #e2e8f0",
            background: "#ffffff",
            color: "#64748b",
            cursor: "pointer",
            fontSize: 14,
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          {isOpen ? "◀" : "▶"}
        </button>
      </div>

      <div
        ref={listRef}
        style={{
          flex: 1,
          overflow: "auto",
          padding: 16,
          background: "#ffffff",
        }}
      >
        {items.length === 0 && mode === "chat" && (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "#94a3b8",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 14 }}>开始与智能体对话</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              例如：创建用户模块、如何使用这个平台
            </div>
          </div>
        )}

        {items.length > 0 && (
          <Bubble.List
            items={items}
            autoScroll
            role={{
              user: { placement: "end" },
              ai: {
                placement: "start",
                variant: "borderless",
                classNames: { content: "agent-chat-ai-borderless" },
                header: (_content: string, info: Info) => {
                  if (
                    thinkingSteps.length === 0 ||
                    info.key !== lastAiKey
                  ) {
                    return null;
                  }
                  return (
                    <ThinkingSteps
                      steps={thinkingSteps}
                      expanded={stepsExpanded}
                      onToggle={() => setStepsExpanded((e) => !e)}
                    />
                  );
                },
                contentRender: (content: string, info: Info) => (
                  <XMarkdown
                    content={content}
                    className="agent-chat-markdown"
                    config={markdownConfig}
                    streaming={{
                      hasNextChunk:
                        (isLoading &&
                          info.key === lastAiKey &&
                          mode === "chat") ||
                        (mode === "generating" && info.key === "generating"),
                      tail: true,
                    }}
                  />
                ),
              },
            }}
          />
        )}

        {generatingError && mode === "chat" && (
          <div
            style={{
              margin: "12px 16px 0",
              padding: 10,
              borderRadius: 6,
              background: "#fee2e2",
              color: "#991b1b",
              fontSize: 13,
            }}
          >
            生成出错：{generatingError}
          </div>
        )}

        {error && mode === "chat" && (
          <div
            style={{
              marginTop: 12,
              padding: 10,
              borderRadius: 6,
              background: "#fee2e2",
              color: "#991b1b",
              fontSize: 13,
            }}
          >
            请求出错：{error.message}
          </div>
        )}
      </div>

      <div
        style={{
          padding: 16,
          borderTop: "1px solid #e2e8f0",
          background: "#fafafa",
        }}
      >
        {mode === "requirements" ? (
          renderRequirementsCard()
        ) : (
          <Sender
            value={input}
            onChange={(value) => setInput(value)}
            onSubmit={() => handleSubmit()}
            loading={isLoading || mode === "generating"}
            onCancel={() => {
              stop();
              generateAbortRef.current?.abort();
            }}
            submitType="enter"
            placeholder={
              mode === "generating"
                ? "模块生成中，请稍候..."
                : "输入任务或问题，例如：创建用户模块..."
            }
            autoSize={{ minRows: 1, maxRows: 6 }}
          />
        )}
      </div>
    </div>
  );
}
