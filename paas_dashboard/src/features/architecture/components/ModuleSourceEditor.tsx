import { useEffect, useState } from "react";
import {
  deleteModule,
  fetchModuleFile,
  fetchModuleFiles,
  reloadModule,
  updateModuleFile,
} from "../../../services/api";

interface ModuleSourceEditorProps {
  pluginName: string;
  onChanged?: () => void;
  onDeleted?: () => void;
}

export function ModuleSourceEditor({
  pluginName,
  onChanged,
  onDeleted,
}: ModuleSourceEditorProps) {
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [saveResult, setSaveResult] = useState<{
    checkOk: boolean;
    reloadOk: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    setFiles([]);
    setSelectedFile(null);
    setContent("");
    setOriginalContent("");
    setError(null);
    setSaveResult(null);

    let cancelled = false;
    setLoading(true);
    fetchModuleFiles(pluginName)
      .then((list) => {
        if (cancelled) return;
        setFiles(list);
        if (list.length > 0) {
          setSelectedFile(list[0]);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [pluginName]);

  useEffect(() => {
    if (!selectedFile) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSaveResult(null);
    fetchModuleFile(pluginName, selectedFile)
      .then((text) => {
        if (cancelled) return;
        setContent(text);
        setOriginalContent(text);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [pluginName, selectedFile]);

  const hasChanges = content !== originalContent;

  const handleSave = async () => {
    if (!selectedFile) return;
    setSaving(true);
    setError(null);
    setSaveResult(null);
    try {
      const result = await updateModuleFile(pluginName, selectedFile, content);
      const checkOk = Boolean(result.check?.ok);
      const reloadError = result.reload_report?.error;
      const reloadOk = checkOk && !reloadError;

      if (reloadOk) {
        setOriginalContent(content);
        setSaveResult({
          checkOk: true,
          reloadOk: true,
          message: "保存并重载成功",
        });
      } else if (!checkOk) {
        setSaveResult({
          checkOk: false,
          reloadOk: false,
          message: `静态检查未通过：${(result.check?.errors || []).join("；")}`,
        });
      } else {
        setSaveResult({
          checkOk: true,
          reloadOk: false,
          message: `重载失败：${reloadError || "未知错误"}`,
        });
      }

      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReloadOnly = async () => {
    setSaving(true);
    setError(null);
    setSaveResult(null);
    try {
      await reloadModule(pluginName);
      setSaveResult({
        checkOk: true,
        reloadOk: true,
        message: "模块重载成功",
      });
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const ok = window.confirm(
      `确定删除模块 ${pluginName} 吗？该操作不可恢复，模块目录及其所有文件都会被删除。`
    );
    if (!ok) return;

    setDeleting(true);
    setError(null);
    try {
      await deleteModule(pluginName);
      onDeleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {loading && files.length === 0 && (
        <div style={{ fontSize: 12, color: "#64748b" }}>加载文件列表...</div>
      )}

      {files.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {files.map((file) => (
            <button
              key={file}
              type="button"
              onClick={() => setSelectedFile(file)}
              style={{
                padding: "4px 10px",
                fontSize: 12,
                borderRadius: 12,
                border: "1px solid",
                borderColor: selectedFile === file ? "#3b82f6" : "#cbd5e1",
                background: selectedFile === file ? "#eff6ff" : "#ffffff",
                color: selectedFile === file ? "#1d4ed8" : "#475569",
                cursor: "pointer",
              }}
            >
              {file}
            </button>
          ))}
        </div>
      )}

      {selectedFile && (
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 6,
            }}
          >
            <span style={{ fontSize: 12, color: "#64748b", fontFamily: "monospace" }}>
              {selectedFile}
            </span>
            {hasChanges && (
              <span style={{ fontSize: 11, color: "#f59e0b" }}>已修改</span>
            )}
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={loading}
            spellCheck={false}
            style={{
              width: "100%",
              height: 240,
              padding: 10,
              borderRadius: 6,
              border: "1px solid #cbd5e1",
              fontSize: 12,
              fontFamily: "monospace",
              resize: "vertical",
              boxSizing: "border-box",
              background: loading ? "#f8fafc" : "#ffffff",
            }}
          />
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          onClick={handleSave}
          disabled={saving || deleting || !selectedFile || !hasChanges}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "none",
            background: saving || !hasChanges ? "#93c5fd" : "#3b82f6",
            color: "#fff",
            cursor: saving || !hasChanges ? "not-allowed" : "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {saving ? "保存中..." : "保存并重载"}
        </button>
        <button
          onClick={handleReloadOnly}
          disabled={saving || deleting}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            background: "#fff",
            color: "#475569",
            cursor: saving || deleting ? "not-allowed" : "pointer",
            fontSize: 12,
          }}
        >
          仅重载
        </button>
        <button
          onClick={handleDelete}
          disabled={saving || deleting}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "none",
            background: deleting ? "#fca5a5" : "#ef4444",
            color: "#fff",
            cursor: saving || deleting ? "not-allowed" : "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {deleting ? "删除中..." : "删除模块"}
        </button>
      </div>

      {saveResult && (
        <div
          style={{
            padding: 8,
            borderRadius: 6,
            fontSize: 12,
            background: saveResult.reloadOk ? "#dcfce7" : "#fef3c7",
            color: saveResult.reloadOk ? "#166534" : "#92400e",
          }}
        >
          {saveResult.message}
        </div>
      )}

      {error && (
        <div
          style={{
            padding: 8,
            borderRadius: 6,
            fontSize: 12,
            background: "#fee2e2",
            color: "#991b1b",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
