import { Panel } from "@xyflow/react";
import type { CheatSheetCounts, CheatSheetModuleStatus } from "../../../types/cheatSheet";

interface GraphStatsPanelProps {
  counts: CheatSheetCounts;
  modules: CheatSheetModuleStatus;
  loading?: boolean;
  error?: string | null;
}

export function GraphStatsPanel({
  counts,
  modules,
  loading,
  error,
}: GraphStatsPanelProps) {
  const loadedCount = new Set(modules.loaded).size;
  const failedCount = new Set(modules.failed.map((f) => f.module)).size;
  const totalCount = loadedCount + failedCount;

  return (
    <Panel position="top-left">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "8px 14px",
          borderRadius: 8,
          background: "rgba(255, 255, 255, 0.92)",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 4px rgba(0, 0, 0, 0.04)",
          backdropFilter: "blur(6px)",
          fontSize: 12,
          flexWrap: "wrap",
        }}
      >
        <Stat label="Controller" value={counts.controllers} color="#3b82f6" />
        <Stat label="Service" value={counts.services} color="#22c55e" />
        <Stat label="Mapper" value={counts.mappers} color="#8b5cf6" />
        <Stat
          label="模块"
          value={loadedCount}
          color="#0f172a"
          suffix={`/${totalCount}`}
        />
        {failedCount > 0 && (
          <Stat label="失败" value={failedCount} color="#ef4444" />
        )}
        {loading && (
          <span style={{ color: "#64748b", whiteSpace: "nowrap" }}>刷新中...</span>
        )}
        {error && (
          <span style={{ color: "#ef4444", whiteSpace: "nowrap" }}>{error}</span>
        )}
      </div>
    </Panel>
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
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color }} />
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ fontWeight: 700, color: "#0f172a" }}>
        {value}
        {suffix}
      </span>
    </div>
  );
}
