import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { MethodNodeData } from "../lib/graphBuilder";

const TYPE_STYLES: Record<
  MethodNodeData["componentType"],
  { background: string; border: string; color: string }
> = {
  controller: { background: "#eff6ff", border: "#3b82f6", color: "#1d4ed8" },
  service: { background: "#f0fdf4", border: "#22c55e", color: "#15803d" },
  mapper: { background: "#faf5ff", border: "#8b5cf6", color: "#7e22ce" },
};

export function MethodNode(props: NodeProps) {
  const data = props.data as MethodNodeData;
  const { method, componentType, height, locked } = data;
  const styles = TYPE_STYLES[componentType];
  const label = method.feature || method.name;

  return (
    <div
      style={{
        width: "100%",
        height,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#ffffff",
        border: `${locked ? 3 : 1}px solid ${styles.border}${locked ? "" : "40"}`,
        borderRadius: 8,
        boxShadow: locked ? `0 0 0 3px ${styles.border}30, 0 2px 8px rgba(0, 0, 0, 0.06)` : "0 2px 8px rgba(0, 0, 0, 0.06)",
        padding: "0 12px",
        boxSizing: "border-box",
        position: "relative",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={handleStyle(styles.border, { top: -5, left: "50%" })}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        style={handleStyle(styles.border, { bottom: -5, left: "50%" })}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={handleStyle(styles.border, { top: "50%", left: -6 })}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={handleStyle(styles.border, { top: "50%", right: -6 })}
      />

      <div
        style={{
          fontSize: 14,
          fontWeight: 700,
          color: styles.color,
          textAlign: "center",
          lineHeight: 1.2,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          width: "100%",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function handleStyle(
  color: string,
  pos: { top?: number | string; left?: number | string; bottom?: number | string; right?: number | string }
): React.CSSProperties {
  return {
    position: "absolute",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: color,
    border: "2px solid #fff",
    zIndex: 1,
    transform: pos.left === "50%" ? "translateX(-50%)" : pos.top === "50%" ? "translateY(-50%)" : undefined,
    ...pos,
  };
}
