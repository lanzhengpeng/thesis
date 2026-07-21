import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ModuleNodeData } from "../lib/graphBuilder";

export function GatewayNode(props: NodeProps) {
  const data = props.data as ModuleNodeData;

  return (
    <div
      style={{
        width: 200,
        height: 80,
        borderRadius: 12,
        background: "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
        color: "#f8fafc",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 16,
        fontWeight: 700,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)",
        border: "2px solid #475569",
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
          background: "#64748b",
          border: "2px solid #fff",
          top: -5,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />
      {data.label}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        style={{
          position: "absolute",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#64748b",
          border: "2px solid #fff",
          bottom: -5,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />
    </div>
  );
}
