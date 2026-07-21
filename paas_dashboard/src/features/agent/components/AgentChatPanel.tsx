import { useMemo, useRef, useEffect } from "react";
import { useChat } from "ai/react";
import { Bubble, Sender } from "@ant-design/x";
import type { BubbleItemType, Info } from "@ant-design/x/es/bubble/interface";
import { XMarkdown } from "@ant-design/x-markdown";
import { markedHighlight } from "marked-highlight";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import "../styles/agent-chat.css";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * 将后端 SSE 流（data: ...\n\n）转换为纯文本流，
 * 供 Vercel AI SDK useChat 在 streamMode: 'text' 下消费。
 */
async function customFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const response = await fetch(input, init);

  if (!response.ok || !response.body) {
    return response;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const data = part.slice(6);
          controller.enqueue(encoder.encode(data));
        }
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

export function AgentChatPanel() {
  const listRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    input,
    setInput,
    handleSubmit,
    isLoading,
    stop,
    error,
  } = useChat({
    api: `${BASE_URL}/admin/agent/generate`,
    streamMode: "text",
    experimental_prepareRequestBody: ({ messages: chatMessages }) => {
      const lastMessage = chatMessages[chatMessages.length - 1];
      return { task: lastMessage?.content || "" };
    },
    fetch: customFetch,
    keepLastMessageOnError: true,
  });

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
    const list: BubbleItemType[] = messages.map(
      (msg) =>
        ({
          key: msg.id,
          role: msg.role === "user" ? "user" : "ai",
          content: msg.content,
        } satisfies BubbleItemType)
    );

    if (
      isLoading &&
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
  }, [messages, isLoading]);

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

  return (
    <div
      style={{
        width: 400,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid #e2e8f0",
        background: "#ffffff",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid #e2e8f0",
          background: "#fafafa",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 16, color: "#0f172a" }}>
          AI 智能体助手
        </h3>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#64748b" }}>
          输入自然语言任务，自动生成并部署模块
        </p>
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
        {items.length === 0 && (
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
              例如：创建用户模块、生成订单服务
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
                contentRender: (content: string, info: Info) => (
                  <XMarkdown
                    content={content}
                    className="agent-chat-markdown"
                    config={markdownConfig}
                    streaming={{
                      hasNextChunk:
                        isLoading && info.key === lastAiKey,
                    }}
                  />
                ),
              },
            }}
          />
        )}

        {error && (
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
        <Sender
          value={input}
          onChange={(value) => setInput(value)}
          onSubmit={() => handleSubmit()}
          loading={isLoading}
          onCancel={stop}
          submitType="enter"
          placeholder="输入任务，例如：创建用户模块..."
          autoSize={{ minRows: 1, maxRows: 6 }}
        />
      </div>
    </div>
  );
}
