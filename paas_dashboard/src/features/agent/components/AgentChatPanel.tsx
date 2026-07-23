import {
  ArrowUpOutlined,
  AudioOutlined,
  BookOutlined,
  BorderOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  CopyOutlined,
  DislikeOutlined,
  DownOutlined,
  EditOutlined,
  FileAddOutlined,
  FileTextOutlined,
  LikeOutlined,
  LoadingOutlined,
  OrderedListOutlined,
  PlusOutlined,
  RedoOutlined,
  SearchOutlined,
  SettingOutlined,
  ShareAltOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { ChevronLeft, History, PanelLeft } from "lucide-react";
import { Sender } from "@ant-design/x";
import { XMarkdown } from "@ant-design/x-markdown";
import "@ant-design/x-markdown/dist/x-markdown.css";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { markedHighlight } from "marked-highlight";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  useAgentChat,
  type ReactCycle,
  type ReactStep,
  type ThinkStep,
  type ToolStep,
} from "../hooks/useAgentChat";
import "../styles/agent-chat.css";

function stepsEqual(a: ReactStep, b: ReactStep): boolean {
  if (a.type !== b.type || a.status !== b.status) return false;
  if (a.type === "think") {
    return a.content === (b as ThinkStep).content;
  }
  const tb = b as ToolStep;
  return a.name === tb.name && a.input === tb.input && a.output === tb.output;
}

function cyclesEqual(a: ReactCycle, b: ReactCycle): boolean {
  if (a.finalContent !== b.finalContent) return false;
  if (a.steps.length !== b.steps.length) return false;
  return a.steps.every((s, i) => stepsEqual(s, b.steps[i]));
}

function dedupeCycles(cycles: ReactCycle[]): ReactCycle[] {
  return cycles.filter(
    (c, idx) =>
      idx === 0 || !cycles.slice(0, idx).some((prev) => cyclesEqual(prev, c))
  );
}

function isSummaryThink(step: ReactStep, finalAnswer: string): boolean {
  if (step.type !== "think") return false;
  const contentTrim = step.content.trim();
  if (!contentTrim) return true;
  if (contentTrim.includes("最终回答：")) return true;
  if (contentTrim.includes("任务状态：已完成")) return true;
  const finalTrim = finalAnswer.trim();
  if (
    finalTrim &&
    (contentTrim === finalTrim ||
      contentTrim.includes(finalTrim) ||
      finalTrim.includes(contentTrim))
  ) {
    return true;
  }
  return false;
}

function visibleCyclesFor(
  cycles: ReactCycle[],
  finalAnswer: string
): ReactCycle[] {
  return cycles
    .map((c) => ({
      ...c,
      steps: c.steps.filter((s) => !isSummaryThink(s, finalAnswer)),
    }))
    .filter((c) => c.steps.length > 0);
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

function MarkdownContent({ content }: { content: string }) {
  const config = useMemo(
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
  if (!content) return null;
  return (
    <XMarkdown
      content={content}
      className="agent-chat-markdown"
      config={config}
    />
  );
}

function getToolDisplay(name: string): { title: string; icon: React.ReactNode } {
  const normalized = name.toLowerCase();
  if (
    normalized.includes("terminal") ||
    normalized.includes("bash") ||
    normalized.includes("command") ||
    normalized.includes("shell")
  ) {
    return { title: "执行命令", icon: <TerminalIcon /> };
  }
  if (normalized.includes("read") && normalized.includes("file")) {
    return { title: "阅读文件", icon: <FileTextOutlined /> };
  }
  if (
    normalized.includes("write") &&
    (normalized.includes("file") || normalized.includes("create"))
  ) {
    return { title: "创建文件", icon: <FileAddOutlined /> };
  }
  if (normalized.includes("search")) {
    return { title: "搜索文件", icon: <SearchOutlined /> };
  }
  if (normalized.includes("plan") || normalized.includes("update_plan")) {
    return { title: "更新计划", icon: <OrderedListOutlined /> };
  }
  if (normalized.includes("skill") || normalized.includes("load")) {
    return { title: "加载技能", icon: <ToolOutlined /> };
  }
  if (normalized.includes("file")) {
    return { title: "文件操作", icon: <FileTextOutlined /> };
  }
  return { title: name, icon: <ToolOutlined /> };
}

function extractToolSummary(step: ToolStep): string {
  if (!step.input) return "";
  try {
    const parsed = JSON.parse(step.input);
    if (parsed.file_path) return parsed.file_path;
    if (parsed.path) return parsed.path;
    if (parsed.command) return parsed.command;
    if (parsed.query) return parsed.query;
    if (parsed.skill) return parsed.skill;
    if (parsed.expression) return parsed.expression;
    if (parsed.arguments) return JSON.stringify(parsed.arguments);
    if (typeof parsed === "string") return parsed;
    return "";
  } catch {
    const trimmed = step.input.trim();
    return trimmed.length > 60 ? `${trimmed.slice(0, 60)}…` : trimmed;
  }
}

function extractFilePath(step: ToolStep): string | null {
  if (!step.input) return null;
  try {
    const parsed = JSON.parse(step.input);
    if (parsed.file_path) return parsed.file_path;
    if (parsed.path) return parsed.path;
    return null;
  } catch {
    return null;
  }
}

function StepIcon({ step }: { step: ReactStep }) {
  if (step.type === "think") return <BulbOutlined />;
  return getToolDisplay(step.name).icon;
}

function StepTitle({ step }: { step: ReactStep }) {
  if (step.type === "think") return "思考过程";
  return getToolDisplay(step.name).title;
}

function CodeBlock({
  code,
  label,
  filePath,
  isOutput,
}: {
  code: string;
  label: string;
  filePath?: string | null;
  isOutput?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const handleCopy = () => {
    void navigator.clipboard.writeText(code);
  };

  const isFile = !!filePath && !isOutput;

  const labelProps = isFile
    ? {
        role: "button" as const,
        tabIndex: 0 as const,
        onClick: () => setOpen((v) => !v),
        onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((v) => !v);
          }
        },
      }
    : {};

  return (
    <div
      className={`agent-step__code ${
        isOutput ? "agent-step__code--output" : ""
      } ${isFile ? "agent-step__code--file" : ""}`.trim()}
    >
      <div
        className="agent-step__label"
        {...labelProps}
      >
        <span className="agent-step__label-left">
          {isFile ? (
            <>
              <FileTextOutlined />
              <span className="agent-step__file-path" title={filePath}>
                {filePath}
              </span>
            </>
          ) : (
            <span>{label}</span>
          )}
        </span>
        <span className="agent-step__label-right">
          {isFile && (
            <span className="agent-step__file-arrow">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M7 7h10v10" />
                <path d="M7 17 17 7" />
              </svg>
            </span>
          )}
          <button
            type="button"
            className="agent-step__copy"
            title="复制"
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
          >
            <CopyOutlined />
          </button>
        </span>
      </div>
      {(!isFile || open) && <pre>{code}</pre>}
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`agent-chevron ${open ? "agent-chevron--open" : ""}`}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m4 17 6-6-6-6" />
      <path d="M12 19h8" />
    </svg>
  );
}

function StepItem({ step }: { step: ReactStep }) {
  const [open, setOpen] = useState(false);
  const summary = step.type === "tool" ? extractToolSummary(step) : "";
  const filePath = step.type === "tool" ? extractFilePath(step) : null;
  const hasContent =
    (step.type === "think" && !!step.content) ||
    (step.type === "tool" && (!!step.input || !!step.output));

  const inputLabel = filePath ? "参数" : "参数";
  const outputLabel = filePath ? "返回" : "返回";

  return (
    <div className="agent-step">
      <button
        type="button"
        className="agent-step__header"
        onClick={() => hasContent && setOpen((v) => !v)}
        disabled={!hasContent}
      >
        <span className="agent-step__left">
          <span className="agent-step__icon">
            <StepIcon step={step} />
          </span>
          <span className="agent-step__title">
            <StepTitle step={step} />
          </span>
          {summary && <span className="agent-step__summary">{summary}</span>}
        </span>
        {hasContent && (
          <span className="agent-step__chevron">
            {step.status === "loading" ? <LoadingOutlined /> : <Chevron open={open} />}
          </span>
        )}
      </button>

      {open && (
        <div className="agent-step__body">
          {step.type === "think" && step.content && (
            <div className="agent-step__content">
              <MarkdownContent content={step.content} />
            </div>
          )}
          {step.type === "tool" && (
            <>
              {step.input && (
                <CodeBlock code={step.input} label={inputLabel} filePath={filePath} />
              )}
              {step.output && (
                <CodeBlock
                  code={step.output}
                  label={outputLabel}
                  filePath={filePath}
                  isOutput
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function CycleItem({
  cycle,
  defaultOpen,
}: {
  cycle: ReactCycle;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen ?? true);
  const prevDefault = useRef(defaultOpen);

  useEffect(() => {
    if (defaultOpen !== prevDefault.current) {
      setOpen(defaultOpen ?? true);
      prevDefault.current = defaultOpen;
    }
  }, [defaultOpen]);

  const done = cycle.steps.filter((s) => s.status !== "loading").length;
  const total = cycle.steps.length;

  return (
    <div className="agent-cycle">
      <button
        type="button"
        className="agent-cycle__header"
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          {open ? "已展开" : "已收起"} {total} 个步骤
        </span>
        {cycle.status === "loading" && (
          <span className="agent-cycle__count">({done}/{total})</span>
        )}
        <Chevron open={open} />
      </button>
      {open && (
        <div className="agent-cycle__steps">
          {cycle.steps.map((step, sIdx) => (
            <StepItem key={`${cycle.id}-${sIdx}`} step={step} />
          ))}
        </div>
      )}
    </div>
  );
}

function ThinkingPanel({ cycles }: { cycles: ReactCycle[] }) {
  const [allOpen, setAllOpen] = useState(true);
  const total = cycles.reduce((sum, c) => sum + c.steps.length, 0);

  if (total === 0) return null;

  return (
    <div className="agent-thinking">
      <button
        type="button"
        className="agent-thinking__toggle"
        onClick={() => setAllOpen((v) => !v)}
      >
        <span>{allOpen ? "已展开所有步骤" : "已收起所有步骤"}</span>
        <Chevron open={allOpen} />
      </button>
      <div className="agent-thinking__cycles">
        {cycles.map((cycle) => (
          <CycleItem key={cycle.id} cycle={cycle} defaultOpen={allOpen} />
        ))}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="agent-bubble__typing">
      <span className="agent-bubble__dot" />
      <span className="agent-bubble__dot" />
      <span className="agent-bubble__dot" />
      <span>AI 正在思考…</span>
    </div>
  );
}

function UserMessage({ content }: { content: string }) {
  const handleCopy = () => {
    void navigator.clipboard.writeText(content);
  };

  return (
    <div className="agent-message agent-message--user">
      <div className="agent-message--user__inner">
        <div className="agent-message--user__header">
          <span className="agent-message--user__avatar">L</span>
          <span className="agent-message--user__name">lanzhengpeng</span>
        </div>
        <div className="agent-message--user__row">
          <div className="agent-message--user__spacer" />
          <div className="agent-message--user__bubble">{content}</div>
        </div>
        <div className="agent-message--user__actions">
          <button
            type="button"
            className="agent-message__action"
            title="编辑"
            onClick={() => {
              // TODO: wire edit flow
            }}
          >
            <EditOutlined />
          </button>
          <button
            type="button"
            className="agent-message__action"
            title="复制"
            onClick={handleCopy}
          >
            <CopyOutlined />
          </button>
          <button
            type="button"
            className="agent-message__action"
            title="重新发送"
            onClick={() => {
              // TODO: wire resend flow
            }}
          >
            <RedoOutlined />
          </button>
        </div>
      </div>
    </div>
  );
}

function AssistantMessage({
  data,
  onRegenerate,
}: {
  data?: { content: string; cycles: ReactCycle[]; loading: boolean; done?: boolean };
  onRegenerate?: () => void;
}) {
  const content = data?.content ?? "";
  const loading = data?.loading && !content && !data.cycles.length;

  const handleCopy = () => {
    if (content) void navigator.clipboard.writeText(content);
  };

  const timeString = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  const hasFileWrite =
    data?.cycles.some((cycle) =>
      cycle.steps.some(
        (s) =>
          s.type === "tool" &&
          (s.name.toLowerCase().includes("write") ||
            s.name.toLowerCase().includes("create"))
      )
    ) ?? false;

  return (
    <div className="agent-message agent-message--assistant">
      <div className="agent-message--assistant__inner">
        {loading ? (
          <TypingDots />
        ) : (
          <>
            {data && data.cycles.length > 0 && (
              <ThinkingPanel cycles={data.cycles} />
            )}
            {content && (
              <div className="agent-message__answer">
                <MarkdownContent content={content} />
              </div>
            )}
            {data?.done && hasFileWrite && <CheckpointCard />}
            <div className="agent-message--assistant__footer">
              <div className="agent-message--assistant__actions">
                <button
                  type="button"
                  className="agent-message__action"
                  title="复制"
                  onClick={handleCopy}
                >
                  <CopyOutlined />
                </button>
                {onRegenerate && (
                  <button
                    type="button"
                    className="agent-message__action"
                    title="重新生成"
                    onClick={onRegenerate}
                  >
                    <RedoOutlined />
                  </button>
                )}
                <button
                  type="button"
                  className="agent-message__action"
                  title="分享"
                >
                  <ShareAltOutlined />
                </button>
                <button
                  type="button"
                  className="agent-message__action"
                  title="有用"
                >
                  <LikeOutlined />
                </button>
                <button
                  type="button"
                  className="agent-message__action"
                  title="无用"
                >
                  <DislikeOutlined />
                </button>
              </div>
              <div className="agent-message--assistant__meta">
                <span className="agent-message--assistant__time">
                  <ClockCircleOutlined />
                  <span>{timeString}</span>
                </span>
                <span className="agent-message--assistant__tokens">
                  — tokens · $0.000
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CheckpointCard() {
  return (
    <div className="agent-checkpoint">
      <div className="agent-checkpoint__info">
        <div className="agent-checkpoint__title">版本检查点</div>
        <div className="agent-checkpoint__desc">当前变更未持久化（占位）</div>
      </div>
      <div className="agent-checkpoint__actions">
        <button
          type="button"
          className="agent-checkpoint__btn agent-checkpoint__btn--primary"
          disabled
        >
          部署
        </button>
        <button type="button" className="agent-checkpoint__btn" disabled>
          回退
        </button>
      </div>
    </div>
  );
}

export function AgentChatPanel({
  isConversationSidebarOpen,
  onFolderClick,
  onConversationToggle,
  onBackClick,
  onHistoryClick,
}: {
  isConversationSidebarOpen?: boolean;
  onFolderClick?: () => void;
  onConversationToggle?: () => void;
  onBackClick?: () => void;
  onHistoryClick?: () => void;
}) {
  const { messages, status, error, send, stop } = useAgentChat();
  const [input, setInput] = useState("");
  const isStreaming = status === "streaming";

  const assistantData = useMemo(() => {
    const map = new Map<
      string,
      { content: string; cycles: ReactCycle[]; loading: boolean; done?: boolean }
    >();
    messages.forEach((m) => {
      if (m.role === "assistant") {
        const all = dedupeCycles(m.cycles ?? []);
        const content = cleanFinalAnswer(m.content);
        const cycles = visibleCyclesFor(all, content);
        map.set(m.id, {
          content,
          cycles,
          loading: m.status === "loading",
          done: m.status === "done",
        });
      }
    });
    return map;
  }, [messages]);

  const lastUserIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") return i;
    }
    return -1;
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    void send(text);
  };

  const handleRegenerate = (messageIndex: number) => {
    const text = messages[messageIndex]?.content;
    if (!text || isStreaming) return;
    void send(text);
  };

  return (
    <div className="agent-panel">
      <div className="agent-panel__header">
        <div className="agent-panel__header-inner">
          <button
            type="button"
            className="agent-panel__icon-btn"
            title="返回"
            onClick={() => onBackClick?.()}
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </button>
          {!isConversationSidebarOpen && (
            <button
              type="button"
              className="agent-panel__icon-btn"
              title="对话列表"
              onClick={() => onConversationToggle?.()}
            >
              <PanelLeft size={16} aria-hidden="true" />
            </button>
          )}
          <div className="agent-panel__brand">
            <button
              className="agent-panel__brand-trigger"
              type="button"
              aria-haspopup="dialog"
              aria-expanded={false}
              aria-controls="radix-:rd:"
              data-state="closed"
              data-slot="popover-trigger"
            >
              <span data-slot="avatar" className="agent-panel__brand-avatar">
                <img
                  data-slot="avatar-image"
                  alt=""
                  src="https://coze-coding-project.tos.coze.site/gen_project_icon/2026-05-28/7644848070408323114_1779957446.png?sign=1784870498-d8a08333e7-0-150f0370ca6423a40dac95769c5fb72637e3dde5c07d679f617ab4817cd9ab3b"
                />
              </span>
              <div className="agent-panel__brand-name">
                <div className="agent-panel__brand-name-text">
                  接口生成和规范
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="agent-panel__brand-chevron"
                aria-hidden="true"
              >
                <path d="m18 15-6-6-6 6" />
              </svg>
            </button>
          </div>
          <button
            type="button"
            className="agent-panel__icon-btn"
            title="历史版本"
            onClick={() => onHistoryClick?.()}
          >
            <History size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="agent-panel__icon-btn"
            title="项目文件"
            onClick={() => onFolderClick?.()}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="agent-panel__body">
        {messages.length > 0 && (
          <div className="agent-message-list">
            {messages.map((m, idx) =>
              m.role === "user" ? (
                <UserMessage key={m.id} content={m.content} />
              ) : (
                <AssistantMessage
                  key={m.id}
                  data={assistantData.get(m.id)}
                  onRegenerate={
                    idx === messages.length - 1 && lastUserIndex >= 0
                      ? () => handleRegenerate(lastUserIndex)
                      : undefined
                  }
                />
              )
            )}
          </div>
        )}

        {error && <div className="agent-error">请求出错：{error}</div>}
      </div>

      <div className="agent-panel__footer">
        <div className="agent-panel__sender">
          <Sender
            value={input}
            onChange={(value) => setInput(value)}
            onSubmit={handleSend}
            loading={isStreaming}
            onCancel={stop}
            submitType="enter"
            placeholder="输入任务或问题，例如：计算 2 + 3…"
            autoSize={{ minRows: 1, maxRows: 4 }}
            suffix={false}
            footer={
              <div className="agent-sender-toolbar">
                <div className="agent-sender-toolbar__left">
                  <button
                    type="button"
                    className="agent-sender-toolbar__btn"
                    title="上传文件（未实现）"
                    disabled
                  >
                    <PlusOutlined />
                  </button>
                  <button
                    type="button"
                    className="agent-sender-toolbar__btn"
                    title="设置（未实现）"
                    disabled
                  >
                    <SettingOutlined />
                  </button>
                  <button
                    type="button"
                    className="agent-sender-toolbar__btn agent-sender-toolbar__btn--text"
                    title="技能（未实现）"
                    disabled
                  >
                    <BookOutlined />
                    <span>技能</span>
                    <span className="agent-sender-toolbar__inline-badge">0</span>
                  </button>
                  <button
                    type="button"
                    className="agent-sender-toolbar__btn agent-sender-toolbar__btn--text"
                    title="模型选择（未实现）"
                    disabled
                  >
                    <span>Auto</span>
                    <DownOutlined />
                  </button>
                </div>
                <div className="agent-sender-toolbar__right">
                  <button
                    type="button"
                    className="agent-sender-toolbar__btn"
                    title="语音输入（未实现）"
                    disabled
                  >
                    <AudioOutlined />
                  </button>
                  {isStreaming ? (
                    <button
                      type="button"
                      className="agent-sender-toolbar__btn agent-sender-toolbar__btn--send"
                      title="停止生成"
                      onClick={stop}
                    >
                      <BorderOutlined />
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="agent-sender-toolbar__btn agent-sender-toolbar__btn--send"
                      title="发送"
                      disabled={!input.trim()}
                      onClick={handleSend}
                    >
                      <ArrowUpOutlined />
                    </button>
                  )}
                </div>
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
