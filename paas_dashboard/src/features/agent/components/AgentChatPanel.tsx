import {
  ArrowUpOutlined,
  AudioOutlined,
  BookOutlined,
  BorderOutlined,
  CopyOutlined,
  DownOutlined,
  FileAddOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  PlusOutlined,
  RedoOutlined,
  SearchOutlined,
  SettingOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { ChevronLeft, History, PanelLeft } from "lucide-react";
import { Sender } from "@ant-design/x";
import { XMarkdown } from "@ant-design/x-markdown";
import "@ant-design/x-markdown/dist/x-markdown.css";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { markedHighlight } from "marked-highlight";
import { useMemo, useState } from "react";
import { useAgentChat, type UIMessage } from "../hooks/useAgentChat";
import "../styles/agent-chat.css";

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
    return { title: "搜索", icon: <SearchOutlined /> };
  }
  if (normalized.includes("plan") || normalized.includes("update_plan")) {
    return { title: "更新计划", icon: <OrderedListOutlined /> };
  }
  if (normalized.includes("skill") || normalized.includes("load")) {
    return { title: "加载技能", icon: <ToolOutlined /> };
  }
  if (normalized.includes("calc")) {
    return { title: "计算", icon: <span style={{ fontSize: 14 }}>🔢</span> };
  }
  if (normalized.includes("weather")) {
    return { title: "天气", icon: <span style={{ fontSize: 14 }}>🌤</span> };
  }
  if (normalized.includes("database") || normalized.includes("query")) {
    return { title: "数据库", icon: <span style={{ fontSize: 14 }}>🗄</span> };
  }
  if (normalized.includes("file")) {
    return { title: "文件操作", icon: <FileTextOutlined /> };
  }
  return { title: name, icon: <ToolOutlined /> };
}

function extractToolSummary(input: string): string {
  if (!input) return "";
  try {
    const parsed = JSON.parse(input);
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
    const trimmed = input.trim();
    return trimmed.length > 60 ? `${trimmed.slice(0, 60)}…` : trimmed;
  }
}

function extractFilePath(input: string): string | null {
  if (!input) return null;
  try {
    const parsed = JSON.parse(input);
    if (parsed.file_path) return parsed.file_path;
    if (parsed.path) return parsed.path;
    return null;
  } catch {
    return null;
  }
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
  const lines = code.split("\n");
  const isTruncated = lines.length > 20;
  const [expanded, setExpanded] = useState(false);
  const displayCode = isTruncated && !expanded ? lines.slice(0, 20).join("\n") : code;

  const handleCopy = () => {
    void navigator.clipboard.writeText(code);
  };

  return (
    <div
      className={`agent-code-block ${isOutput ? "agent-code-block--output" : ""}`}
    >
      <div className="agent-code-block__header">
        <div className="agent-code-block__header-left">
          <span className="agent-code-block__lang">
            {filePath ? filePath.split("/").pop() : label}
          </span>
          <span className="agent-code-block__line-count">
            {lines.length} {lines.length === 1 ? "line" : "lines"}
          </span>
        </div>
        <button
          type="button"
          className="agent-code-block__copy"
          onClick={handleCopy}
        >
          Copy
        </button>
      </div>
      <pre>{displayCode}</pre>
      {isTruncated && (
        <button
          type="button"
          className="agent-code-block__toggle"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded
            ? "Collapse"
            : `Show ${lines.length - 20} more lines`}
        </button>
      )}
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
        <div className="agent-message--user__bubble">{content}</div>
        <div className="agent-message--user__actions">
          <button
            type="button"
            className="agent-message__action"
            title="复制"
            onClick={handleCopy}
          >
            <CopyOutlined />
            <span>Copy</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="agent-typing">
      <span className="agent-typing__dot" />
      <span className="agent-typing__dot" />
      <span className="agent-typing__dot" />
    </div>
  );
}

function AssistantMessage({
  content,
  loading,
  isStreaming,
}: {
  content: string;
  loading: boolean;
  isStreaming: boolean;
}) {
  const handleCopy = () => {
    if (content) void navigator.clipboard.writeText(content);
  };

  const showCursor = loading && isStreaming;

  return (
    <div className="agent-message agent-message--assistant">
      <div className="agent-message--assistant__inner">
        {loading && !content && isStreaming ? (
          <TypingDots />
        ) : (
          <>
            {content && (
              <div className="agent-message__answer">
                <MarkdownContent content={content} />
                {showCursor && <span className="agent-cursor" />}
              </div>
            )}
            <div className="agent-message--user__actions">
              <button
                type="button"
                className="agent-message__action"
                title="复制"
                onClick={handleCopy}
              >
                <CopyOutlined />
                <span>Copy</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ThinkingBlock({ content, isActive }: { content: string; isActive?: boolean }) {
  const [open, setOpen] = useState(false);
  if (!content.trim() && !isActive) return null;

  const lines = content.split("\n").filter((l) => l.trim());
  const firstLine = lines[0]?.replace(/\s+/g, " ").trim() || "";
  const preview =
    firstLine.length > 80 ? firstLine.slice(0, 80) + "..." : firstLine;

  return (
    <div className="agent-thinking">
      <button
        type="button"
        className="agent-thinking__toggle"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="agent-thinking__triangle">
          {open ? "▾" : "▸"}
        </span>
        <span className="agent-thinking__label">
          思考过程
          {isActive && <span className="agent-thinking__dots" />}
        </span>
        {!open && preview && (
          <span className="agent-thinking__preview">{preview}</span>
        )}
      </button>
      {open && (
        <div className="agent-thinking__content">
          <MarkdownContent content={content} />
          {isActive && <span className="agent-cursor" />}
        </div>
      )}
    </div>
  );
}

function ToolUseBlock({
  toolName,
  input,
}: {
  toolName: string;
  input: string;
}) {
  const [open, setOpen] = useState(false);
  const display = getToolDisplay(toolName);
  const summary = extractToolSummary(input);
  const filePath = extractFilePath(input);

  return (
    <div className="agent-tool-use">
      <button
        type="button"
        className="agent-tool-use__header"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="agent-tool-use__icon">{display.icon}</span>
        <span className="agent-tool-use__name">{display.title}</span>
        {(filePath || summary) && (
          <span className="agent-tool-use__summary">
            {filePath ? filePath.split("/").pop() : summary}
          </span>
        )}
        <span
          className={`agent-tool-use__chevron ${open ? "agent-tool-use__chevron--open" : ""}`}
        >
          ▾
        </span>
      </button>
      {open && (
        <div className="agent-tool-use__body">
          <CodeBlock
            code={input}
            label="参数"
            filePath={filePath}
          />
        </div>
      )}
    </div>
  );
}

function ToolResultBlock({
  content,
  isError,
}: {
  content: string;
  isError: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!content) return null;

  const lines = content.split("\n");
  const preview = lines.slice(0, 6).join("\n");
  const hasMore = lines.length > 6;

  return (
    <div className="agent-tool-result">
      <button
        type="button"
        className="agent-tool-result__header"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="agent-tool-result__status">
          {isError ? "✗ Error" : "✓"}
        </span>
        {!expanded && (
          <span
            className={`agent-tool-result__badge ${isError ? "agent-tool-result__badge--error" : "agent-tool-result__badge--success"}`}
          >
            {preview.length > 40 ? preview.slice(0, 40) + "…" : preview}
          </span>
        )}
      </button>
      {expanded && (
        isError ? (
          <div className="agent-tool-result__content--error">
            {content}
          </div>
        ) : (
          <div className="agent-tool-result__content">
            <CodeBlock code={content} label="Output" isOutput />
          </div>
        )
      )}
      {hasMore && (
        <button
          type="button"
          className="agent-tool-result__more"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "收起" : `展开 (${lines.length} lines)`}
        </button>
      )}
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return <div className="agent-error">请求出错：{message}</div>;
}

function MessageItem({ message, isStreaming }: { message: UIMessage; isStreaming: boolean }) {
  switch (message.type) {
    case "user_text":
      return <UserMessage content={message.content} />;
    case "assistant_text":
      return (
        <AssistantMessage
          content={message.content}
          loading={message.status === "loading"}
          isStreaming={isStreaming}
        />
      );
    case "thinking":
      return <ThinkingBlock content={message.content} isActive={isStreaming && message.type === "thinking"} />;
    case "tool_use":
      return <ToolUseBlock toolName={message.toolName} input={message.input} />;
    case "tool_result":
      return (
        <ToolResultBlock content={message.content} isError={message.isError} />
      );
    case "error":
      return <ErrorBlock message={message.message} />;
    default:
      return null;
  }
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

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
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
                  src="https://coze-coding-project.tos.coze.site/gen_project_icon/2026-05-28/7644848070408323114_1779957446.png?sign=1784870498-d8a08333e-0-150f0370ca6423a40dac95769c5fb72637e3dde5c07d679f617ab4817cd9ab3b"
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
            {messages.map((m) => (
              <MessageItem
                key={m.id}
                message={m}
                isStreaming={isStreaming}
              />
            ))}
          </div>
        )}

        {error && !messages.some((m) => m.type === "error") && (
          <div className="agent-error">请求出错：{error}</div>
        )}
      </div>

      <div className="agent-panel__footer">
        <div className="agent-panel__sender">
          <Sender
            value={input}
            onChange={(value) => setInput(value)}
            onSubmit={handleSend}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.ctrlKey &&
                !e.metaKey &&
                !e.altKey
              ) {
                e.preventDefault();
                handleSend();
                return false;
              }
            }}
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
