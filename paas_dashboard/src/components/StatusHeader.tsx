import type { CheatSheetCounts, CheatSheetModuleStatus } from "../types/cheatSheet";

interface StatusHeaderProps {
  counts: CheatSheetCounts;
  modules: CheatSheetModuleStatus;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export function StatusHeader({ counts, modules, loading, error, onRefresh }: StatusHeaderProps) {
  return (
    <header
      style={{
        height: 64,
        background: "#ffffff",
        borderBottom: "1px solid #e2e8f0",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <h1 style={{ margin: 0, fontSize: 20, color: "#0f172a" }}>
          PaaS 架构可视化
        </h1>

        <div style={{ display: "flex", gap: 16, fontSize: 14 }}>
          <Stat label="Controller" value={counts.controllers} color="#3b82f6" />
          <Stat label="Service" value={counts.services} color="#22c55e" />
          <Stat label="Mapper" value={counts.mappers} color="#8b5cf6" />
          <Stat
            label="模块"
            value={modules.loaded.length}
            color="#0f172a"
            suffix={`/${modules.loaded.length + modules.failed.length}`}
          />
          {modules.failed.length > 0 && (
            <Stat label="失败" value={modules.failed.length} color="#ef4444" />
          )}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {loading && <span style={{ color: "#64748b", fontSize: 13 }}>刷新中...</span>}
        {error && <span style={{ color: "#ef4444", fontSize: 13 }}>{error}</span>}
        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            color: "#334155",
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          立即刷新
        </button>
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  color,
  suffix,
}: {
  label: string;
  value: number;
  color: string;
  suffix?: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ fontWeight: 700, color: "#0f172a" }}>
        {value}
        {suffix}
      </span>
    </div>
  );
}
