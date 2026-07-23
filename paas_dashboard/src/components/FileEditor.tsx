import { useEffect, useMemo, useRef, useState } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { python } from "@codemirror/lang-python";
import { markdown } from "@codemirror/lang-markdown";
import { javascript } from "@codemirror/lang-javascript";
import { json } from "@codemirror/lang-json";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";
import { XMarkdown } from "@ant-design/x-markdown";
import "@ant-design/x-markdown/dist/x-markdown.css";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { markedHighlight } from "marked-highlight";
import { Eye, PencilLine } from "lucide-react";
import { fetchFinderWrite } from "../services/api";
import "./FileEditor.css";

interface FileEditorProps {
  path: string;
  content: string;
  onChange?: (value: string) => void;
}

function getLanguageExtension(path: string) {
  const ext = path.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "py":
      return python();
    case "md":
      return markdown();
    case "js":
      return javascript();
    case "jsx":
      return javascript({ jsx: true });
    case "ts":
      return javascript({ typescript: true });
    case "tsx":
      return javascript({ jsx: true, typescript: true });
    case "json":
      return json();
    case "html":
      return html();
    case "css":
      return css();
    default:
      return [];
  }
}

function isMarkdown(path: string) {
  return path.split(".").pop()?.toLowerCase() === "md";
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
      className="file-editor__markdown"
      config={config}
    />
  );
}

export function FileEditor({ path, content, onChange }: FileEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const saveTimerRef = useRef<number | null>(null);
  const pendingContentRef = useRef<string | null>(null);
  const onChangeRef = useRef(onChange);
  const [mode, setMode] = useState<"preview" | "edit">(
    isMarkdown(path) ? "preview" : "edit"
  );
  const [saveState, setSaveState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");

  onChangeRef.current = onChange;

  const markdownFile = isMarkdown(path);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        window.clearTimeout(saveTimerRef.current);
      }
      // Component unmounting: try to flush any pending save.
      if (pendingContentRef.current !== null) {
        void fetchFinderWrite(path, pendingContentRef.current).catch(() => {
          // Silent fail on unmount.
        });
      }
    };
  }, [path]);

  useEffect(() => {
    if (mode !== "edit" || !containerRef.current) {
      if (viewRef.current) {
        viewRef.current.destroy();
        viewRef.current = null;
      }
      return;
    }

    const lightTheme = EditorView.theme({
      "&": {
        height: "100%",
        backgroundColor: "#ffffff",
        color: "#171717",
      },
      ".cm-scroller": { overflow: "auto" },
      ".cm-content": {
        minHeight: "100%",
        caretColor: "#171717",
      },
      "&.cm-focused .cm-cursor": {
        borderLeftColor: "#171717",
      },
      "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection": {
        backgroundColor: "#bfdbfe",
      },
      ".cm-gutters": {
        backgroundColor: "#f8fafc",
        color: "#64748b",
        borderRight: "1px solid #e2e8f0",
      },
      ".cm-activeLineGutter": {
        backgroundColor: "#e2e8f0",
      },
      ".cm-activeLine": {
        backgroundColor: "#f1f5f9",
      },
      ".cm-lineNumbers": {
        color: "#64748b",
      },
      ".cm-selectionMatch": {
        backgroundColor: "#dbeafe",
      },
      ".cm-matchingBracket, .cm-nonmatchingBracket": {
        backgroundColor: "#dbeafe",
        outline: "1px solid #93c5fd",
      },
      ".cm-tooltip": {
        backgroundColor: "#ffffff",
        border: "1px solid #e2e8f0",
        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
      },
      ".cm-tooltip-autocomplete > ul > li[aria-selected]": {
        backgroundColor: "#eff6ff",
        color: "#171717",
      },
      ".cm-panel": {
        backgroundColor: "#f8fafc",
        borderTop: "1px solid #e2e8f0",
      },
      ".cm-searchMatch": {
        backgroundColor: "#fef08a",
      },
      ".cm-searchMatch.cm-searchMatch-selected": {
        backgroundColor: "#fde047",
      },
    });

    const extensions = [
      basicSetup,
      lightTheme,
      syntaxHighlighting(defaultHighlightStyle),
      getLanguageExtension(path),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const value = update.state.doc.toString();
          onChangeRef.current?.(value);
          if (markdownFile) {
            pendingContentRef.current = value;
            if (saveTimerRef.current) {
              window.clearTimeout(saveTimerRef.current);
            }
            setSaveState("idle");
            saveTimerRef.current = window.setTimeout(() => {
              const pending = pendingContentRef.current;
              if (pending === null) return;
              pendingContentRef.current = null;
              setSaveState("saving");
              fetchFinderWrite(path, pending)
                .then(() => setSaveState("saved"))
                .catch(() => setSaveState("error"));
            }, 1000);
          }
        }
      }),
    ];

    if (!markdownFile) {
      extensions.push(EditorView.editable.of(false));
      extensions.push(EditorState.readOnly.of(true));
    }

    const state = EditorState.create({
      doc: content,
      extensions,
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // content is intentionally omitted: the editor is the source of truth while
    // mounted; recreating on every keystroke would reset cursor/scroll state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, path]);

  const fileName = path.split("/").pop() ?? path;

  const saveLabel = {
    idle: "",
    saving: "保存中...",
    saved: "已保存",
    error: "保存失败",
  }[saveState];

  return (
    <div className="file-editor">
      <div className="file-editor__header">
        <nav className="file-editor__breadcrumb" aria-label="breadcrumb">
          <ol>
            <li>
              <span className="file-editor__breadcrumb-current">{fileName}</span>
            </li>
          </ol>
        </nav>
        <div className="file-editor__header-actions">
          {!markdownFile && (
            <span className="file-editor__status file-editor__status--readonly">
              只读
            </span>
          )}
          {markdownFile && saveLabel && (
            <span
              className={`file-editor__status file-editor__status--${saveState}`}
            >
              {saveLabel}
            </span>
          )}
          {markdownFile && (
            <div className="file-editor__tabs">
              <button
                type="button"
                className={`file-editor__tab${
                  mode === "preview" ? " file-editor__tab--active" : ""
                }`}
                title="预览"
                aria-label="预览"
                onClick={() => setMode("preview")}
              >
                <Eye size={14} />
              </button>
              <button
                type="button"
                className={`file-editor__tab${
                  mode === "edit" ? " file-editor__tab--active" : ""
                }`}
                title="编辑"
                aria-label="编辑"
                onClick={() => setMode("edit")}
              >
                <PencilLine size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="file-editor__content">
        {mode === "preview" && isMarkdown(path) ? (
          <MarkdownContent content={content} />
        ) : (
          <div className="file-editor__editor" ref={containerRef} />
        )}
      </div>
    </div>
  );
}
