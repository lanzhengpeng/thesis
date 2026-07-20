import type { NodeProps } from "@xyflow/react";
import type { ModuleNodeData } from "../lib/graphBuilder";

export const MODULE_HEADER_HEIGHT = 56;

export function ModuleNode(props: NodeProps) {
  const data = props.data as ModuleNodeData;
  const isFailed = data.status === "failed";
  const { counts } = data;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        borderRadius: 12,
        background: isFailed ? "#fef2f2" : "#ffffff",
        border: isFailed ? "2px solid #ef4444" : "2px solid #3b82f6",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: MODULE_HEADER_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "0 16px",
          boxSizing: "border-box",
          borderBottom: isFailed ? "1px solid #fecaca" : "1px solid #bfdbfe",
          minWidth: 0,
        }}
      >
        <span
          style={{
            flex: "1 1 auto",
            minWidth: 0,
            fontSize: 16,
            fontWeight: 700,
            color: isFailed ? "#b91c1c" : "#1e293b",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {data.label}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 6 }}>
            <span style={badgeStyle("#dbeafe", "#1d4ed8")}>C: {counts.controllers}</span>
            <span style={badgeStyle("#dcfce7", "#15803d")}>S: {counts.services}</span>
            <span style={badgeStyle("#f3e8ff", "#7e22ce")}>M: {counts.mappers}</span>
          </div>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: isFailed ? "#ef4444" : "#22c55e",
              flexShrink: 0,
            }}
          />
        </div>
      </div>

      <div style={{ flex: 1, position: "relative" }} />

      {isFailed && data.error && (
        <div
          style={{
            fontSize: 11,
            color: "#991b1b",
            background: "#fee2e2",
            padding: 8,
            borderRadius: 6,
            wordBreak: "break-all",
            margin: "0 16px 12px",
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
    fontSize: 11,
    fontWeight: 600,
  };
}
