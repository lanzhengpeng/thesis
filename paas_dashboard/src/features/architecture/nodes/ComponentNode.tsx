import { type NodeProps } from "@xyflow/react";
import type { ComponentNodeData } from "../lib/graphBuilder";

const TYPE_STYLES: Record<
  ComponentNodeData["componentType"],
  { background: string; border: string; color: string; headerBg: string }
> = {
  controller: {
    background: "rgba(239, 246, 255, 0.65)",
    border: "#3b82f6",
    color: "#1d4ed8",
    headerBg: "rgba(59, 130, 246, 0.12)",
  },
  service: {
    background: "rgba(240, 253, 244, 0.65)",
    border: "#22c55e",
    color: "#15803d",
    headerBg: "rgba(34, 197, 94, 0.12)",
  },
  mapper: {
    background: "rgba(250, 245, 255, 0.65)",
    border: "#8b5cf6",
    color: "#7e22ce",
    headerBg: "rgba(139, 92, 246, 0.12)",
  },
};

export function ComponentNode(props: NodeProps) {
  const data = props.data as ComponentNodeData;
  const styles = TYPE_STYLES[data.componentType];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        borderRadius: 12,
        background: styles.background,
        border: `2px solid ${styles.border}`,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "visible",
        boxShadow: "0 6px 18px rgba(0, 0, 0, 0.12)",
        position: "relative",
      }}
    >
      <div
        style={{
          height: 48,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: `0 16px`,
          borderBottom: `1px solid ${styles.border}40`,
          background: styles.headerBg,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: styles.color,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {data.label}
        </span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            color: "#fff",
            background: styles.border,
            padding: "3px 7px",
            borderRadius: 4,
            flexShrink: 0,
          }}
        >
          {data.componentType}
        </span>
      </div>
    </div>
  );
}
