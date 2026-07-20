import type { NodeProps } from "@xyflow/react";
import type { ModuleNodeData } from "../lib/graphBuilder";

export function ModuleNode(props: NodeProps) {
  const data = props.data as ModuleNodeData;
  const isFailed = data.status === "failed";
  const { counts } = data;

  return (
    <div
      style={{
        width: 260,
        minHeight: 120,
        borderRadius: 12,
        background: isFailed ? "#fef2f2" : "#ffffff",
        border: isFailed ? "2px solid #ef4444" : "2px solid #3b82f6",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: isFailed ? "#b91c1c" : "#1e293b",
            wordBreak: "break-all",
          }}
        >
          {data.label}
        </span>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: isFailed ? "#ef4444" : "#22c55e",
          }}
        />
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          fontSize: 12,
          color: "#475569",
        }}
      >
        <span style={badgeStyle("#dbeafe", "#1d4ed8")}>C: {counts.controllers}</span>
        <span style={badgeStyle("#dcfce7", "#15803d")}>S: {counts.services}</span>
        <span style={badgeStyle("#f3e8ff", "#7e22ce")}>M: {counts.mappers}</span>
      </div>

      {isFailed && data.error && (
        <div
          style={{
            fontSize: 11,
            color: "#991b1b",
            background: "#fee2e2",
            padding: 8,
            borderRadius: 6,
            wordBreak: "break-all",
          }}
        >
          {data.error}
        </div>
      )}
    </div>
  );
}

function badgeStyle(bg: string, color: string): React.CSSProperties {
  return {
    background: bg,
    color: color,
    padding: "2px 8px",
    borderRadius: 999,
    fontWeight: 600,
  };
}
