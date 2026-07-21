import { Handle, Position, type NodeProps } from "@xyflow/react";
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
        borderRadius: 16,
        background: isFailed ? "rgba(254, 242, 242, 0.85)" : "rgba(255, 255, 255, 0.85)",
        border: isFailed ? "2px solid #ef4444" : "2px solid #bfdbfe",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.1)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          position: "absolute",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#94a3b8",
          border: "2px solid #fff",
          top: -5,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 1,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        style={{
          position: "absolute",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#94a3b8",
          border: "2px solid #fff",
          bottom: -5,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 1,
        }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          position: "absolute",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#94a3b8",
          border: "2px solid #fff",
          top: "50%",
          left: -6,
          transform: "translateY(-50%)",
          zIndex: 1,
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          position: "absolute",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#94a3b8",
          border: "2px solid #fff",
          top: "50%",
          right: -6,
          transform: "translateY(-50%)",
          zIndex: 1,
        }}
      />

      <div
        style={{
          height: MODULE_HEADER_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "0 24px",
          boxSizing: "border-box",
          borderBottom: isFailed ? "1px solid rgba(254, 202, 202, 0.8)" : "1px solid rgba(191, 219, 254, 0.8)",
          background: isFailed ? "rgba(254, 202, 202, 0.6)" : "rgba(219, 234, 254, 0.5)",
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
            padding: 10,
            borderRadius: 6,
            wordBreak: "break-all",
            margin: "0 24px 16px",
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
